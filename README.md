# Video Analysis with GPT-4V

This application allows you to upload videos and get detailed analysis using OpenAI's GPT-4V (Vision) model. The application provides a modern web interface for uploading videos and displays the AI-generated analysis of the video content.

## Features

- Drag and drop video upload
- Support for multiple video formats (MP4, MOV, AVI, MKV)
- Real-time video analysis using GPT-4V
- Modern and responsive UI
- Detailed analysis of video content
- Batch processing of multiple videos
- Redis-based session storage

## Prerequisites

- Python 3.7 or higher (for local development)
- OpenAI API key with access to GPT-4V
- Docker and Docker Compose (for containerized deployment)

## Local Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Running Locally

1. Make sure your virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```
3. Open your web browser and navigate to `http://localhost:7081`

## Docker Deployment

The application is containerized and can be run using Docker Compose:

1. Make sure Docker and Docker Compose are installed on your system
2. Run the Docker build script:
```bash
./docker-build.sh your_openai_api_key
```
3. Access the application at `http://localhost:7080`

The Docker deployment includes:
- Web application (Flask) on port 7081
- Batch processor service (Go) on port 7082
- Redis for session storage
- Nginx as a reverse proxy on port 7080

## Architecture

The application consists of several components:
1. **Web Application (Flask)**: Handles video uploads, analysis, and user interface
2. **Batch Processor (Go)**: Processes multiple videos in parallel
3. **Redis**: Stores session data and chat history
4. **Nginx**: Routes requests to the appropriate service

## Usage

1. Open the application in your web browser
2. Drag and drop a video file onto the upload area or click to select a file
3. Wait for the analysis to complete
4. View the detailed analysis of your video
5. For batch processing, use the batch upload feature

## Notes

- Maximum video file size is 500MB
- Supported video formats: MP4, MOV, AVI, MKV
- The application stores uploaded videos in the `uploads` directory

## License

MIT License 