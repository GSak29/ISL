# Voice-to-ISL Animation Translator

A Python Flask web application that translates voice input to Indian Sign Language (ISL) animations using the Grok API for intelligent sentence analysis.

## Features

- 🎤 **Voice Recognition**: Real-time speech-to-text conversion
- 🤖 **AI Analysis**: Intelligent sentence breakdown using Grok API
- 🎬 **Video Sequences**: Plays ISL animations in meaningful sequences
- 📊 **Progress Tracking**: Visual feedback for translation progress
- 🎯 **AI-Powered Chunks**: Intelligent sentence breakdown into meaningful chunks
- 🐍 **Python Backend**: Built with Flask for easy deployment and maintenance

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Quick Start

### Option 1: Auto Setup (Recommended)

```bash
python run.py
```

This script will:
- Check Python version
- Install dependencies automatically
- Create .env file if it doesn't exist
- Start the server

### Option 2: Manual Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Environment File

Create a `.env` file in the root directory:

```bash
# Copy the example file
cp env.example .env
```

Then edit the `.env` file and add your Grok API key:

```
GROQ_API_KEY=your_actual_groq_api_key_here
PORT=3000
```

### 3. Start the Server

```bash
python app.py
```

The application will be available at `http://localhost:3000`

### 4. Alternative: Direct File Access

If you prefer to run without a server, you can:
1. Open `index.html` directly in a browser
2. Enter your Grok API key when prompted
3. The key will be stored in browser localStorage

## Available Sign Language Animations

The system supports these words with corresponding video files:
- Hello, Namaste, Good, Bad, Please
- Mother, Father, Brother
- Food, Name, Your, Time

## Usage

1. **Voice Input**: Click the microphone button and speak
2. **AI Analysis**: The Groq API analyzes your sentence and creates intelligent chunks
3. **Video Playback**: ISL animations play in sequence based on API analysis
4. **Test Mode**: Use the "🧪 Test Sequence" button to try predefined sentences

**Note**: This application requires a valid Groq API key to function. No fallback to basic word detection is provided.

## API Integration

The application exclusively uses the Groq API for intelligent sentence analysis:
- Breaks down sentences into meaningful chunks
- Maps concepts to available animations
- Creates logical sequences for sign language communication
- **No fallback to basic word detection** - API analysis is required

## File Structure

```
├── index.html          # Main application frontend
├── app.py              # Flask server
├── run.py              # Quick start script
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
├── env.example        # Example environment file
├── video/             # ISL animation videos
│   ├── Hello.mp4
│   ├── Good.mp4
│   └── ...
└── README.md          # This file
```

## Python Dependencies

The application uses these main Python packages:
- **Flask**: Web framework
- **Flask-CORS**: Cross-Origin Resource Sharing support
- **python-dotenv**: Environment variable management
- **requests**: HTTP client (for API calls)

## Troubleshooting

- **Python Version**: Ensure you have Python 3.7 or higher
- **API Key Required**: The application will not function without a valid Groq API key
- **API Key Issues**: Make sure your `.env` file contains the correct Groq API key
- **Video Playback**: Ensure all video files are in the `video/` directory
- **Server Issues**: Check that port 3000 is available or change the PORT in `.env`
- **Dependencies**: Run `pip install -r requirements.txt` if you encounter import errors

## Development

For development with auto-restart:

```bash
# Install Flask development dependencies
pip install flask[dotenv]

# Set environment variable for development
export FLASK_ENV=development
export FLASK_DEBUG=True

# Run the application
python app.py
```

## Deployment

For production deployment, consider using:
- **Gunicorn**: `gunicorn -w 4 -b 0.0.0.0:3000 app:app`
- **Docker**: Create a Dockerfile for containerization
- **Cloud Platforms**: Deploy to Heroku, AWS, or Google Cloud 