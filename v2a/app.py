"""
Voice-to-ISL Animation Translator - Python Flask Server
A web application that translates voice input to Indian Sign Language (ISL) animations.
"""

import os
import logging
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
PORT = int(os.getenv('PORT', 3000))

# HTML template - we'll serve the index.html file directly
@app.route('/')
def index():
    """Serve the main HTML file"""
    try:
        with open('index.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except FileNotFoundError:
        return jsonify({'error': 'index.html not found'}), 404

@app.route('/api/grok-key', methods=['GET'])
def get_grok_key():
    """API endpoint to get the Groq API key"""
    logger.info('Checking for GROQ_API_KEY in environment...')
    
    # Log available environment variables that contain 'GROQ'
    groq_vars = [key for key in os.environ.keys() if 'GROQ' in key]
    logger.info(f'Available environment variables: {groq_vars}')
    
    if GROQ_API_KEY:
        logger.info('✅ GROQ_API_KEY found and loaded successfully')
        return jsonify({'apiKey': GROQ_API_KEY})
    else:
        logger.error('❌ GROQ_API_KEY not found in environment variables')
        logger.info('Please check your .env file contains: GROQ_API_KEY=your_api_key_here')
        return jsonify({
            'error': 'GROQ_API_KEY not found in environment variables',
            'message': 'Please check your .env file contains: GROQ_API_KEY=your_api_key_here'
        }), 404

@app.route('/video/<filename>')
def serve_video(filename):
    """Serve video files from the video directory"""
    try:
        return send_from_directory('video', filename)
    except FileNotFoundError:
        return jsonify({'error': f'Video file {filename} not found'}), 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except FileNotFoundError:
        return jsonify({'error': f'Static file {filename} not found'}), 404

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f'Internal error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function to run the Flask application"""
    logger.info(f'🚀 Starting Flask server on http://localhost:{PORT}')
    logger.info('📁 Loading environment variables from .env file...')
    
    # Check if GROQ_API_KEY is loaded
    if GROQ_API_KEY:
        if GROQ_API_KEY.startswith('gsk_'):
            logger.info('✅ GROQ_API_KEY loaded successfully from .env file')
            logger.info('🤖 AI Analysis is required for translation')
        else:
            logger.warning('⚠️ GROQ_API_KEY found but format seems invalid (should start with "gsk_")')
            logger.info('🤖 AI Analysis might fail if the key is incorrect')
    else:
        logger.warning('❌ GROQ_API_KEY not found in .env file')
        logger.info('📝 Please ensure your .env file contains: GROQ_API_KEY=your_api_key_here')
        logger.info('🔧 The application requires GROQ_API_KEY to function')
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=PORT, debug=True)

if __name__ == '__main__':
    main()
