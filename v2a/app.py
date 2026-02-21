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

import requests
import json
import random

# ... (existing imports are fine, but ensure requests is imported)

def get_available_videos():
    """Get list of available video files (without extension)"""
    video_dir = os.path.join(os.path.dirname(__file__), 'video')
    if not os.path.exists(video_dir):
        return []
    
    videos = []
    for f in os.listdir(video_dir):
        if f.lower().endswith(('.mov', '.mp4')):
            videos.append(os.path.splitext(f)[0])
            
    return videos

@app.route('/api/process-text', methods=['POST'])
def process_text():
    """Process text using Groq to map to available ISL videos"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    if not GROQ_API_KEY:
        return jsonify({
            'error': 'GROQ_API_KEY not configured',
            'sequence': []
        }), 500
        
    available_videos = get_available_videos()
    available_videos_str = ", ".join(available_videos)
    
    system_prompt = f"""
    You are a Sign Language Translator assistant. 
    Your task is to map the user's spoken sentence into a sequence of sign language video filenames from the available dataset.
    
    AVAILABLE VIDEO DATASET:
    [{available_videos_str}]
    
    RULES:
    1. Analyze the user's sentence and extract key meanings.
    2. Map identifying words to the CLOSEST match in the dataset (e.g., "mom" -> "MUMMY").
    3. If a word helps convey meaning but isn't in the dataset, mark it as 'unavailable'.
    4. If the exact word exists, use it.
    5. Synonyms are allowed (e.g., "home" -> "HOUSE" if HOUSE exists, or vice versa).
    6. Return a JSON array of objects. Each object must have:
       - "word": The word/concept from the user's sentence.
       - "video": The exact filename from the dataset (without extension) OR null if not found.
       - "available": boolean (true if video found, false otherwise).
    
    EXAMPLE:
    Dataset: [MUMMY, EAT, FOOD]
    Input: "Mom is eating"
    Output: [
        {{"word": "Mom", "video": "MUMMY", "available": true}},
        {{"word": "is", "video": null, "available": false}},
        {{"word": "eating", "video": "EAT", "available": true}}
    ]
    
    Return ONLY valid JSON. No markdown, no explanations.
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"} 
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Groq API Error: {response.text}")
            return jsonify({'error': 'AI processing failed', 'details': response.text}), 500
            
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Parse JSON from content
        try:
            parsed_content = json.loads(content)
            # Handle if the AI wraps it in a root key like "sequence" or returns a raw list
            sequence = parsed_content.get('sequence', parsed_content) if isinstance(parsed_content, dict) else parsed_content
            
            # Additional validation to ensure we have the correct structure
            if not isinstance(sequence, list):
                 # Fallback: try to find a list in the values
                 for val in parsed_content.values():
                     if isinstance(val, list):
                         sequence = val
                         break
            
            # Post-process to ensure video file extensions are handled if needed, 
            # but frontend probably expects just the name or full path. 
            # Let's attach the full web path for the frontend.
            final_sequence = []
            for item in sequence:
                video_name = item.get('video')
                if video_name:
                    # Find specific file extension
                    real_filename = f"{video_name}.MOV" # Default
                    for f in os.listdir(os.path.join(os.path.dirname(__file__), 'video')):
                         if f.startswith(video_name) and f.lower().endswith(('.mov', '.mp4')):
                             real_filename = f
                             break
                    
                    item['video_url'] = f"/video/{real_filename}"
                else:
                    item['video_url'] = None
                final_sequence.append(item)
                
            return jsonify({'sequence': final_sequence})
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response: {content}")
            return jsonify({'error': 'Invalid AI response format'}), 500
            
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
