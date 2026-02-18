
import os
import sys
import requests
import socket
from dotenv import load_dotenv

def check_internet():
    print("\n1. [NET] Checking Internet Connection...")
    try:
        # Try to connect to Google's DNS
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print("   [OK] Internet is accessible")
        return True
    except OSError:
        print("   [FAIL] No Internet connection")
        return False

def check_files():
    print("\n2. [FILE] Checking Project Files...")
    
    files = {
        '.env': 'Configuration File',
        'app.py': 'Backend Server',
        'index.html': 'Frontend Interface',
        'video': 'Video Directory'
    }
    
    all_exist = True
    for filename, description in files.items():
        if os.path.exists(filename):
            print(f"   [OK] Found {description} ({filename})")
        else:
            print(f"   [FAIL] MISSING {description} ({filename})")
            all_exist = False
            
    if os.path.exists('video'):
        video_count = len([f for f in os.listdir('video') if f.endswith(('.mp4', '.MOV', '.mov'))])
        print(f"   [INFO] Video directory contains {video_count} video files")
    
    return all_exist

def check_api_key():
    print("\n3. [KEY] Checking API Key...")
    
    if not os.path.exists('.env'):
        print("   [FAIL] .env file missing - Cannot check key")
        return False
        
    load_dotenv(override=True)
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        print("   [FAIL] GROQ_API_KEY not found in .env")
        return False
        
    # Masked print
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
    print(f"   [INFO] Loaded Key: {masked_key}")
    
    if not api_key.startswith('gsk_'):
        print("   [FAIL] Key Format Error: Does not start with 'gsk_'")
    else:
        print("   [OK] Key Format looks correct (starts with 'gsk_')")

    print("\n4. [API] Testing Groq API Endpoint...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": "Ping"}],
        "max_tokens": 5
    }
    
    try:
        print("   [WAIT] Sending test request to Groq...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print("   [OK] API Call SUCCESS! The key is valid and working.")
            return True
        elif response.status_code == 401:
            print("   [FAIL] API Call REJECTED (401 Unauthorized). Check your API Key.")
            print(f"      Response: {response.text}")
            return False
        else:
            print(f"   [FAIL] API Call Failed with status {response.status_code}")
            print(f"      Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   [FAIL] API Call Error: {str(e)}")
        return False

def main():
    print("=== Voice-to-ISL Diagnostic Tool ===")
    
    internet_ok = check_internet()
    files_ok = check_files()
    
    if internet_ok:
        api_ok = check_api_key()
    else:
        print("\n[FAIL] Skipping API check due to no internet")
        api_ok = False
        
    print("\n=== Diagnostic Summary ===")
    if internet_ok and files_ok and api_ok:
        print("[PASS] ALL CHECKS PASSED. The backend is configured correctly.")
        print("      If it still fails, the issue is likely in the Browser/Frontend.")
    else:
        print("[FAIL] ISSUES FOUND. Please fix the errors above.")

if __name__ == "__main__":
    main()
