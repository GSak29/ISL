
import os
import sys
from dotenv import load_dotenv
import requests
import json

def test_environment():
    print("Testing environment setup...")
    
    # 1. Check .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        return
    print("✅ .env file exists")
    
    # 2. Load .env
    load_dotenv()
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env!")
        return
    
    print(f"Key length: {len(api_key)}")
    if api_key.startswith('gsk_'):
        print("✅ Key starts with 'gsk_'")
    else:
        print(f"❌ Key DOES NOT start with 'gsk_', it starts with '{api_key[:4]}'")
    
    # Check for quotes
    if api_key.startswith('"') or api_key.startswith("'"):
        print("⚠️ Key seems to be quoted. dotenv might handle it, but check if it includes quotes in the value.")
    
    # 3. Test API connectivity
    print("\nTesting Groq API connectivity...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "user", "content": "Return JSON: {\"status\": \"ok\"}"}
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"❌ API call failed with exception: {e}")

if __name__ == "__main__":
    test_environment()
