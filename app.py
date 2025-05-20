import os
import base64
import tempfile
import cv2
from flask import Flask, request, render_template, jsonify, send_from_directory, session, make_response
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
from PIL import Image
import io
import uuid
from datetime import datetime

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
                           f"Structure your response with the TECHNICAL SUMMARY first, followed by a NARRATED SUMMARY, and finally the DETAILED ANALYSIS OF THE VIDEO FRAMES."
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
                "content": "You are a comprehensive video analysis expert with exceptional attention to accuracy and fine details. Your task is to analyze frames from a video with extremely high precision. \n\nFor all identifications, especially animals, vehicles, and objects:\n1. Take extra time to verify species, breeds, makes and models before stating them\n2. Look carefully at distinguishing features (e.g., elephant trunks vs buffalo horns, ear shapes, body proportions)\n3. If uncertain about an identification, describe the features you see and provide possible options rather than making a definitive but potentially incorrect statement\n4. Use taxonomic precision (correct species names) when identifying animals\n5. If image quality makes identification difficult, explicitly state this limitation\n\nOrganize your response in the following order:\n\n1. **TECHNICAL SUMMARY:** Provide a concise, factual summary of what is happening in the video. Focus on objective observations, counts, and key events in a straightforward manner. Keep this section brief and informative.\n\n2. **NARRATED SUMMARY:** Present the video content in an engaging, narrative style as if you were a documentary narrator. Use vivid language and natural storytelling techniques while maintaining factual accuracy. Make this section come alive for someone who hasn't seen the video.\n\n3. **DETAILED ANALYSIS OF THE VIDEO FRAMES:** In this section, include your comprehensive analysis with all details:\n   - Exact counts of people, animals, vehicles, and other key objects\n   - Specific colors of important elements (clothing, vehicles, backgrounds, etc.)\n   - Precise spatial relationships between objects\n   - Detailed descriptions of actions and movements\n   - Object characteristics like size, shape, brand, model when possible\n   - Environmental details (indoor/outdoor, lighting, weather if applicable)\n   - Text content visible in the frames\n\nPrioritize accuracy over comprehensiveness when necessary - it's better to be tentative but accurate than confident but wrong."
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
                "additional_context": additional_context if additional_context else None,  # Store the additional context
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
                
                # Extract frames from the video - use 8 frames for better accuracy
                frames, timestamps, duration = extract_frames(filepath, num_frames=8)
                formatted_timestamps = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in timestamps]
                
                # Get additional context if provided
                additional_context = request.form.get('additional_context', '').strip()
                
                # Initialize the chat session
                chat_sessions[session_id] = {
                    "frames": frames,
                    "timestamps": formatted_timestamps,
                    "filename": filename,
                    "duration": duration,
                    "additional_context": additional_context if additional_context else None,  # Store the additional context
                    "history": [
                        {
                            "role": "system",
                            "content": "You are a detailed video analysis expert with an exceptional commitment to accuracy. Your task is to analyze frames from a video and respond to the user's specific questions or follow their custom instructions about the video content. \n\nWhen identifying elements in the video:\n1. Be extremely careful with taxonomic classifications of animals - verify identifying features (trunks, horns, ears, etc.) before naming a species\n2. Distinguish carefully between similar-looking objects (e.g., elephant vs. buffalo, tiger vs. lion, car models)\n3. When uncertain, describe visual features and possible identifications rather than making definitive statements\n4. Consider image quality and viewing angle in your confidence level\n\nWhen providing a complete analysis, structure your response in this exact order:\n\n1. **TECHNICAL SUMMARY:** Brief, factual overview of the video content with key observations\n\n2. **NARRATED SUMMARY:** An engaging, narrative description of the video in a documentary-style voice\n\n3. **DETAILED ANALYSIS OF THE VIDEO FRAMES:** Comprehensive breakdown including:\n   - Count specific objects (people, vehicles, animals, items) and report exact numbers\n   - Describe precise colors of all important elements\n   - Identify brands, models, and specific types of objects when confident, otherwise describe features\n   - Notice text visible in the frames and report it accurately\n   - Pay careful attention to spatial relationships and compositions\n   - Describe actions in detail, including subtle movements\n   - Note environmental details (location type, weather, lighting)\n\nAim for 100% accuracy in your descriptions, even if it means being more tentative in some identifications."
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
                "text": f"Please carefully verify the animal species in the video. This is a specific request to double-check animal identification. Focus on clear taxonomic identification based on visible features.\n\nUser query: {custom_prompt}\n\nStructure your response with these sections in order:\n\n1. **TECHNICAL SUMMARY:** Brief identification of the animals with taxonomic precision\n\n2. **NARRATED SUMMARY:** Describe the animals in a naturalist style\n\n3. **DETAILED ANALYSIS:** When identifying animals:\n   - Look for distinctive features (trunk, horns, ears, tails, etc.)\n   - Compare size and proportions\n   - Note coloration patterns and textures\n   - Observe behaviors if visible\n   - Provide taxonomic details when possible\n   - If uncertain between species (like elephant vs buffalo), explain why and provide visual evidence for your conclusion"
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
                "text": f"Please provide a narrated summary of the video in the style of a {narrative_style}. Create a vivid, expressive narration that brings the video content to life while maintaining factual accuracy.\n\nUser request: {custom_prompt}\n\nEven if just creating a narrated version, structure your response with a TECHNICAL SUMMARY first, followed by your NARRATED SUMMARY, and if needed, a brief DETAILED ANALYSIS section. Use descriptive language, natural transitions, and an engaging tone appropriate for the requested style."
            }
        ]
    else:
        # Regular custom prompt
        message_content = [
            {
                "type": "text", 
                "text": f"Regarding the video '{session_data['filename']}' with duration {int(session_data['duration'] // 60):02d}:{int(session_data['duration'] % 60):02d}, here's a new question or instruction from the user: \n\n{custom_prompt}"
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
    session_data['history'].append({
        "role": "user",
        "content": message_content
    })
    
    # Get analysis from GPT-4 Vision with conversation history
    try:
        # Only use last 10 messages to avoid exceeding context limits
        recent_history = session_data['history'][-10:] if len(session_data['history']) > 10 else session_data['history']
        
        # If animal verification or narration, boost max tokens for detailed response
        max_tokens = 2000 if (is_animal_verification or is_narration_request) else 1500
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=recent_history,
            max_tokens=max_tokens
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

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    if 'content' not in request.form:
        return jsonify({'error': 'No content provided'}), 400
    
    content = request.form['content']
    title = request.form.get('title', 'Video Analysis Report')
    
    try:
        # Create HTML content
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
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div class="no-print">
                    <p>To save as PDF, use your browser's print function (Ctrl+P or Cmd+P) and select "Save as PDF".</p>
                    <button onclick="window.print()" style="padding: 8px 16px; background-color: #4338ca; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;">Print / Save as PDF</button>
                </div>
            </div>
            <div class="content">
                {content.replace('\n', '<br>')}
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

if __name__ == '__main__':
    print("Starting Flask application...")  # Debug print
    app.run(host='127.0.0.1', port=8081, debug=True)