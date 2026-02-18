"""
Voice-to-ISL Animation Translator - Quick Start Script
This script provides a quick way to start the application.
"""

import subprocess
import sys
import os

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected")

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Creating one from env.example...")
        try:
            with open('env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("📝 Please edit .env file and add your GROQ_API_KEY")
        except FileNotFoundError:
            print("❌ env.example file not found")
            sys.exit(1)
    else:
        print("✅ .env file found")

def start_server():
    """Start the Flask server"""
    print("🚀 Starting Voice-to-ISL Translator...")
    try:
        from app import main
        main()
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")

def main():
    """Main function"""
    print("🎤 Voice-to-ISL Animation Translator")
    print("=" * 40)
    
    check_python_version()
    install_dependencies()
    check_env_file()
    start_server()

if __name__ == "__main__":
    main()
