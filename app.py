import os
import sqlite3
import logging
import uuid
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from flask import Flask, request, jsonify, render_template, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
class Config:
    """Application configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 32 * 1024 * 1024))  # 32MB (ImgBB limit)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'}
    
    # ImgBB Configuration
    IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')
    IMGBB_API_URL = 'https://api.imgbb.com/1/upload'
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'images.db')
    
    # Application Configuration
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

app.config.from_object(Config)

# Setup Logging
def setup_logging():
    """Configure structured logging for production"""
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    log_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    return logger

logger = setup_logging()

# Validate Configuration
def validate_config():
    """Validate required environment variables"""
    if not Config.IMGBB_API_KEY:
        error_msg = "Missing required environment variable: IMGBB_API_KEY"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    
    logger.info("Configuration validated successfully")

# Database Functions
def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_db():
    """Initialize database with required tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                s3_url TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                original_filename TEXT,
                file_size INTEGER,
                content_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_uploaded_at 
            ON images(uploaded_at DESC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

# Utility Functions
def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def upload_to_imgbb(file, filename: str, image_id: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Upload file to ImgBB
    Returns: (success: bool, image_url: str, delete_url: str, error_message: str)
    """
    try:
        # Read file content
        file.seek(0)
        file_content = file.read()
        
        # Encode to base64
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Prepare payload
        payload = {
            'key': Config.IMGBB_API_KEY,
            'image': base64_image,
            'name': f"{image_id}_{filename}"
        }
        
        # Make request to ImgBB API
        logger.info(f"Uploading to ImgBB for ID: {image_id}")
        response = requests.post(Config.IMGBB_API_URL, data=payload, timeout=30)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                data = result.get('data', {})
                image_url = data.get('url')
                delete_url = data.get('delete_url')
                
                logger.info(f"File uploaded successfully to ImgBB: {image_url}")
                return True, image_url, delete_url, None
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                logger.error(f"ImgBB API error: {error_msg}")
                return False, None, None, error_msg
        else:
            error_msg = f"ImgBB API returned status code {response.status_code}"
            logger.error(error_msg)
            return False, None, None, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Upload timeout - ImgBB API did not respond in time"
        logger.error(error_msg)
        return False, None, None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error during upload: {str(e)}"
        logger.error(error_msg)
        return False, None, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during upload: {str(e)}"
        logger.error(error_msg)
        return False, None, None, error_msg

def save_image_metadata(image_id: str, image_url: str, delete_url: str,
                        filename: str, file_size: int, content_type: str):
    """Save image metadata to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO images (id, s3_url, s3_key, original_filename, file_size, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (image_id, image_url, delete_url or '', filename, file_size, content_type))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Image metadata saved for ID: {image_id}")
    except sqlite3.Error as e:
        logger.error(f"Database error saving metadata: {str(e)}")
        raise

# Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        conn = get_db_connection()
        conn.close()
        
        # Check ImgBB API key is configured
        if not Config.IMGBB_API_KEY:
            raise Exception("ImgBB API key not configured")
        
        return jsonify({
            'status': 'healthy',
            'storage': 'ImgBB',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': Config.ENVIRONMENT
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/<image_id>', methods=['GET'])
def upload_page(image_id: str):
    """Serve upload page for specific ID"""
    # Validate image_id (alphanumeric and hyphens only)
    if not image_id or not image_id.replace('-', '').replace('_', '').isalnum():
        logger.warning(f"Invalid image_id attempted: {image_id}")
        abort(400, description="Invalid image ID format")
    
    logger.info(f"Upload page requested for ID: {image_id}")
    return render_template('upload.html', image_id=image_id)

@app.route('/upload/<image_id>', methods=['POST'])
def upload_image(image_id: str):
    """Handle image upload"""
    # Validate image_id
    if not image_id or not image_id.replace('-', '').replace('_', '').isalnum():
        logger.warning(f"Invalid image_id in upload: {image_id}")
        return jsonify({'error': 'Invalid image ID format'}), 400
    
    # Check if file is present
    if 'file' not in request.files:
        logger.warning(f"No file in upload request for ID: {image_id}")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        logger.warning(f"Empty filename in upload for ID: {image_id}")
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file extension
    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type attempted: {file.filename}")
        return jsonify({
            'error': f'Invalid file type. Allowed types: {", ".join(Config.ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Secure the filename
        original_filename = secure_filename(file.filename)
        
        # Get file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        # Check file size (ImgBB max: 32MB)
        if file_size > Config.MAX_CONTENT_LENGTH:
            return jsonify({
                'error': f'File too large. Maximum size: {Config.MAX_CONTENT_LENGTH / (1024*1024):.0f}MB'
            }), 413
        
        # Get content type
        content_type = file.content_type or 'application/octet-stream'
        
        # Upload to ImgBB
        success, image_url, delete_url, error = upload_to_imgbb(file, original_filename, image_id)
        
        if not success:
            return jsonify({'error': error or 'Upload failed'}), 500
        
        # Save metadata to database
        save_image_metadata(
            image_id, image_url, delete_url,
            original_filename, file_size, content_type
        )
        
        logger.info(f"Upload completed successfully for ID: {image_id}")
        
        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'image_id': image_id,
            's3_url': image_url,  # Keep field name for compatibility with frontend
            'image_url': image_url,
            'delete_url': delete_url,
            'uploaded_at': datetime.utcnow().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Upload error for ID {image_id}: {str(e)}")
        return jsonify({
            'error': 'Internal server error during upload'
        }), 500

@app.route('/api/url/<image_id>', methods=['GET'])
def get_image_url(image_id: str):
    """Get S3 URL for a given image ID"""
    # Validate image_id
    if not image_id or not image_id.replace('-', '').replace('_', '').isalnum():
        logger.warning(f"Invalid image_id in GET request: {image_id}")
        return jsonify({'error': 'Invalid image ID format'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, s3_url, original_filename, file_size, 
                   content_type, uploaded_at
            FROM images 
            WHERE id = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
        ''', (image_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"Image URL retrieved for ID: {image_id}")
            return jsonify({
                'success': True,
                'image_id': row['id'],
                's3_url': row['s3_url'],
                'original_filename': row['original_filename'],
                'file_size': row['file_size'],
                'content_type': row['content_type'],
                'uploaded_at': row['uploaded_at']
            }), 200
        else:
            logger.info(f"Image not found for ID: {image_id}")
            return jsonify({
                'error': 'Image not found',
                'image_id': image_id
            }), 404
            
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving image: {str(e)}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error retrieving image URL: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/images/<image_id>', methods=['GET'])
def get_all_images_for_id(image_id: str):
    """Get all uploads for a given ID (if multiple uploads)"""
    if not image_id or not image_id.replace('-', '').replace('_', '').isalnum():
        return jsonify({'error': 'Invalid image ID format'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, s3_url, original_filename, file_size, 
                   content_type, uploaded_at
            FROM images 
            WHERE id = ?
            ORDER BY uploaded_at DESC
        ''', (image_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            images = [{
                'image_id': row['id'],
                's3_url': row['s3_url'],
                'original_filename': row['original_filename'],
                'file_size': row['file_size'],
                'content_type': row['content_type'],
                'uploaded_at': row['uploaded_at']
            } for row in rows]
            
            return jsonify({
                'success': True,
                'count': len(images),
                'images': images
            }), 200
        else:
            return jsonify({
                'error': 'No images found',
                'image_id': image_id
            }), 404
            
    except Exception as e:
        logger.error(f"Error retrieving images: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error Handlers
@app.errorhandler(400)
def bad_request(e):
    """Handle 400 errors"""
    return jsonify({'error': str(e.description)}), 400

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(413)
def request_entity_too_large(e):
    """Handle file too large errors"""
    return jsonify({
        'error': f'File too large. Maximum size: {Config.MAX_CONTENT_LENGTH / (1024*1024)}MB'
    }), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

# Application Initialization
def initialize_app():
    """Initialize application components"""
    logger.info("Initializing application...")
    
    # Validate configuration
    validate_config()
    
    # Initialize database
    init_db()
    
    # Verify ImgBB configuration
    if Config.IMGBB_API_KEY:
        logger.info("ImgBB API configured successfully")
    else:
        logger.warning("ImgBB API key not found - uploads will fail")
    
    logger.info("Application initialized successfully")

# Initialize application when module is loaded (for gunicorn)
try:
    initialize_app()
except Exception as e:
    logger.critical(f"Failed to initialize application: {str(e)}")
    raise

# Run Application
if __name__ == '__main__':
    try:
        
        # Run server
        debug_mode = Config.ENVIRONMENT == 'development'
        logger.info(f"Starting Flask server in {Config.ENVIRONMENT} mode...")
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=debug_mode,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}")
        raise

