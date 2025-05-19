import os
import base64
import tempfile
import cv2
from flask import Flask, request, render_template, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
from PIL import Image
import io
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # Secret key for sessions
# Simple CORS configuration
CORS(app, supports_credentials=True)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# Store chat sessions (in-memory for development, use a database in production)
chat_sessions = {}

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
            
            # Extract frames from the video
            frames, timestamps, duration = extract_frames(filepath, num_frames=5)
            
            # Format timestamps as mm:ss
            formatted_timestamps = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in timestamps]
            
            # Prepare message content for GPT-4 Vision
            message_content = [
                {
                    "type": "text", 
                    "text": f"I'm sending you 5 frames from a video named '{filename}' with a duration of {int(duration // 60):02d}:{int(duration % 60):02d}. "
                           f"The frames were taken at the following timestamps: {', '.join(formatted_timestamps)}. "
                           f"Please analyze these frames and provide a comprehensive analysis of what is happening in this video. "
                           f"Describe the scenes, actions, people, objects, and any other notable elements visible in the frames. always include the overall summary of the video in the analysis"
                }
            ]
            
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
                "content": "You are a video analysis expert. Your task is to analyze frames from a video and provide a comprehensive description of what is happening in the video. always include the overall summary of the video in the analysis"
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
            chat_sessions[session_id] = {
                "frames": frames,
                "timestamps": formatted_timestamps,
                "filename": filename,
                "duration": duration,
                "history": [
                    system_message,
                    user_message,
                    {"role": "assistant", "content": assistant_response}
                ]
            }
            
            # Store video frames for reuse
            temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_frames.mp4")
            cv2.VideoCapture(filepath).release()  # Close the video file
            os.rename(filepath, temp_file_path)  # Rename to session ID
            
            # Clean up the uploaded file after processing
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return jsonify({
                'analysis': assistant_response,
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
    if not session_id or session_id not in chat_sessions:
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
                
                # Extract frames from the video
                frames, timestamps, duration = extract_frames(filepath, num_frames=5)
                formatted_timestamps = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in timestamps]
                
                # Initialize the chat session
                chat_sessions[session_id] = {
                    "frames": frames,
                    "timestamps": formatted_timestamps,
                    "filename": filename,
                    "duration": duration,
                    "history": [
                        {
                            "role": "system",
                            "content": "You are a video analysis expert. Your task is to analyze frames from a video and respond to the user's specific questions or follow their custom instructions about the video content."
                        }
                    ]
                }
                
                # Store video frames for reuse
                temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_frames.mp4")
                cv2.VideoCapture(filepath).release()  # Close the video file
                os.rename(filepath, temp_file_path)  # Rename to session ID
                
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
    session_data = chat_sessions[session_id]
    
    # Prepare message content for GPT-4 Vision with custom prompt
    message_content = [
        {
            "type": "text", 
            "text": f"Regarding the video '{session_data['filename']}' with duration {int(session_data['duration'] // 60):02d}:{int(session_data['duration'] % 60):02d}, here's a new question or instruction from the user: \n\n{custom_prompt}"
        }
    ]
    
    # Add frames only for the first few custom prompts to avoid context length issues
    if len(session_data['history']) < 8:  # Only include frames for first few interactions
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
    session_data['history'].append({
        "role": "user",
        "content": message_content
    })
    
    # Get analysis from GPT-4 Vision with conversation history
    try:
        # Only use last 10 messages to avoid exceeding context limits
        recent_history = session_data['history'][-10:] if len(session_data['history']) > 10 else session_data['history']
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=recent_history,
            max_tokens=1500
        )
        
        # Add assistant's response to history
        assistant_response = response.choices[0].message.content
        session_data['history'].append({
            "role": "assistant",
            "content": assistant_response
        })
        
        return jsonify({
            'analysis': assistant_response,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error in GPT processing: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask application...")  # Debug print
    app.run(host='127.0.0.1', port=8080, debug=True)