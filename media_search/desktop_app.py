#!/usr/bin/env python3
"""
Desktop Media Search Application
A desktop wrapper for the MediaSearch web interface using webview.
"""

import os
import sys
import threading
import time
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import webview
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install pywebview")
    import webview

from app import app, search_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaSearchDesktopApp:
    def __init__(self):
        self.flask_thread = None
        self.flask_port = 5002  # Changed from 5001 to 5002 to avoid Docker conflict
        self.app_title = "MediaSearch - AI-Powered Media Discovery (Desktop)"
        self.app_width = 1200
        self.app_height = 800
        
    def start_flask_server(self):
        """Start the Flask server in a separate thread."""
        try:
            # Run Flask in debug=False mode for desktop
            app.run(
                host='127.0.0.1',
                port=self.flask_port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Failed to start Flask server: {e}")
            
    def wait_for_server(self, timeout=30):
        """Wait for Flask server to start."""
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f'http://127.0.0.1:{self.flask_port}/health')
                if response.status_code == 200:
                    logger.info("Flask server is ready")
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(0.5)
                
        logger.error("Flask server failed to start within timeout")
        return False
        
    def create_window(self):
        """Create the main application window."""
        url = f'http://127.0.0.1:{self.flask_port}/'
        
        # Create the webview window
        window = webview.create_window(
            title=self.app_title,
            url=url,
            width=self.app_width,
            height=self.app_height,
            min_size=(800, 600),
            resizable=True,
            fullscreen=False,
            shadow=True,
            on_top=False,
            text_select=True
        )
        
        return window
        
    def run(self):
        """Run the desktop application."""
        logger.info("Starting MediaSearch Desktop Application...")
        logger.info(f"Desktop app will run on port {self.flask_port}")
        
        # Start Flask server in background thread
        self.flask_thread = threading.Thread(target=self.start_flask_server, daemon=True)
        self.flask_thread.start()
        
        # Wait for server to be ready
        if not self.wait_for_server():
            logger.error("Failed to start application - server not ready")
            return
            
        # Create and show the main window
        window = self.create_window()
        
        logger.info("Application window created, starting webview...")
        
        # Start the webview (this blocks until window is closed)
        webview.start(
            debug=False,
            menu=[],
            server='threaded'
        )
        
        logger.info("Application closed")

def main():
    """Main entry point for the desktop application."""
    try:
        app_instance = MediaSearchDesktopApp()
        app_instance.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 