# Video Analysis with GPT-4V

This application allows you to upload videos and get detailed analysis using OpenAI's GPT-4V (Vision) model. The application provides a modern web interface for uploading videos and displays the AI-generated analysis of the video content.

## Features

- Drag and drop video upload
- Support for multiple video formats (MP4, MOV, AVI, MKV)
- Real-time video analysis using GPT-4V
- Modern and responsive UI
- Detailed analysis of video content

## Prerequisites

- Python 3.7 or higher
- OpenAI API key with access to GPT-4V

## Setup

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

## Running the Application

1. Make sure your virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```
3. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. Open the application in your web browser
2. Drag and drop a video file onto the upload area or click to select a file
3. Wait for the analysis to complete
4. View the detailed analysis of your video

## Notes

- Maximum video file size is 100MB
- Supported video formats: MP4, MOV, AVI, MKV
- The application temporarily stores uploaded videos in the `uploads` directory and automatically deletes them after processing

## License

MIT License 