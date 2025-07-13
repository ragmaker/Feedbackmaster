import os
import sqlite3
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from flask import Flask, request, jsonify, g, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = os.getenv('DB_PATH', 'data/semantic_search.db')
DEFAULT_INDEX_MODE = os.getenv('DEFAULT_INDEX_MODE', 'private')
MODEL_NAME = os.getenv('MODEL_NAME', 'all-MiniLM-L6-v2')
FILE_PATH_BASE = os.getenv('FILE_PATH_BASE', '/Users/neranjsubramanian/Documents/video_sara')
MIN_SIMILARITY_SCORE = float(os.getenv('MIN_SIMILARITY_SCORE', '0.2'))
DATA_DIR = Path('data')
INDEX_DIR = DATA_DIR / 'indexes'

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)

class DualVectorSearchService:
    """
    A service for managing dual vector search with FAISS indexes
    and SQLite metadata storage with multi-user support.
    """
    
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.db_path = DB_PATH
        self.index_dir = INDEX_DIR
        
        # Initialize components
        self._init_database()
        self._load_model()
        
        logger.info(f"Initialized DualVectorSearchService with model: {model_name}")
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            # Ensure the database directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Create database connection with proper settings
            conn = sqlite3.connect(self.db_path)
            conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    index_mode TEXT DEFAULT 'private',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # File metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    filename TEXT,
                    summary_text TEXT,
                    frame_details TEXT,
                    duration INTEGER,
                    format TEXT,
                    resolution TEXT,
                    owner TEXT,
                    topic TEXT,
                    tags TEXT,
                    file_path_base TEXT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Indexing status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indexing_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT,
                    user_id TEXT,
                    summary_indexed BOOLEAN DEFAULT FALSE,
                    frame_details_indexed BOOLEAN DEFAULT FALSE,
                    summary_vector_id INTEGER,
                    frame_details_vector_id INTEGER,
                    indexed_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    FOREIGN KEY (file_id) REFERENCES file_metadata (file_id) ON DELETE CASCADE
                )
            ''')
            
            # User index mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_index_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    index_type TEXT,
                    index_file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Create default user if it doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, index_mode)
                VALUES ('1', 'default_user', ?)
            ''', (DEFAULT_INDEX_MODE,))
            
            # Migration: Add file_path_base column if it doesn't exist
            try:
                cursor.execute('ALTER TABLE file_metadata ADD COLUMN file_path_base TEXT')
                logger.info("Added file_path_base column to existing database")
            except sqlite3.OperationalError:
                # Column already exists, no action needed
                pass
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_index_path(self, user_id: str, index_type: str) -> Path:
        """Get the path for a FAISS index file."""
        user_mode = self._get_user_index_mode(user_id)
        if user_mode == 'shared':
            return self.index_dir / f'shared_{index_type}_faiss.bin'
        else:
            return self.index_dir / f'{user_id}_{index_type}_faiss.bin'
    
    def _get_user_index_mode(self, user_id: str) -> str:
        """Get the index mode for a user."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT index_mode FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result['index_mode'] if result else DEFAULT_INDEX_MODE
    
    def _load_or_create_faiss_index(self, user_id: str, index_type: str) -> Tuple[faiss.IndexFlatIP, int]:
        """Load or create a FAISS index for a user and index type."""
        index_path = self._get_index_path(user_id, index_type)
        
        try:
            if index_path.exists():
                index = faiss.read_index(str(index_path))
                current_size = index.ntotal
                logger.info(f"Loaded existing {index_type} index for user {user_id}: {current_size} vectors")
            else:
                index = faiss.IndexFlatIP(self.embedding_dim)
                current_size = 0
                logger.info(f"Created new {index_type} index for user {user_id}")
            
            return index, current_size
        except Exception as e:
            logger.error(f"Failed to load/create index {index_path}: {e}")
            raise
    
    def _save_faiss_index(self, index: faiss.IndexFlatIP, user_id: str, index_type: str):
        """Save a FAISS index to disk."""
        index_path = self._get_index_path(user_id, index_type)
        try:
            faiss.write_index(index, str(index_path))
            logger.info(f"Saved {index_type} index for user {user_id} to {index_path}")
        except Exception as e:
            logger.error(f"Failed to save index {index_path}: {e}")
            raise
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def create_user(self, username: str, index_mode: str = DEFAULT_INDEX_MODE, user_id: str = None) -> Dict[str, Any]:
        """Create a new user."""
        if index_mode not in ['private', 'shared']:
            raise ValueError("index_mode must be 'private' or 'shared'")
        
        # Use provided user_id or generate new one
        if user_id is None:
            user_id = str(uuid.uuid4())
        
        # Validate that user_id doesn't already exist
        if self.get_user(user_id):
            raise ValueError(f"User ID {user_id} already exists")
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, index_mode)
                VALUES (?, ?, ?)
            ''', (user_id, username, index_mode))
            conn.commit()
            conn.close()
            
            logger.info(f"Created user: {username} with ID: {user_id}")
            return {
                'user_id': user_id,
                'username': username,
                'index_mode': index_mode,
                'created_at': datetime.now().isoformat()
            }
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user settings."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            raise ValueError(f"User {user_id} not found")
        
        # Update user
        update_fields = []
        update_values = []
        
        if 'username' in data:
            update_fields.append('username = ?')
            update_values.append(data['username'])
        
        if 'index_mode' in data:
            if data['index_mode'] not in ['private', 'shared']:
                raise ValueError("index_mode must be 'private' or 'shared'")
            update_fields.append('index_mode = ?')
            update_values.append(data['index_mode'])
        
        if update_fields:
            update_values.append(user_id)
            cursor.execute(f'''
                UPDATE users SET {', '.join(update_fields)}
                WHERE user_id = ?
            ''', update_values)
            conn.commit()
        
        # Return updated user
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return dict(result)
    
    def add_file(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a single file to the search index."""
        required_fields = ['file_id', 'user_id', 'filename', 'summary_text', 'frame_details']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        file_id = data['file_id']
        user_id = data['user_id']
        
        # Verify user exists
        if not self.get_user(user_id):
            raise ValueError(f"User {user_id} not found")
        
        # Extract analysis metadata
        metadata = data.get('analysis_metadata', {})
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Insert file metadata
            cursor.execute('''
                INSERT OR REPLACE INTO file_metadata 
                (file_id, user_id, filename, summary_text, frame_details, 
                 duration, format, resolution, owner, topic, tags, file_path_base, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id, user_id, data['filename'], data['summary_text'], 
                data['frame_details'], metadata.get('duration'), 
                metadata.get('format'), metadata.get('resolution'),
                metadata.get('owner'), metadata.get('topic'),
                json.dumps(metadata.get('tags', [])), 
                metadata.get('file_path_base'), datetime.now()
            ))
            
            # Process embeddings
            summary_vector_id = None
            frame_vector_id = None
            
            # Load or create indexes
            summary_index, summary_size = self._load_or_create_faiss_index(user_id, 'summary')
            frame_index, frame_size = self._load_or_create_faiss_index(user_id, 'frame')
            
            # Generate and add summary embedding
            if data['summary_text'].strip():
                summary_embedding = self._generate_embeddings([data['summary_text']])
                summary_index.add(summary_embedding)
                summary_vector_id = summary_size
                self._save_faiss_index(summary_index, user_id, 'summary')
            
            # Generate and add frame embedding
            if data['frame_details'].strip():
                frame_embedding = self._generate_embeddings([data['frame_details']])
                frame_index.add(frame_embedding)
                frame_vector_id = frame_size
                self._save_faiss_index(frame_index, user_id, 'frame')
            
            # Update indexing status
            cursor.execute('''
                INSERT OR REPLACE INTO indexing_status 
                (file_id, user_id, summary_indexed, frame_details_indexed,
                 summary_vector_id, frame_details_vector_id, indexed_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id, user_id, 
                summary_vector_id is not None, 
                frame_vector_id is not None,
                summary_vector_id, frame_vector_id,
                datetime.now(), 'completed'
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully added file {file_id} for user {user_id}")
            return {
                'file_id': file_id,
                'user_id': user_id,
                'status': 'completed',
                'summary_indexed': summary_vector_id is not None,
                'frame_indexed': frame_vector_id is not None,
                'indexed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to add file {file_id}: {e}")
            # Update status to failed
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO indexing_status 
                    (file_id, user_id, status, error_message)
                    VALUES (?, ?, ?, ?)
                ''', (file_id, user_id, 'failed', str(e)))
                conn.commit()
                conn.close()
            except:
                pass
            raise
    
    def add_files_batch(self, user_id: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add multiple files in batch."""
        if not self.get_user(user_id):
            raise ValueError(f"User {user_id} not found")
        
        results = []
        successful = 0
        failed = 0
        
        for file_data in files:
            file_data['user_id'] = user_id
            try:
                result = self.add_file(file_data)
                results.append(result)
                successful += 1
            except Exception as e:
                results.append({
                    'file_id': file_data.get('file_id', 'unknown'),
                    'status': 'failed',
                    'error': str(e)
                })
                failed += 1
        
        return {
            'total_files': len(files),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def get_files(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get files for a user."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fm.*, is_status.status as index_status, is_status.indexed_at
            FROM file_metadata fm
            LEFT JOIN indexing_status is_status ON fm.file_id = is_status.file_id
            WHERE fm.user_id = ?
            ORDER BY fm.created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        results = []
        for row in cursor.fetchall():
            file_data = dict(row)
            # Add file_path attribute
            filename = file_data.get('filename', '')
            if filename:
                # Use file_path_base from metadata if available, otherwise use environment variable
                base_path = file_data.get('file_path_base') or FILE_PATH_BASE
                file_data['file_path'] = os.path.join(base_path, filename)
            else:
                file_data['file_path'] = None
            results.append(file_data)
        
        conn.close()
        return results
    
    def get_file(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific file."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fm.*, is_status.status as index_status, is_status.indexed_at
            FROM file_metadata fm
            LEFT JOIN indexing_status is_status ON fm.file_id = is_status.file_id
            WHERE fm.file_id = ? AND fm.user_id = ?
        ''', (file_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            file_data = dict(result)
            # Add file_path attribute
            filename = file_data.get('filename', '')
            if filename:
                # Use file_path_base from metadata if available, otherwise use environment variable
                base_path = file_data.get('file_path_base') or FILE_PATH_BASE
                file_data['file_path'] = os.path.join(base_path, filename)
            else:
                file_data['file_path'] = None
            return file_data
        
        return None
    
    def update_file(self, file_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update file metadata."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Check if file exists and belongs to user
        cursor.execute('SELECT * FROM file_metadata WHERE file_id = ? AND user_id = ?', (file_id, user_id))
        if not cursor.fetchone():
            raise ValueError(f"File {file_id} not found for user {user_id}")
        
        # Update file metadata
        update_fields = []
        update_values = []
        
        for field in ['filename', 'summary_text', 'frame_details', 'duration', 'format', 'resolution', 'owner', 'topic', 'file_path_base']:
            if field in data:
                update_fields.append(f'{field} = ?')
                update_values.append(data[field])
        
        if 'tags' in data:
            update_fields.append('tags = ?')
            update_values.append(json.dumps(data['tags']))
        
        if update_fields:
            update_fields.append('updated_at = ?')
            update_values.append(datetime.now())
            update_values.append(file_id)
            update_values.append(user_id)
            
            cursor.execute(f'''
                UPDATE file_metadata SET {', '.join(update_fields)}
                WHERE file_id = ? AND user_id = ?
            ''', update_values)
            conn.commit()
        
        # Return updated file
        result = self.get_file(file_id, user_id)
        conn.close()
        
        return result
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Check if file exists and belongs to user
        cursor.execute('SELECT * FROM file_metadata WHERE file_id = ? AND user_id = ?', (file_id, user_id))
        if not cursor.fetchone():
            raise ValueError(f"File {file_id} not found for user {user_id}")
        
        # Delete file metadata (indexing_status will be deleted via CASCADE)
        cursor.execute('DELETE FROM file_metadata WHERE file_id = ? AND user_id = ?', (file_id, user_id))
        conn.commit()
        conn.close()
        
        # Note: We don't remove vectors from FAISS indexes as they don't support deletion
        # This is a known limitation - in production, you'd need to rebuild indexes periodically
        
        logger.info(f"Deleted file {file_id} for user {user_id}")
        return True
    
    def _get_vector_column_name(self, index_type: str) -> str:
        """Map index type to the correct database column name."""
        column_mapping = {
            'summary': 'summary_vector_id',
            'frame': 'frame_details_vector_id'
        }
        return column_mapping.get(index_type, f'{index_type}_vector_id')
    
    def _search_vectors(self, query: str, user_id: str, index_type: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search vectors in a specific index."""
        try:
            # Load index
            index, _ = self._load_or_create_faiss_index(user_id, index_type)
            
            if index.ntotal == 0:
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])
            
            # Search
            scores, indices = index.search(query_embedding, min(top_k, index.ntotal))
            
            # Get file details
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Get the correct column name for this index type
            vector_column = self._get_vector_column_name(index_type)
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    continue
                
                # Filter by minimum similarity score
                if float(score) < MIN_SIMILARITY_SCORE:
                    continue
                
                # Find file by vector index
                cursor.execute(f'''
                    SELECT fm.*, is_status.{vector_column}
                    FROM file_metadata fm
                    JOIN indexing_status is_status ON fm.file_id = is_status.file_id
                    WHERE fm.user_id = ? AND is_status.{vector_column} = ?
                ''', (user_id, int(idx)))
                
                result = cursor.fetchone()
                if result:
                    file_data = dict(result)
                    file_data['similarity_score'] = float(score)
                    file_data['search_type'] = index_type
                    
                    # Add file_path attribute
                    filename = file_data.get('filename', '')
                    if filename:
                        # Use file_path_base from metadata if available, otherwise use environment variable
                        base_path = file_data.get('file_path_base') or FILE_PATH_BASE
                        file_data['file_path'] = os.path.join(base_path, filename)
                    else:
                        file_data['file_path'] = None
                    
                    results.append(file_data)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Search failed for {index_type}: {e}")
            return []
    
    def search_summaries(self, query: str, user_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search summary embeddings."""
        return self._search_vectors(query, user_id, 'summary', top_k)
    
    def search_frames(self, query: str, user_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search frame detail embeddings."""
        return self._search_vectors(query, user_id, 'frame', top_k)
    
    def search_combined(self, query: str, user_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search both summary and frame embeddings."""
        summary_results = self.search_summaries(query, user_id, top_k)
        frame_results = self.search_frames(query, user_id, top_k)
        
        # Combine and sort by similarity score
        combined_results = summary_results + frame_results
        combined_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return combined_results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute('SELECT COUNT(*) as user_count FROM users')
        user_count = cursor.fetchone()['user_count']
        
        # Get file count
        cursor.execute('SELECT COUNT(*) as file_count FROM file_metadata')
        file_count = cursor.fetchone()['file_count']
        
        # Get indexing status
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM indexing_status 
            GROUP BY status
        ''')
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'users': user_count,
            'files': file_count,
            'indexing_status': status_counts,
            'model': self.model_name,
            'embedding_dimension': self.embedding_dim
        }

# Initialize the service
search_service = DualVectorSearchService()

# Flask app
app = Flask(__name__)
CORS(app)

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

# User Management Endpoints
@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username')
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        index_mode = data.get('index_mode', DEFAULT_INDEX_MODE)
        user_id = data.get('user_id')  # Extract user_id from request
        
        result = search_service.create_user(username, index_mode, user_id)
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details."""
    try:
        user = search_service.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        result = search_service.update_user(user_id, data)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# File Management Endpoints
@app.route('/api/files', methods=['POST'])
def add_file():
    """Add a single file."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Explicitly validate user_id is provided
        if not data.get('user_id'):
            return jsonify({'error': 'user_id is required'}), 400
        
        result = search_service.add_file(data)
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/files/batch', methods=['POST'])
def add_files_batch():
    """Add multiple files in batch."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        files = data.get('files', [])
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        if not files:
            return jsonify({'error': 'files array is required'}), 400
        
        result = search_service.add_files_batch(user_id, files)
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding files batch: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    """Get files for a user."""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        files = search_service.get_files(user_id, limit, offset)
        return jsonify({'files': files}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/files/<file_id>', methods=['GET'])
def get_file(file_id):
    """Get a specific file."""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        file_data = search_service.get_file(file_id, user_id)
        if not file_data:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify(file_data), 200
        
    except Exception as e:
        logger.error(f"Error getting file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/files/<file_id>', methods=['PUT'])
def update_file(file_id):
    """Update file metadata."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        result = search_service.update_file(file_id, user_id, data)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file."""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        search_service.delete_file(file_id, user_id)
        return jsonify({'message': 'File deleted successfully'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Search Endpoints
@app.route('/api/search/summary', methods=['GET'])
def search_summary():
    """Search summary embeddings."""
    try:
        query = request.args.get('q')
        user_id = request.args.get('user_id')
        top_k = int(request.args.get('top_k', 10))
        
        if not query:
            return jsonify({'error': 'Query parameter q is required'}), 400
        
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        results = search_service.search_summaries(query, user_id, top_k)
        return jsonify({'results': results}), 200
        
    except Exception as e:
        logger.error(f"Error searching summaries: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search/frames', methods=['GET'])
def search_frames():
    """Search frame detail embeddings."""
    try:
        query = request.args.get('q')
        user_id = request.args.get('user_id')
        top_k = int(request.args.get('top_k', 10))
        
        if not query:
            return jsonify({'error': 'Query parameter q is required'}), 400
        
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        results = search_service.search_frames(query, user_id, top_k)
        return jsonify({'results': results}), 200
        
    except Exception as e:
        logger.error(f"Error searching frames: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search/combined', methods=['GET'])
def search_combined():
    """Search both summary and frame embeddings."""
    try:
        query = request.args.get('q')
        user_id = request.args.get('user_id')
        top_k = int(request.args.get('top_k', 10))
        
        if not query:
            return jsonify({'error': 'Query parameter q is required'}), 400
        
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        results = search_service.search_combined(query, user_id, top_k)
        return jsonify({'results': results}), 200
        
    except Exception as e:
        logger.error(f"Error searching combined: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Statistics Endpoint
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    try:
        stats = search_service.get_stats()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'media_search'}), 200

# Media Search web interface
@app.route('/', methods=['GET'])
def media_search():
    """Media search web interface."""
    return render_template('media_search.html')

# File serving endpoint for local files
@app.route('/api/files/<file_id>/serve', methods=['GET'])
def serve_file(file_id):
    """Serve a media file for preview/download."""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id parameter is required'}), 400
        
        # Get file metadata
        file_data = search_service.get_file(file_id, user_id)
        if not file_data:
            return jsonify({'error': 'File not found'}), 404
        
        file_path = file_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found on disk'}), 404
        
        # Security check: ensure file is within allowed directory
        allowed_base = file_data.get('file_path_base') or FILE_PATH_BASE
        if not file_path.startswith(allowed_base):
            return jsonify({'error': 'Access denied'}), 403
        
        # Return the file
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        return send_from_directory(
            directory, 
            filename, 
            as_attachment=False,
            conditional=True  # Enable HTTP caching
        )
        
    except Exception as e:
        logger.error(f"Error serving file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Database viewer web interface
@app.route('/db', methods=['GET'])
def db_viewer():
    """Database viewer web interface."""
    return render_template('db_viewer.html')

# Simple database viewer endpoint
@app.route('/db/tables', methods=['GET'])
def list_tables():
    """List all database tables."""
    try:
        conn = search_service._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'tables': tables}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/table/<table_name>', methods=['GET'])
def view_table(table_name):
    """View table data."""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        conn = search_service._get_db_connection()
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'table': table_name,
            'columns': columns,
            'rows': [dict(zip(columns, row)) for row in rows],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/query', methods=['POST'])
def execute_query():
    """Execute custom SQL query (SELECT only for safety)."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Only allow SELECT queries for safety
        if not query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT queries are allowed'}), 400
        
        conn = search_service._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'columns': columns,
            'rows': [dict(zip(columns, row)) for row in rows],
            'row_count': len(rows)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False) 