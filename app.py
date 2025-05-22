import os
import sys
import site
import logging

# Fix for ModuleNotFoundError on auto-reload
# Add the virtual environment's site-packages to sys.path
venv_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
site_packages = os.path.join(venv_path, 'venv', 'lib', 'python3.12', 'site-packages')
if os.path.exists(site_packages):
    sys.path.insert(0, site_packages)
# Alternatively, try with a relative path from the current file
local_site_packages = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'lib', 'python3.12', 'site-packages')
if os.path.exists(local_site_packages):
    sys.path.insert(0, local_site_packages)

# Auto-install missing packages during development
def ensure_package(package_name):
    try:
        __import__(package_name)
        print(f"✓ {package_name} is installed")
    except ImportError:
        print(f"! {package_name} not found, attempting to install...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✓ {package_name} has been installed")
            # Force reload to ensure it's in the current process
            __import__(package_name)
        except Exception as e:
            print(f"! Failed to install {package_name}: {e}")
            raise

# Ensure critical packages are available for development
if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
    essential_packages = ['pandas', 'redis', 'flask_session']
    for package in essential_packages:
        ensure_package(package)

import base64
import tempfile
import cv2
from flask import Flask, request, render_template, jsonify, send_from_directory, session, make_response, send_file
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
from PIL import Image
import io
import uuid
from datetime import datetime
import requests
import pandas as pd
import redis
import json
from flask_session import Session

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # Secret key for sessions

# Global variables for chat session management
redis_chat_client = None
in_memory_chat_sessions = {} # Fallback if Redis is not available
CHAT_SESSION_EXPIRY_SECONDS = 3600 * 24 # 24 hours, for example

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

try:
    # Attempt to connect to Redis for chat sessions
    # Using decode_responses=False, as existing code manually decodes bytes from hgetall
    temp_redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)), # Can be separate for chat vs Flask-Session if needed
        socket_timeout=2, # Timeout for Redis operations
        socket_connect_timeout=2 # Timeout for initial connection
    )
    temp_redis_client.ping() # Check connection
    redis_chat_client = temp_redis_client # Assign to global variable if connection is successful
    print("INFO: Successfully connected to Redis. Chat sessions will be stored in Redis.")

    # Configure Flask-Session to also use this Redis instance
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'flask_sess:' # Distinct prefix for Flask's own sessions
    app.config['SESSION_REDIS'] = redis_chat_client # Use the same client for Flask-Session
    Session(app)
    print("INFO: Flask-Session is configured to use Redis.")

except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
    print(f"WARNING: Could not connect to Redis: {e}. Chat sessions will be in-memory (non-persistent).")
    print("INFO: Flask will use default cookie-based sessions for its own session management.")
    redis_chat_client = None # Ensure client is None if connection failed
    # Flask-Session will not be configured for Redis; Flask defaults will apply for `session` proxy.

# Simple CORS configuration
CORS(app, supports_credentials=True)

# Get the port from environment or use default
port = int(os.getenv('PORT', 7081))

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['BATCH_SERVICE_URL'] = os.getenv('BATCH_SERVICE_URL', 'http://batch-processor:7082')  # Batch processor service URL

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Helper functions for chat session management (Redis with in-memory fallback)
def get_chat_session(session_id):
    if redis_chat_client:
        try:
            redis_key = f"chat_session:{session_id}"
            if redis_chat_client.exists(redis_key):
                session_data_raw = redis_chat_client.hgetall(redis_key)
                session_data = {
                    key.decode('utf-8'): value.decode('utf-8')
                    for key, value in session_data_raw.items()
                }
                # Deserialize JSON fields
                session_data['frames'] = json.loads(session_data.get('frames', '[]'))
                session_data['timestamps'] = json.loads(session_data.get('timestamps', '[]'))
                session_data['history'] = json.loads(session_data.get('history', '[]'))
                logger.debug(f"Fetched session {session_id} from Redis.")
                return session_data
            else:
                # Key not found in Redis; see if we have an in-memory copy we can push back
                if session_id in in_memory_chat_sessions:
                    logger.warning(f"Session {session_id} missing in Redis but present in memory – back-filling Redis.")
                    _mem = in_memory_chat_sessions[session_id]
                    # Serialise for Redis
                    backup_obj = {
                        'frames': json.dumps(_mem.get('frames', [])),
                        'timestamps': json.dumps(_mem.get('timestamps', [])),
                        'filename': _mem.get('filename', ''),
                        'duration': str(_mem.get('duration', '0')),
                        'additional_context': _mem.get('additional_context', ''),
                        'history': json.dumps(_mem.get('history', []))
                    }
                    try:
                        redis_chat_client.hset(redis_key, mapping=backup_obj)
                        redis_chat_client.expire(redis_key, CHAT_SESSION_EXPIRY_SECONDS)
                        logger.info(f"Back-filled session {session_id} into Redis.")
                    except Exception as e:
                        logger.error(f"Failed to back-fill Redis for session {session_id}: {e}")
                    return _mem
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            logger.warning(f"Redis connection error in get_chat_session: {e}. Falling back to in-memory.")
    # Redis not available or key missing; return in-memory copy (if any)
    return in_memory_chat_sessions.get(session_id)

def _normalize_chat_data(data):
    """Return a shallow copy of data with frames/timestamps/history deserialized."""
    converted = data.copy()

    # Convert frames
    if isinstance(converted.get("frames"), str):
        try:
            converted["frames"] = json.loads(converted["frames"])
        except Exception:
            pass

    # Convert timestamps
    if isinstance(converted.get("timestamps"), str):
        try:
            converted["timestamps"] = json.loads(converted["timestamps"])
        except Exception:
            pass

    # Convert history
    if isinstance(converted.get("history"), str):
        try:
            converted["history"] = json.loads(converted["history"])
        except Exception:
            pass

    return converted

def set_chat_session(session_id, chat_data):
    frames_json = chat_data.get("frames") # Assuming frames is already json.dumps'd
    timestamps_json = chat_data.get("timestamps") # Assuming timestamps is already json.dumps'd
    history_json = chat_data.get("history") # Assuming history is already json.dumps'd

    redis_data_to_set = {
        "frames": frames_json,
        "timestamps": timestamps_json,
        "filename": chat_data.get("filename", ""),
        "duration": str(chat_data.get("duration", "0")),
        "additional_context": chat_data.get("additional_context", ""),
        "history": history_json
    }

    if redis_chat_client:
        try:
            redis_key = f"chat_session:{session_id}"
            # Use hset with mapping parameter instead of hmset
            redis_chat_client.hset(redis_key, mapping=redis_data_to_set)
            redis_chat_client.expire(redis_key, CHAT_SESSION_EXPIRY_SECONDS)
            return
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            print(f"WARNING: Redis connection error in set_chat_session: {e}. Falling back to in-memory.")

    # Always keep a copy in in-memory store so the app continues without Redis
    in_memory_chat_sessions[session_id] = _normalize_chat_data(chat_data)
    return

def update_chat_history(session_id, history_list):
    history_json = json.dumps(history_list)
    if redis_chat_client:
        try:
            redis_key = f"chat_session:{session_id}"
            redis_chat_client.hset(redis_key, "history", history_json)
            redis_chat_client.expire(redis_key, CHAT_SESSION_EXPIRY_SECONDS) # Refresh expiry
            return
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            print(f"WARNING: Redis connection error in update_chat_history: {e}. Falling back to in-memory.")

    # Always update in-memory copy
    if session_id in in_memory_chat_sessions:
        in_memory_chat_sessions[session_id]['history'] = history_list
    else:
        # Create minimal entry if somehow missing
        in_memory_chat_sessions[session_id] = {
            'frames': [],
            'timestamps': [],
            'filename': '',
            'duration': '0',
            'additional_context': '',
            'history': history_list
        }

def chat_session_exists(session_id):
    if redis_chat_client:
        try:
            return bool(redis_chat_client.exists(f"chat_session:{session_id}"))
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            print(f"WARNING: Redis connection error in chat_session_exists: {e}. Falling back to in-memory.")
    return session_id in in_memory_chat_sessions

def process_markdown_to_html(text):
    """Convert markdown bold ** syntax to HTML for rich text formatting"""
    import re
    # Process bold syntax (** **) to HTML
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_frames(video_path, num_frames=5):
    """Extract frames from a video file"""
    frames = []
    
    # Open the video file
    video = cv2.VideoCapture(video_path)
    
    # Get video properties
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    # Calculate frames to extract based on duration
    if total_frames <= num_frames:
        frame_indices = list(range(total_frames))
    else:
        # Extract frames at regular intervals
        frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
    
    # Extract the frames
    frames_data = []
    timestamps = []
    
    for idx in frame_indices:
        video.set(cv2.CAP_PROP_POS_FRAMES, idx)
        success, frame = video.read()
        
        if success:
            # Convert to RGB (from BGR)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_img = Image.fromarray(frame_rgb)
            
            # Resize if needed (to reduce size)
            max_size = (800, 800)
            pil_img.thumbnail(max_size, Image.LANCZOS)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')
            
            # Calculate timestamp
            timestamp = idx / fps if fps > 0 else 0
            
            frames_data.append(img_base64)
            timestamps.append(timestamp)
    
    video.release()
    
    return frames_data, timestamps, duration

@app.route('/')
def index():
    print("Accessing index route")  # Debug print
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    print("Received upload request")  # Debug print
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Generate a session ID for this chat
            session_id = str(uuid.uuid4())
            
            # Extract frames from the video - increase from 5 to 8 for better accuracy
            frames, timestamps, duration = extract_frames(filepath, num_frames=8)
            
            # Format timestamps as mm:ss
            formatted_timestamps = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in timestamps]
            
            # Check for additional context from user
            additional_context = request.form.get('additional_context', '').strip()
            
            # Prepare message content for GPT-4 Vision
            message_content = [
                {
                    "type": "text", 
                    "text": f"I'm sending you 8 frames from a video named '{filename}' with a duration of {int(duration // 60):02d}:{int(duration % 60):02d}. "
                           f"The frames were taken at the following timestamps: {', '.join(formatted_timestamps)}. "
                           f"Please analyze these frames and provide a comprehensive analysis of what is happening in this video. "
                           f"Pay special attention to accurately identifying animals, people, and objects. Double-check species identification by examining distinguishing features. "
                           f"Structure your response with proper HTML formatting using <h3>GENERATED TITLE</h3> first as a one-line title for the video, followed by <h3>VIDEO SUMMARY</h3>, then <h3>NARRATED SUMMARY</h3>, and finally the <h3>DETAILED ANALYSIS OF THE VIDEO SEGMENTS</h3>. IMPORTANT: ENSURE ALL SECTION HEADINGS ARE IN ALL CAPITAL LETTERS EXACTLY AS SHOWN."
                }
            ]
            
            # Include additional context if provided
            if additional_context:
                message_content[0]["text"] += f"\n\nAdditional context from the user: {additional_context}"
                
            # Add each frame to the message content
            for i, (frame, timestamp) in enumerate(zip(frames, formatted_timestamps)):
                message_content.append({
                    "type": "text",
                    "text": f"Frame {i+1} (at {timestamp}):"
                })
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame}"
                    }
                })
            
            # System message
            system_message = {
                "role": "system",
                "content": "You are a comprehensive video analysis expert with exceptional attention to accuracy and fine details. Your task is to analyze frames from a video with extremely high precision. \n\nFor all identifications, especially animals, vehicles, and objects:\n1. Take extra time to verify species, breeds, makes and models before stating them\n2. Look carefully at distinguishing features (e.g., elephant trunks vs buffalo horns, ear shapes, body proportions)\n3. If uncertain about an identification, describe the features you see and provide possible options rather than making a definitive but potentially incorrect statement\n4. Use taxonomic precision (correct species names) when identifying animals\n5. If image quality makes identification difficult, explicitly state this limitation\n\nOrganize your response in the following order using proper HTML formatting (not markdown):\n\n1. <h3>GENERATED TITLE</h3> Create a one-line descriptive title for the video based on its main content\n\n2. <h3>VIDEO SUMMARY</h3> Provide a concise, factual summary of what is happening in the video. Focus on objective observations, counts, and key events in a straightforward manner. Keep this section brief and informative.\n\n3. <h3>NARRATED SUMMARY</h3> Present the video content in an engaging, narrative style as if you were a documentary narrator. Use vivid language and natural storytelling techniques while maintaining factual accuracy. Make this section come alive for someone who hasn't seen the video.\n\n4. <h3>DETAILED ANALYSIS OF THE VIDEO SEGMENTS</h3> In this section, include your comprehensive analysis with all details:\n   - Exact counts of people, animals, vehicles, and other key objects\n   - Specific colors of important elements (clothing, vehicles, backgrounds, etc.)\n   - Precise spatial relationships between objects\n   - Detailed descriptions of actions and movements\n   - Object characteristics like size, shape, brand, model when possible\n   - Environmental details (indoor/outdoor, lighting, weather if applicable)\n   - Text content visible in the frames\n\nPrioritize accuracy over comprehensiveness when necessary - it's better to be tentative but accurate than confident but wrong. IMPORTANT: ENSURE ALL SECTION HEADINGS ARE IN ALL CAPITAL LETTERS EXACTLY AS SHOWN ABOVE."
            }
            
            # User message with the frames
            user_message = {
                "role": "user",
                "content": message_content
            }
            
            # Get analysis from GPT-4 Vision
            response = client.chat.completions.create(
                model="gpt-4o",  # Updated to current supported model
                messages=[system_message, user_message],
                max_tokens=1500
            )
            
            # Initialize chat session with history
            assistant_response = response.choices[0].message.content
            # Convert markdown bold syntax to HTML for rich text display
            assistant_response_html = process_markdown_to_html(assistant_response)
            chat_data = {
                "frames": json.dumps(frames),  # Serialize list to JSON string
                "timestamps": json.dumps(formatted_timestamps),  # Serialize list to JSON string
                "filename": filename,
                "duration": str(duration), # Store as string
                "additional_context": additional_context if additional_context else "", # Ensure string
                "history": json.dumps([  # Serialize list of dicts to JSON string
                    system_message,
                    user_message,
                    {"role": "assistant", "content": assistant_response}
                ])
            }
            set_chat_session(session_id, chat_data)
            
            # Store video frames for reuse
            # Delete the raw video file now that frames are extracted to save disk space
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify({
                'analysis': assistant_response_html,
                'session_id': session_id
            })
            
        except Exception as e:
            print(f"Error processing request: {str(e)}")  # Debug print
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/custom_analysis', methods=['POST'])
def custom_analysis():
    print("Received custom analysis request")
    
    if 'custom_prompt' not in request.form:
        return jsonify({'error': 'No custom prompt provided'}), 400
    
    custom_prompt = request.form['custom_prompt']
    session_id = request.form.get('session_id')
    
    # Check if we have a valid session ID
    if not session_id or not chat_session_exists(session_id):
        # If no session ID or invalid session ID, try to process with uploaded video
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided and no active session'}), 400
            
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Create a new session ID
                session_id = str(uuid.uuid4())
                
                # Extract frames from the video - use 8 frames for better accuracy
                frames, timestamps, duration = extract_frames(filepath, num_frames=8)
                formatted_timestamps = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in timestamps]
                
                # Get additional context if provided
                additional_context = request.form.get('additional_context', '').strip()
                
                # Initialize the chat session
                initial_system_message = {
                    "role": "system",
                    "content": "You are a detailed video analysis expert with an exceptional commitment to accuracy. Your task is to analyze frames from a video and respond to the user's specific questions or follow their custom instructions about the video content. \n\nWhen identifying elements in the video:\n1. Be extremely careful with taxonomic classifications of animals - verify identifying features (trunks, horns, ears, etc.) before naming a species\n2. Distinguish carefully between similar-looking objects (e.g., elephant vs. buffalo, tiger vs. lion, car models)\n3. When uncertain, describe visual features and possible identifications rather than making definitive statements\n4. Consider image quality and viewing angle in your confidence level\n\nWhen providing a complete analysis, structure your response using proper HTML formatting (not markdown) in this exact order:\n\n1. <h3>GENERATED TITLE</h3> Create a one-line descriptive title for the video based on its main content\n\n2. <h3>VIDEO SUMMARY</h3> Brief, factual overview of the video content with key observations\n\n3. <h3>NARRATED SUMMARY</h3> An engaging, narrative description of the video in a documentary-style voice\n\n4. <h3>DETAILED ANALYSIS OF THE VIDEO SEGMENTS</h3> Comprehensive breakdown including:\n   - Count specific objects (people, vehicles, animals, items) and report exact numbers\n   - Describe precise colors of all important elements\n   - Identify brands, models, and specific types of objects when confident, otherwise describe features\n   - Notice text visible in the frames and report it accurately\n   - Pay careful attention to spatial relationships and compositions\n   - Describe actions in detail, including subtle movements\n   - Note environmental details (location type, weather, lighting)\n\nAim for 100% accuracy in your descriptions, even if it means being more tentative in some identifications. IMPORTANT: ENSURE ALL SECTION HEADINGS ARE IN ALL CAPITAL LETTERS EXACTLY AS SHOWN ABOVE."
                }
                chat_data = {
                    "frames": json.dumps(frames),
                    "timestamps": json.dumps(formatted_timestamps),
                    "filename": filename,
                    "duration": str(duration),
                    "additional_context": additional_context if additional_context else "",
                    "history": json.dumps([initial_system_message])
                }
                set_chat_session(session_id, chat_data)
                
                # Store video frames for reuse
                # Delete the raw video file now that frames are extracted to save disk space
                if os.path.exists(filepath):
                    os.remove(filepath)
                
            except Exception as e:
                print(f"Error processing custom analysis request: {str(e)}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': str(e)}), 500
                
            # Clean up original file
            if os.path.exists(filepath):
                os.remove(filepath)
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    
    # We now have a valid session
    session_data = get_chat_session(session_id)
    if not session_data:
        # This case should ideally not be hit if the exists check above passed,
        # but as a safeguard:
        return jsonify({'error': 'Session not found in Redis after check'}), 404

    # Check if this is a request to verify animal identification or for narration
    is_animal_verification = False
    is_narration_request = False
    
    animal_verification_prompts = [
        "verify animal", "animal identification", "identify animal", 
        "check species", "verify species", "animal species", "identify species",
        "what animal", "what species", "confirm animal", "verify animal species"
    ]
    
    narration_prompts = [
        "narrate", "narration", "narrator", "narrate video", "tell story", 
        "documentary style", "narrative voice", "describe as narrator",
        "nature documentary", "sports broadcast", "movie trailer", "storyteller"
    ]
    
    for phrase in animal_verification_prompts:
        if phrase.lower() in custom_prompt.lower():
            is_animal_verification = True
            break
            
    for phrase in narration_prompts:
        if phrase.lower() in custom_prompt.lower():
            is_narration_request = True
            break
            
    # Prepare message content for GPT-4 Vision with custom prompt
    if is_animal_verification:
        # Special handling for animal verification with focus on accuracy
        message_content = [
            {
                "type": "text", 
                "text": f"Please carefully verify the animal species in the video. This is a specific request to double-check animal identification. Focus on clear taxonomic identification based on visible features.\n\nUser query: {custom_prompt}\n\nStructure your response with these sections in order using HTML formatting:\n\n1. <h3>GENERATED TITLE</h3> Create a one-line descriptive title about the animals in this video\n\n2. <h3>VIDEO SUMMARY</h3> Brief identification of the animals with taxonomic precision\n\n3. <h3>NARRATED SUMMARY</h3> Describe the animals in a naturalist style\n\n4. <h3>DETAILED ANALYSIS</h3> When identifying animals:\n   - Look for distinctive features (trunk, horns, ears, tails, etc.)\n   - Compare size and proportions\n   - Note coloration patterns and textures\n   - Observe behaviors if visible\n   - Provide taxonomic details when possible\n   - If uncertain between species (like elephant vs buffalo), explain why and provide visual evidence for your conclusion\n\nIMPORTANT: ENSURE ALL SECTION HEADINGS ARE IN ALL CAPITAL LETTERS EXACTLY AS SHOWN ABOVE."
            }
        ]
    elif is_narration_request:
        # Special handling for narration requests
        narrative_style = ""
        
        # Check for specific narrative styles
        if "nature documentary" in custom_prompt.lower():
            narrative_style = "nature documentary like David Attenborough"
        elif "sports broadcast" in custom_prompt.lower():
            narrative_style = "sports broadcast"
        elif "movie trailer" in custom_prompt.lower():
            narrative_style = "movie trailer with dramatic tone"
        elif "storyteller" in custom_prompt.lower():
            narrative_style = "engaging storyteller"
        else:
            narrative_style = "documentary-style narrator"
            
        message_content = [
            {
                "type": "text", 
                "text": f"Please provide a narrated summary of the video in the style of a {narrative_style}. Create a vivid, expressive narration that brings the video content to life while maintaining factual accuracy.\n\nUser request: {custom_prompt}\n\nEven if just creating a narrated version, structure your response using HTML formatting with a <h3>GENERATED TITLE</h3> first as a one-line title for the video, followed by <h3>VIDEO SUMMARY</h3>, then your <h3>NARRATED SUMMARY</h3>, and if needed, a brief <h3>DETAILED ANALYSIS</h3> section. Use descriptive language, natural transitions, and an engaging tone appropriate for the requested style.\n\nIMPORTANT: ENSURE ALL SECTION HEADINGS ARE IN ALL CAPITAL LETTERS EXACTLY AS SHOWN ABOVE."
            }
        ]
    else:
        # Regular custom prompt
        message_content = [
            {
                "type": "text", 
                "text": f"Regarding the video '{session_data['filename']}' with duration {int(float(session_data['duration']) // 60):02d}:{int(float(session_data['duration']) % 60):02d}, here's a new question or instruction from the user: \n\n{custom_prompt}"
            }
        ]
        
        # Use the additional context stored in the session data if available
        if session_data.get('additional_context'):
            message_content[0]["text"] += f"\n\nAdditional context provided by the user: {session_data['additional_context']}"
    
    # Add frames only for the first few custom prompts or special requests
    if len(session_data['history']) < 8 or is_animal_verification or is_narration_request:
        # Add each frame to the message content
        for i, (frame, timestamp) in enumerate(zip(session_data['frames'], session_data['timestamps'])):
            message_content.append({
                "type": "text",
                "text": f"Frame {i+1} (at {timestamp}):"
            })
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame}"
                }
            })
    
    # Add the user's custom prompt to the history
    current_history = session_data['history']
    current_history.append({
        "role": "user",
        "content": message_content
    })
    update_chat_history(session_id, current_history)
    
    # Get analysis from GPT-4 Vision with conversation history
    try:
        # Only use last 10 messages to avoid exceeding context limits
        recent_history = current_history[-10:] if len(current_history) > 10 else current_history
        
        # If animal verification or narration, boost max tokens for detailed response
        max_tokens = 2000 if (is_animal_verification or is_narration_request) else 1500
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=recent_history,
            max_tokens=max_tokens
        )
        
        # Add assistant's response to history
        assistant_response = response.choices[0].message.content
        # Convert markdown bold syntax to HTML for rich text display
        assistant_response_html = process_markdown_to_html(assistant_response)
        current_history.append({
            "role": "assistant",
            "content": assistant_response
        })
        update_chat_history(session_id, current_history)
        
        return jsonify({
            'analysis': assistant_response_html,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error in GPT processing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    if 'content' not in request.form:
        return jsonify({'error': 'No content provided'}), 400
    
    content = request.form['content']
    title = request.form.get('title', 'Video Analysis Report')
    
    try:
        # Create HTML content using regular string formatting
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content_with_br = content.replace('\n', '<br>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                h1 {{ color: #4338ca; }}
                .header {{ padding-bottom: 20px; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px; }}
                .content {{ white-space: pre-wrap; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #6b7280; text-align: center; }}
                @media print {{
                    body {{ font-size: 12pt; }}
                    .no-print {{ display: none; }}
                    a {{ text-decoration: none; color: black; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Generated on {timestamp}</p>
                <div class="no-print">
                    <p>To save as PDF, use your browser's print function (Ctrl+P or Cmd+P) and select "Save as PDF".</p>
                    <button onclick="window.print()" style="padding: 8px 16px; background-color: #4338ca; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;">Print / Save as PDF</button>
                </div>
            </div>
            <div class="content">
                {content_with_br}
            </div>
            <div class="footer">
                <p>Generated by Video Analysis Assistant</p>
            </div>
        </body>
        </html>
        """
        
        # Return HTML content directly
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        
        return response
        
    except Exception as e:
        print(f"Error generating export: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/batch/status', methods=['GET'])
def batch_service_status():
    """Check if the batch processing service is running"""
    try:
        response = requests.get(
            f"{app.config['BATCH_SERVICE_URL']}/active-jobs",
            timeout=2  # Short timeout for quick status check
        )
        return jsonify({
            'status': 'running',
            'endpoint': app.config['BATCH_SERVICE_URL']
        })
    except requests.RequestException as e:
        return jsonify({
            'status': 'not running',
            'error': f"Batch processing service is not available: {str(e)}",
            'endpoint': app.config['BATCH_SERVICE_URL']
        }), 503  # Service Unavailable

@app.route('/batch/process-folder', methods=['POST'])
def batch_process_folder():
    """Process all videos in a folder using the batch processor service"""
    data = request.json
    if not data or 'folder_path' not in data:
        return jsonify({'error': 'No folder path provided'}), 400
    
    # Verify the folder path exists
    folder_path = data.get('folder_path')
    try:
        print(f"Checking if folder exists: {folder_path}")
        if not os.path.isdir(folder_path):
            print(f"Folder does not exist: {folder_path}")
            return jsonify({'error': f'Folder not found: {folder_path}'}), 400
        
        # Check permissions
        if not os.access(folder_path, os.R_OK):
            print(f"Permission denied for folder: {folder_path}")
            return jsonify({'error': f'Permission denied for folder: {folder_path}'}), 403
        
        # Check if there are video files in the folder
        print(f"Looking for video files in: {folder_path}")
        video_files = [f for f in os.listdir(folder_path) 
                      if os.path.isfile(os.path.join(folder_path, f)) and 
                      any(f.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)]
        
        print(f"Video files found: {video_files}")
        
        if not video_files:
            return jsonify({'error': f'No video files found in folder: {folder_path}'}), 400
        
        print(f"Found {len(video_files)} video files in {folder_path}")
    except Exception as e:
        error_message = f"Error accessing folder {folder_path}: {str(e)}"
        print(error_message)
        return jsonify({'error': error_message}), 500
    
    try:
        print(f"Forwarding request to batch processor: {data}")
        # Forward the request to the batch processor service
        response = requests.post(
            f"{app.config['BATCH_SERVICE_URL']}/process-folder",
            json=data,
            timeout=10  # Add timeout to prevent hanging
        )
        
        print(f"Batch processor response: Status={response.status_code}, Content={response.text[:200]}")
        
        if response.status_code != 200:
            error_message = f"Batch processor error: {response.text}"
            print(f"Error from batch processor: {error_message}")
            return jsonify({'error': error_message}), response.status_code
            
        return jsonify(response.json())
    except requests.RequestException as e:
        error_message = f"Cannot connect to batch processing service: {str(e)}"
        print(f"Connection error to batch processor: {error_message}")
        return jsonify({
            'error': error_message,
            'hint': "Make sure the batch processing service is running (go run batch-processor/main.go)"
        }), 503
    except Exception as e:
        error_message = f"Error processing batch request: {str(e)}"
        print(f"Exception in batch processing: {error_message}")
        return jsonify({'error': error_message}), 500

@app.route('/batch/status/<batch_id>', methods=['GET'])
def batch_status(batch_id):
    """Get the status of a batch job"""
    try:
        response = requests.get(f"{app.config['BATCH_SERVICE_URL']}/batch-status/{batch_id}")
        
        if response.status_code != 200:
            return jsonify({'error': f'Batch processor error: {response.text}'}), response.status_code
            
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch/active-jobs', methods=['GET'])
def batch_active_jobs():
    """Get all active batch jobs"""
    try:
        response = requests.get(f"{app.config['BATCH_SERVICE_URL']}/active-jobs")
        
        if response.status_code != 200:
            return jsonify({'error': f'Batch processor error: {response.text}'}), response.status_code
            
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch/job/<job_id>', methods=['GET'])
def batch_job_status(job_id):
    """Get status of an individual job in a batch"""
    try:
        response = requests.get(f"{app.config['BATCH_SERVICE_URL']}/job/{job_id}")
        
        if response.status_code != 200:
            return jsonify({'error': f'Batch processor error: {response.text}'}), response.status_code
            
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch/batch-upload', methods=['POST'])
def batch_upload_files():
    """Process multiple video files using the batch processor service"""
    # Check if files were uploaded
    if 'videos' not in request.files:
        return jsonify({'error': 'No videos provided'}), 400
    
    # Get list of files
    files = request.files.getlist('videos')
    if not files or len(files) == 0:
        return jsonify({'error': 'No videos provided'}), 400
    
    # Check if there are too many files
    if len(files) > 15:  # Max limit defined in batch processor
        return jsonify({'error': 'Too many files. Maximum allowed is 15'}), 400
    
    # Check if cleanup was requested
    cleanup = request.form.get('cleanup', 'false').lower() in ('true', 't', '1', 'yes')
    
    try:
        print(f"Forwarding {len(files)} files to batch processor")
        
        # Create a new multipart request to forward to the batch processor
        response = requests.post(
            f"{app.config['BATCH_SERVICE_URL']}/batch-upload",
            files=[('videos', (file.filename, file.read(), file.content_type)) for file in files],
            data={'cleanup': str(cleanup).lower()},
            timeout=30  # Longer timeout for multiple file uploads
        )
        
        print(f"Batch processor response: Status={response.status_code}")
        
        if response.status_code != 200:
            error_message = f"Batch processor error: {response.text}"
            print(f"Error from batch processor: {error_message}")
            return jsonify({'error': error_message}), response.status_code
            
        return jsonify(response.json())
    except requests.RequestException as e:
        error_message = f"Cannot connect to batch processing service: {str(e)}"
        print(f"Connection error to batch processor: {error_message}")
        return jsonify({
            'error': error_message,
            'hint': "Make sure the batch processing service is running (go run batch-processor/main.go)"
        }), 503
    except Exception as e:
        error_message = f"Error processing batch request: {str(e)}"
        print(f"Exception in batch processing: {error_message}")
        return jsonify({'error': error_message}), 500

@app.route('/video-analysis/<session_id>', methods=['GET'])
def get_video_analysis(session_id):
    """Get analysis results for a specific video by session ID"""
    try:
        # Try to get from Redis or in-memory fallback
        session_data = get_chat_session(session_id)
        
        if session_data:
            # history will be a Python list from get_chat_session helper
            history = session_data.get('history', []) 
            filename = session_data.get('filename', 'unknown_video')
            
            for message in history:
                if message['role'] == 'assistant':
                    return jsonify({
                        'analysis': message['content'],
                        'filename': filename,
                        'session_id': session_id
                    })
            # If assistant message not found in history for some reason
            return jsonify({'error': 'Assistant analysis not found in session history', 'session_id': session_id}), 404

        # If not found in active sessions (Redis or in-memory), then attempt to find the analysis file (existing fallback logic)
        # The batch processor stores the session ID, which we can use to look up the analysis
        # We need to find the original filename associated with this session_id to locate the correct analysis file.
        # This information isn't directly available here if not in chat_sessions.
        # However, the batch processor *does* know the filename and analysis_id (session_id).
        # For robustness, it's better to rely on information directly from the batch processor's job status
        # when exporting all, rather than trying to reconstruct filenames here.
        # This function is primarily for retrieving individual analysis when a session is active or was recently.

        # Fallback: check analysis files based on session_id pattern if needed, though less ideal.
        # This part might need adjustment if filenames don't consistently embed session_id.
        # The primary source of truth for batch export will be the batch service.
        
        # Attempt to find an analysis file that might contain the session_id in its name,
        # or a file whose name corresponds to a filename stored with this session_id if it were in chat_sessions.
        # This is a bit indirect. The /batch/export-excel route will have more direct info.

        placeholder_filename = "unknown_video" # Default if no specific filename is found
        
        # Attempt to find analysis file, assuming it might be named like original_filename_analysis.txt
        # This part is tricky without knowing the exact original filename if not in chat_sessions.
        # The batch export logic will be more robust by using filename from batch job details.
        
        # Search for a file that *might* match this session_id pattern in its name if created by the batch job.
        # This is a secondary check.
        potential_analysis_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('_analysis.txt') and session_id in f]
        if potential_analysis_files:
            analysis_file_path = os.path.join(app.config['UPLOAD_FOLDER'], potential_analysis_files[0])
            # Try to infer original filename (this is an approximation)
            original_filename_guess = potential_analysis_files[0].replace(f"_{session_id}_analysis.txt", "").replace("_analysis.txt", "")
            if not original_filename_guess: # If session ID was the only distinguishing part
                 original_filename_guess = potential_analysis_files[0].replace('_analysis.txt', '')


            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                analysis = f.read()
            return jsonify({
                'analysis': analysis,
                'filename': original_filename_guess, # This filename might not be the one from chat_sessions
                'session_id': session_id
            })
                
        return jsonify({'error': 'Analysis not found in active sessions or typical file locations for this session ID'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch/export-excel/<batch_id>', methods=['GET'])
def export_batch_excel(batch_id):
    """Export all completed analyses for a given batch_id to an Excel file."""
    try:
        # 1. Call the batch processor's /batch-status/<batch_id> endpoint
        batch_status_url = f"{app.config['BATCH_SERVICE_URL']}/batch-status/{batch_id}"
        response = requests.get(batch_status_url)
        
        if response.status_code != 200:
            return jsonify({'error': f'Failed to get batch status from processor: {response.text}'}), response.status_code
            
        batch_data = response.json()
        
        if not batch_data or 'job_statuses' not in batch_data:
            return jsonify({'error': 'Invalid batch status response from processor'}), 500
            
        job_statuses = batch_data.get('job_statuses', [])
        
        export_data = []
        
        # 2. Iterate through JobStatuses
        for job in job_statuses:
            if job.get('status') == 'completed' and job.get('analysis_id'):
                analysis_id = job.get('analysis_id')
                original_filename = job.get('file_name', f"video_{analysis_id}") # Fallback filename
                analysis_content = "Analysis not found"

                # Try to get analysis from Redis or in-memory fallback
                session_data = get_chat_session(analysis_id)

                if session_data:
                    # history will be a Python list from get_chat_session helper
                    history = session_data.get('history', [])
                    original_filename = session_data.get('filename', original_filename)

                    for message in history:
                        if message.get('role') == 'assistant':
                            analysis_content = message.get('content', "Analysis content missing.")
                            break
                else:
                    # If not in active sessions (Redis or in-memory), try the /video-analysis/<session_id> endpoint
                    analysis_response = get_video_analysis(analysis_id)
                    if analysis_response and analysis_response.status_code == 200:
                        analysis_data = analysis_response.get_json()
                        analysis_content = analysis_data.get('analysis', 'Failed to retrieve analysis via endpoint.')
                        # Update filename if the endpoint provided a more specific one
                        original_filename = analysis_data.get('filename', original_filename)
                    else:
                        # As a last resort, directly try to find the analysis file based on original_filename
                        # (The get_video_analysis might have already tried a variation of this)
                        analysis_file_name = f"{os.path.splitext(original_filename)[0]}_analysis.txt"
                        analysis_file_path = os.path.join(app.config['UPLOAD_FOLDER'], analysis_file_name)
                        if os.path.exists(analysis_file_path):
                            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                                analysis_content = f.read()
                        else:
                            # If original_filename_analysis.txt doesn't exist, try pattern with session_id
                            # This covers cases where filename might have been altered (e.g. by prepending session_id)
                            # This logic is similar to what's in get_video_analysis, but specific here
                            potential_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                               if f.endswith('_analysis.txt') and analysis_id in f]
                            if potential_files:
                                with open(os.path.join(app.config['UPLOAD_FOLDER'], potential_files[0]), 'r', encoding='utf-8') as f_alt:
                                    analysis_content = f_alt.read()
                                # original_filename from batch job is likely still the best reference
                            else:
                                analysis_content = f"Analysis for {original_filename} (ID: {analysis_id}) not found in memory or file system."
                
                export_data.append({
                    'Filename': original_filename,
                    'Analysis Result': analysis_content
                })

        if not export_data:
            return jsonify({'message': 'No completed analyses found for this batch to export.'}), 404

        # 3. Create an Excel file
        df = pd.DataFrame(export_data)
        
        output = io.BytesIO()
        # Use a context manager for the ExcelWriter to ensure it's closed properly
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Batch Analysis Results')
        output.seek(0)
        
        excel_filename = f"batch_{batch_id}_analysis_results.xlsx"
        
        # 4. Return the Excel file as a download
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=excel_filename # Use download_name for Flask 2.0+
        )

    except requests.RequestException as e:
        print(f"Error contacting batch processor for excel export: {str(e)}")
        return jsonify({'error': f'Could not connect to batch processing service: {str(e)}'}), 503
    except Exception as e:
        print(f"Error generating Excel export for batch {batch_id}: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask application...")
    # You can set this environment variable to disable reloading for troubleshooting
    use_reloader = os.environ.get('DISABLE_RELOADER', '').lower() != 'true'
    reloader_type = 'watchdog'  # More reliable than the default 'stat'
    
    try:
        import watchdog
        print(f"Using {reloader_type} reloader")
    except ImportError:
        reloader_type = 'stat'
        print(f"Watchdog not available, falling back to {reloader_type} reloader")
    
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False,
        use_reloader=use_reloader,
        reloader_type=reloader_type if use_reloader else None
    )