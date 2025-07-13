#!/bin/bash

# MediaSearch Application Launcher Script
# Provides easy installation and launching of the media search interface

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
VENV_DIR="$SCRIPT_DIR/venv"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Python is available
check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    local python_version=$($PYTHON_CMD --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
    local major_version=$(echo $python_version | cut -d'.' -f1)
    local minor_version=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 8 ]); then
        print_error "Python 3.8 or higher is required (found $python_version)"
        exit 1
    fi
    
    print_success "Python $python_version found"
}

# Function to setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    print_status "Installing dependencies..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    
    print_success "Dependencies installed"
}

# Function to launch web version
launch_web() {
    print_status "Starting MediaSearch Web Version..."
    print_status "Access the application at: http://localhost:5001"
    print_status "Press Ctrl+C to stop the server"
    
    cd "$SCRIPT_DIR"
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    fi
    
    $PYTHON_CMD launch_media_search.py web
}

# Function to launch desktop version
launch_desktop() {
    print_status "Starting MediaSearch Desktop Version..."
    
    cd "$SCRIPT_DIR"
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    fi
    
    $PYTHON_CMD launch_media_search.py desktop
}

# Function to launch interactive mode
launch_interactive() {
    print_status "Starting MediaSearch Interactive Mode..."
    
    cd "$SCRIPT_DIR"
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    fi
    
    $PYTHON_CMD launch_media_search.py
}

# Function to show help
show_help() {
    echo "MediaSearch Application Launcher"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  install      Install dependencies and setup environment"
    echo "  web          Launch web version (browser-based)"
    echo "  desktop      Launch desktop version (native app)"
    echo "  interactive  Launch interactive mode (default)"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install     # First-time setup"
    echo "  $0 web         # Launch web version"
    echo "  $0 desktop     # Launch desktop version"
    echo "  $0             # Interactive mode"
    echo ""
    echo "For more information, see MEDIA_SEARCH_UI_README.md"
}

# Function to install and setup
install_setup() {
    print_status "Installing MediaSearch..."
    
    check_python
    setup_venv
    
    print_success "Installation complete!"
    print_status "You can now run: $0 web, $0 desktop, or $0 interactive"
}

# Function to check if installation is needed
check_installation() {
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
        print_warning "Virtual environment not found. Running installation..."
        install_setup
    fi
}

# Main function
main() {
    cd "$SCRIPT_DIR"
    
    case "${1:-interactive}" in
        install)
            install_setup
            ;;
        web)
            check_installation
            launch_web
            ;;
        desktop)
            check_installation
            launch_desktop
            ;;
        interactive)
            check_installation
            launch_interactive
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Trap Ctrl+C
trap 'print_status "Shutting down..."; exit 0' INT

# Run main function
main "$@" 