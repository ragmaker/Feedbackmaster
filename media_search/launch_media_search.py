#!/usr/bin/env python3
"""
MediaSearch Application Launcher
Choose between web and desktop versions of the media search interface.
"""

import sys
import os
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def launch_web_version():
    """Launch the web version of MediaSearch."""
    logger.info("Starting MediaSearch Web Version...")
    logger.info("Access the application at: http://localhost:5001")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        from app import app
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")

def launch_desktop_version():
    """Launch the desktop version of MediaSearch."""
    logger.info("Starting MediaSearch Desktop Version...")
    
    try:
        from desktop_app import MediaSearchDesktopApp
        app_instance = MediaSearchDesktopApp()
        app_instance.run()
    except ImportError as e:
        logger.error("Desktop dependencies not installed. Please run: pip install pywebview")
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start desktop application: {e}")
        sys.exit(1)

def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="MediaSearch Application Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_media_search.py web      # Launch web version
  python launch_media_search.py desktop  # Launch desktop version
  python launch_media_search.py          # Interactive mode
        """
    )
    
    parser.add_argument(
        'mode', 
        nargs='?', 
        choices=['web', 'desktop', 'interactive'],
        default='interactive',
        help='Launch mode: web, desktop, or interactive (default: interactive)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        launch_web_version()
    elif args.mode == 'desktop':
        launch_desktop_version()
    else:
        # Interactive mode
        print("\n" + "="*50)
        print("   MediaSearch - AI-Powered Media Discovery")
        print("="*50)
        print("\nChoose your preferred launch mode:")
        print("1. Web Version (Browser-based)")
        print("2. Desktop Version (Native app)")
        print("3. Exit")
        print("-" * 50)
        
        while True:
            try:
                choice = input("\nEnter your choice (1-3): ").strip()
                
                if choice == '1':
                    launch_web_version()
                    break
                elif choice == '2':
                    launch_desktop_version()
                    break
                elif choice == '3':
                    print("Goodbye!")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main() 