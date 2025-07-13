# MediaSearch - AI-Powered Media Discovery Interface

A modern, glassmorphism-styled media search interface that provides natural language search capabilities for your media files. Available as both a web application and a native desktop application.

## ✨ Features

### 🔍 **Smart Search**
- **Natural Language Queries**: Search using plain English like "sunset photos" or "meeting recordings"
- **AI-Powered**: Leverages sentence transformers and FAISS for semantic search
- **Real-time Results**: Instant search results with relevance scoring
- **Combined Search**: Searches both file summaries and frame details

### 🎨 **Modern Design**
- **Glassmorphism Effects**: Beautiful backdrop blur and translucent elements
- **Soft Color Palette**: Soothing blues, purples, and slate tones
- **Responsive Layout**: Works perfectly on both desktop and mobile
- **Dark Theme**: Eye-friendly design optimized for extended use

### 📱 **Flexible Views**
- **Grid View**: Compact thumbnail grid with 2-3 columns
- **List View**: Detailed list format with expanded information
- **Modal Preview**: Click to preview/play media files
- **Sorting Options**: Sort by relevance, date, name, or size

### 🖥️ **Cross-Platform**
- **Web Application**: Access via browser at `http://localhost:5001`
- **Desktop Application**: Native app experience using PyWebView
- **Responsive Design**: Optimized for various screen sizes

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Option 1: Interactive Launcher (Recommended)
```bash
# Run the interactive launcher
python launch_media_search.py

# Choose between:
# 1. Web Version (Browser-based)
# 2. Desktop Version (Native app)
```

### Option 2: Direct Launch
```bash
# Web version
python launch_media_search.py web

# Desktop version
python launch_media_search.py desktop
```

### Option 3: Manual Launch
```bash
# Web version - Start Flask server
python app.py
# Then open browser to http://localhost:5001

# Desktop version - Run desktop app directly
python desktop_app.py
```

## 🎯 Usage Guide

### **Search Interface**
1. **Natural Language Search**: Type queries like:
   - "beach vacation photos"
   - "quarterly meeting recordings"
   - "landscape photography sunset"
   - "product demo videos"

2. **View Toggle**: Switch between grid and list views
3. **Sort Options**: Order results by relevance, date, name, or size
4. **File Count**: See total indexed files in the header

### **Media Preview**
- **Click any media item** to open the preview modal
- **Supported Media Types**:
  - 🎥 **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
  - 🎵 **Audio**: MP3, WAV, FLAC, AAC, OGG, WMA
  - 🖼️ **Images**: JPG, PNG, GIF, BMP, SVG, WebP
  - 📄 **Documents**: PDF, DOC, TXT, and others

### **Modal Features**
- **Media Player**: Built-in video/audio player with controls
- **Image Viewer**: High-quality image display
- **File Details**: Complete metadata information
- **Actions**: Copy file path or open in default application

## 📐 Technical Architecture

### **Frontend Components**
- **HTML5**: Semantic structure with modern elements
- **CSS3**: Advanced styling with glassmorphism effects
- **JavaScript**: Vanilla JS for optimal performance
- **Responsive Design**: Mobile-first approach

### **Backend Integration**
- **Flask API**: RESTful endpoints for data retrieval
- **Semantic Search**: AI-powered content understanding
- **SQLite Database**: Efficient metadata storage
- **FAISS Indexing**: Fast similarity search

### **Desktop Integration**
- **PyWebView**: Native desktop wrapper
- **Thread Management**: Separate Flask server thread
- **Cross-Platform**: Works on Windows, macOS, Linux

## 🛠️ Configuration

### **Environment Variables**
```bash
# Optional configuration in .env file
DB_PATH=data/semantic_search.db
FILE_PATH_BASE=/path/to/your/media/files
MODEL_NAME=all-MiniLM-L6-v2
MIN_SIMILARITY_SCORE=0.2
```

### **Customization Options**
- **Color Scheme**: Modify CSS variables in `media_search.html`
- **Layout**: Adjust grid columns and spacing
- **Search Parameters**: Configure relevance thresholds
- **Window Size**: Desktop app dimensions in `desktop_app.py`

## 📁 File Structure

```
media_search/
├── templates/
│   ├── media_search.html      # Main UI interface
│   └── db_viewer.html         # Database viewer
├── app.py                     # Flask backend
├── desktop_app.py             # Desktop application
├── launch_media_search.py     # Application launcher
├── requirements.txt           # Python dependencies
└── data/                      # Database and indexes
```

## 🔧 API Endpoints

### **Search Endpoints**
- `GET /api/search/combined?q=<query>&user_id=<id>&top_k=<limit>`
- `GET /api/search/summary?q=<query>&user_id=<id>&top_k=<limit>`
- `GET /api/search/frames?q=<query>&user_id=<id>&top_k=<limit>`

### **File Management**
- `GET /api/files?user_id=<id>&limit=<limit>&offset=<offset>`
- `GET /api/files/<file_id>?user_id=<id>`
- `POST /api/files` - Add new file
- `PUT /api/files/<file_id>` - Update file
- `DELETE /api/files/<file_id>` - Delete file

### **System**
- `GET /api/stats` - System statistics
- `GET /health` - Health check
- `GET /` - Main interface
- `GET /db` - Database viewer

## 🎨 Design Specifications

### **Color Palette**
- **Primary**: Gradient from `#667eea` to `#764ba2`
- **Glass Effects**: `rgba(255, 255, 255, 0.1)` with backdrop blur
- **Text**: `#1f2937` (dark) and `#6b7280` (medium)
- **Background**: Linear gradient blues and purples

### **Typography**
- **Font Family**: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif
- **Headings**: 16px-28px, weight 600-700
- **Body Text**: 14px-16px, weight 400
- **Metadata**: 12px-14px, weight 400

### **Layout**
- **Grid**: Auto-fill columns, 280px minimum width
- **Spacing**: 15px-30px between elements
- **Border Radius**: 10px-50px for various elements
- **Shadows**: Multiple levels with rgba(0,0,0,0.1-0.3)

## 🔍 Troubleshooting

### **Common Issues**

1. **Search Not Working**
   - Check if backend server is running
   - Verify database has indexed files
   - Ensure proper user_id parameter

2. **Media Files Not Playing**
   - Verify file paths are correct
   - Check browser media support
   - Ensure file permissions

3. **Desktop App Not Starting**
   - Install PyWebView: `pip install pywebview`
   - Check for port conflicts (5001)
   - Verify Python dependencies

### **Performance Tips**
- **File Indexing**: Ensure all media files are properly indexed
- **Search Optimization**: Use specific terms for better results
- **Browser Cache**: Clear cache if UI updates don't appear
- **Memory Usage**: Desktop app uses ~100MB RAM

## 🚀 Advanced Features

### **Keyboard Shortcuts**
- **Enter**: Perform search
- **Escape**: Close modal
- **Ctrl+F**: Focus search input (browser)

### **Search Tips**
- Use descriptive terms: "beach sunset" vs "photo"
- Combine concepts: "birthday party children"
- Include context: "office meeting presentation"
- Try synonyms: "car, vehicle, automobile"

### **File Organization**
- Group related files in folders
- Use descriptive filenames
- Add metadata during upload
- Regular reindexing for best results

## 📄 License

This project is part of the Feedbackmaster media search system. Please refer to the main project license for usage terms.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request with description

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the project repository
4. Contact the development team

---

**🎉 Enjoy your AI-powered media discovery experience!** 