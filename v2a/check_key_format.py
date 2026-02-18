
import os
from dotenv import load_dotenv

def check_key():
    if not os.path.exists('.env'):
        print("No .env file")
        return

    load_dotenv()
    key = os.getenv('GROQ_API_KEY')
    
    if not key:
        print("No GROQ_API_KEY in .env")
        return
        
    print(f"Key length: {len(key)}")
    print(f"Starts with 'gsk_': {key.startswith('gsk_')}")
    print("Ends with newline: {}".format(key.endswith('\\n') if key else False))
    print(f"Contains space: {' ' in key}")
    print(f"First 4 chars: {key[:4]}")
    print(f"Last 4 chars: {key[-4:]}")
    
    # Check raw file content for quotes
    with open('.env', 'r') as f:
        content = f.read()
        print("Raw .env content (masked):")
        for line in content.splitlines():
            if 'GROQ_API_KEY' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    val = parts[1].strip()
                    if val.startswith('"') and val.endswith('"'):
                        print("Key is double-quoted in file")
                    elif val.startswith("'") and val.endswith("'"):
                        print("Key is single-quoted in file")
                    else:
                        print("Key is NOT quoted in file")

if __name__ == "__main__":
    check_key()
