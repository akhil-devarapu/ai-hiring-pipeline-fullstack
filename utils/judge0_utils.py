import requests
import time
import os

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com"
JUDGE0_HEADERS = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY"),  # Get from environment variable
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "Content-Type": "application/json"
}

LANGUAGE_MAP = {
    'python': 71,
    'cpp': 54,
    'c': 50,
    'java': 62,
    'javascript': 63,
    'ruby': 72,
    'go': 60,
    'php': 68,
    'csharp': 51,
    'swift': 83,
    'rust': 73
}

def submit_code(code, language, stdin=""):
    # Check if RapidAPI key is configured
    if JUDGE0_HEADERS["X-RapidAPI-Key"] == "YOUR_RAPIDAPI_KEY":
        return "demo_token"  # Return demo token for testing
    
    lang_id = LANGUAGE_MAP.get(language.lower(), 71)  # Default to Python
    data = {
        "source_code": code,
        "language_id": lang_id,
        "stdin": stdin
    }
    
    try:
        resp = requests.post(f"{JUDGE0_URL}/submissions?base64_encoded=false&wait=false", 
                           json=data, headers=JUDGE0_HEADERS, timeout=10)
        if resp.status_code == 201:
            return resp.json()["token"]
        else:
            print(f"Judge0 API error: {resp.status_code} - {resp.text}")
            return "demo_token"
    except Exception as e:
        print(f"Judge0 API connection error: {e}")
        return "demo_token"

def get_result(token):
    # If it's a demo token, return a mock result
    if token == "demo_token":
        return "5"  # Mock output for demo
    
    # Check if RapidAPI key is configured
    if JUDGE0_HEADERS["X-RapidAPI-Key"] == "YOUR_RAPIDAPI_KEY":
        return "5"  # Return mock result
    
    for _ in range(20):
        try:
            resp = requests.get(f"{JUDGE0_URL}/submissions/{token}?base64_encoded=false", 
                              headers=JUDGE0_HEADERS, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result["status"]["id"] in [1, 2]:  # In Queue or Processing
                    time.sleep(1)
                    continue
                return result.get("stdout", "")
            else:
                print(f"Judge0 API error: {resp.status_code} - {resp.text}")
                return "Judge0 API error"
        except Exception as e:
            print(f"Judge0 API connection error: {e}")
            return "Judge0 connection error"
        time.sleep(1)
    return "Judge0 timeout or error" 