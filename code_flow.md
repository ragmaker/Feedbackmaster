# FeedbackMaster Application Code Flow

## Overview
FeedbackMaster is a Flask-based web application that processes video uploads and provides AI-powered analysis using GPT-4 Vision. The application maintains stateful sessions for efficient video processing and analysis.

## Application Architecture

### 1. Core Components
- **Flask Application**: Main web server
- **OpenAI Integration**: GPT-4 Vision API for video analysis
- **Session Management**: In-memory session storage
- **File Processing**: Video frame extraction and management

### 2. Key Dependencies
```python
- Flask: Web framework
- OpenAI: GPT-4 Vision API client
- OpenCV (cv2): Video processing
- PIL: Image processing
- Flask-CORS: Cross-origin resource sharing
```

## Detailed Code Flow

### 1. Application Initialization
```python
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
CORS(app, supports_credentials=True)
```
- Initializes Flask application
- Sets up secret key for sessions
- Configures CORS for cross-origin requests

### 2. Video Upload Process (`/upload` endpoint)

#### 2.1 Initial Upload
1. Receives video file through POST request
2. Validates file type and size
3. Generates unique session ID (UUID)
4. Processes video:
   - Extracts frames (8 frames by default)
   - Converts frames to base64
   - Stores frames in session

#### 2.2 Frame Extraction
```python
def extract_frames(video_path, num_frames=5):
    # Opens video file
    # Calculates frame intervals
    # Extracts frames at regular intervals
    # Converts frames to base64
    # Returns frames, timestamps, and duration
```

#### 2.3 Session Storage
```python
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
```

### 3. Custom Analysis Process (`/custom_analysis` endpoint)

#### 3.1 Request Handling
1. Receives custom prompt and session ID
2. Validates session existence
3. Two possible paths:
   - With session ID: Uses stored frames
   - Without session ID: Processes new video upload

#### 3.2 GPT-4 Vision Integration
1. Prepares message content:
   - System message (context)
   - User message (with frames)
   - Custom prompt
2. Sends request to GPT-4 Vision API
3. Processes and returns response

### 4. State Management

#### 4.1 Session Storage
- In-memory dictionary `chat_sessions`
- Key: Session ID (UUID)
- Value: Session data (frames, history, etc.)

#### 4.2 File Storage
- Videos stored in `uploads` directory
- Named as `{session_id}_frames.mp4`
- Temporary storage for processing

### 5. PDF Export Process (`/export-pdf` endpoint)
1. Receives session ID
2. Retrieves analysis history
3. Generates PDF with analysis
4. Returns PDF file

## Data Flow

### 1. Video Upload Flow
```
Client -> Upload Video -> Server
  -> Validate File
  -> Generate Session ID
  -> Extract Frames
  -> Store in Session
  -> Return Session ID
```

### 2. Analysis Flow
```
Client -> Custom Analysis Request -> Server
  -> Validate Session
  -> Retrieve Frames
  -> Prepare GPT Request
  -> Get Analysis
  -> Update Session History
  -> Return Analysis
```

### 3. PDF Export Flow
```
Client -> Export Request -> Server
  -> Retrieve Session Data
  -> Generate PDF
  -> Return PDF File
```

## Security Considerations

### 1. File Validation
- File type checking
- File size limits
- Secure filename handling

### 2. Session Management
- UUID-based session IDs
- In-memory session storage
- Session validation

### 3. API Security
- Environment variable configuration
- API key management
- CORS configuration

## Performance Optimizations

### 1. Video Processing
- Frame extraction at intervals
- Image resizing for efficiency
- Base64 encoding for API transmission

### 2. State Management
- In-memory session storage
- Efficient frame storage
- Session-based video reuse

## Limitations and Future Improvements

### 1. Current Limitations
- In-memory session storage (lost on server restart)
- Local file storage
- Single-server architecture

### 2. Potential Improvements
1. Database Integration
   - Persistent session storage
   - Better scalability
   - Session expiration

2. Cloud Storage
   - S3 or similar for video storage
   - CDN integration
   - Better file management

3. Scalability
   - Multiple server instances
   - Load balancing
   - Redis for session management

4. Security Enhancements
   - Rate limiting
   - Better authentication
   - File encryption

## Error Handling

### 1. File Processing Errors
- Invalid file types
- File size limits
- Processing failures

### 2. API Errors
- OpenAI API failures
- Rate limiting
- Invalid responses

### 3. Session Errors
- Invalid session IDs
- Missing data
- Expired sessions 