import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    print("❌ GROQ_API_KEY not found. Check your .env file.")
    exit(1)

print("✅ GROQ_API_KEY loaded successfully")
print("💬 Groq Chat Test (type 'exit' to quit)\n")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("👋 Exiting chat")
        break

    payload = {
        "model": "llama-3.1-8b-instant",  # fast + stable
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            print("Groq:", reply)
        else:
            print("❌ API Error:", response.status_code)
            print(response.text)

    except Exception as e:
        print("❌ Request failed:", e)
