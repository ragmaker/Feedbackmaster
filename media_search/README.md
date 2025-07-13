# Media Search Service

A complete Python-based semantic search service for media analysis data with dual vector search capabilities using FAISS and SentenceTransformers.

## Features

- **Dual Vector Search**: Separate indexes for summary and frame detail embeddings
- **Multi-user Support**: User isolation with configurable private/shared index modes
- **RESTful API**: Complete CRUD operations for users and files
- **Semantic Search**: Uses `all-MiniLM-L6-v2` SentenceTransformer for embeddings
- **FAISS Integration**: Efficient similarity search with IndexFlatIP
- **SQLite Storage**: Lightweight metadata storage with full schema
- **Docker Support**: Containerized deployment with docker-compose
- **Comprehensive Testing**: Full workflow test suite with hardcoded test data

## Architecture

```
media_search/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── run_tests.py          # Test runner script
├── README.md             # This file
├── data/                 # Data directory (created at runtime)
│   ├── indexes/          # FAISS index files
│   └── semantic_search.db # SQLite database
└── tests/
    └── test_full_workflow.py # Comprehensive test suite
```

## Database Schema

### Users Table
- `user_id` (TEXT PRIMARY KEY)
- `username` (TEXT UNIQUE)
- `index_mode` (TEXT DEFAULT 'private') - 'private' or 'shared'
- `created_at` (TIMESTAMP)

### File Metadata Table
- `file_id` (TEXT PRIMARY KEY)
- `user_id` (TEXT FOREIGN KEY)
- `filename` (TEXT)
- `summary_text` (TEXT)
- `frame_details` (TEXT)
- `duration`, `format`, `resolution`, `owner`, `topic`, `tags`
- `upload_date`, `created_at`, `updated_at`

### Indexing Status Table
- Tracks FAISS indexing status per file
- Maps file_id to vector_id for retrieval

### User Index Mapping Table
- Maps users to their FAISS index files
- Supports both private and shared index modes

## FAISS Index Architecture

### Index Types
- **Summary Indexes**: `{user_id}_summary_faiss.bin` or `shared_summary_faiss.bin`
- **Frame Indexes**: `{user_id}_frame_faiss.bin` or `shared_frame_faiss.bin`

### Index Modes
- **Private**: Each user has their own FAISS indexes
- **Shared**: All users share common FAISS indexes

## API Endpoints

### User Management
- `POST /api/users` - Create new user
- `GET /api/users/{user_id}` - Get user details
- `PUT /api/users/{user_id}` - Update user settings

### File Management
- `POST /api/files` - Add single file
- `POST /api/files/batch` - Add multiple files
- `GET /api/files?user_id={user_id}` - List user's files
- `GET /api/files/{file_id}?user_id={user_id}` - Get file details
- `PUT /api/files/{file_id}` - Update file metadata
- `DELETE /api/files/{file_id}` - Delete file

### Search
- `GET /api/search/summary?q={query}&user_id={user_id}` - Search summaries
- `GET /api/search/frames?q={query}&user_id={user_id}` - Search frame details
- `GET /api/search/combined?q={query}&user_id={user_id}` - Search both indexes

### System
- `GET /api/stats` - Get service statistics
- `GET /health` - Health check endpoint

## Usage Examples

### Create User
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "index_mode": "private"
  }'
```

### Add File
```bash
curl -X POST http://localhost:5000/api/files \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "nature_doc_001",
    "user_id": "user123",
    "filename": "amazon_rainforest.mp4",
    "summary_text": "A breathtaking documentary about the Amazon rainforest...",
    "frame_details": "Opening scene: Aerial view of endless green canopy...",
    "analysis_metadata": {
      "duration": 240,
      "format": "mp4",
      "resolution": "4K",
      "owner": "nature_productions",
      "topic": "nature_documentary",
      "tags": ["wildlife", "amazon", "conservation"]
    }
  }'
```

### Search
```bash
# Search summaries
curl "http://localhost:5000/api/search/summary?q=amazon%20rainforest&user_id=user123"

# Search frame details
curl "http://localhost:5000/api/search/frames?q=jaguar%20forest&user_id=user123"

# Combined search
curl "http://localhost:5000/api/search/combined?q=wildlife%20documentary&user_id=user123"
```

## Deployment

### Using Docker Compose (Recommended)

1. From the main project directory:
```bash
# Build and start all services
docker-compose up --build

# Or start only media_search service
docker-compose up --build media_search
```

2. The service will be available at `http://localhost:5001`

### Manual Installation

1. Install dependencies:
```bash
cd media_search
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DB_PATH=data/semantic_search.db
export DEFAULT_INDEX_MODE=private
export MODEL_NAME=all-MiniLM-L6-v2
```

3. Run the service:
```bash
python app.py
```

## Testing

### Run Comprehensive Tests
```bash
cd media_search
python run_tests.py
```

### Manual Testing
```bash
# Run the full test suite directly
python tests/test_full_workflow.py --url http://localhost:5000 --wait 10
```

### Test Coverage
The test suite includes:
- Health check verification
- User creation and management
- Single and batch file addition
- File retrieval and listing
- All search endpoint testing
- File update and deletion
- Error handling validation
- Service statistics verification

## Configuration

### Environment Variables
- `DB_PATH`: Path to SQLite database (default: `data/semantic_search.db`)
- `DEFAULT_INDEX_MODE`: Default index mode for new users (default: `private`)
- `MODEL_NAME`: SentenceTransformer model name (default: `all-MiniLM-L6-v2`)
- `FLASK_ENV`: Flask environment (default: `production`)

### Model Information
- **Model**: `all-MiniLM-L6-v2`
- **Embedding Dimension**: 384
- **Similarity Metric**: Cosine similarity (via IndexFlatIP)
- **CPU Only**: No GPU required

## Performance Considerations

### FAISS Indexes
- Uses `IndexFlatIP` for exact similarity search
- Embeddings are normalized for cosine similarity
- Indexes are persisted to disk for durability
- No vector deletion support (FAISS limitation)

### Scaling
- Supports horizontal scaling with shared index mode
- Private index mode provides user isolation
- SQLite is suitable for moderate workloads
- Consider PostgreSQL for high-volume deployments

## Limitations

1. **Vector Deletion**: FAISS doesn't support vector deletion; periodic index rebuilding required
2. **SQLite**: Single-writer limitation for high-concurrency scenarios
3. **Memory Usage**: All vectors loaded in memory for search
4. **Model Loading**: Initial startup time for model download

## Security Notes

- No authentication implemented (first iteration)
- User isolation via `user_id` parameter
- File access control through user verification
- Consider adding JWT authentication for production use

## Development

### Project Structure
```
media_search/
├── app.py                 # Main application with DualVectorSearchService
├── requirements.txt       # Dependencies
├── Dockerfile            # Container configuration
├── run_tests.py          # Test runner
├── data/                 # Runtime data directory
│   ├── indexes/          # FAISS index files
│   └── semantic_search.db # SQLite database
└── tests/
    └── test_full_workflow.py # Comprehensive tests
```

### Key Classes
- `DualVectorSearchService`: Main service class
- Database management with SQLite
- FAISS index handling
- Flask REST API endpoints

## Troubleshooting

### Common Issues

1. **Model Download Failure**
   - Ensure internet connection for initial model download
   - Check disk space for model cache

2. **FAISS Import Error**
   - Verify `faiss-cpu` installation
   - Check Python version compatibility

3. **Database Locked**
   - Ensure proper database connection handling
   - Check file permissions on data directory

4. **Search Returns No Results**
   - Verify files are properly indexed
   - Check user_id parameter in requests
   - Ensure embeddings were generated successfully

### Logs
- Check application logs for detailed error messages
- Enable debug mode for development: `FLASK_ENV=development`

## Future Enhancements

- JWT authentication and authorization
- PostgreSQL support for production
- Advanced search features (filtering, faceting)
- Bulk operations for large datasets
- Monitoring and metrics dashboard
- Index optimization and rebuilding tools 