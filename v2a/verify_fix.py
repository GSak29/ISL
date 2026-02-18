
import os
import sys
from dotenv import load_dotenv

# Mocking the logger
class Logger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

logger = Logger()

def check_env_and_logic():
    print("--- Simulating Backend Logic ---")
    
    # Reload env to pick up any changes
    if os.path.exists('.env'):
        load_dotenv(override=True)
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Logic copied from app.py
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

if __name__ == "__main__":
    check_env_and_logic()
