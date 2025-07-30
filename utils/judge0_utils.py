import requests
import time

JUDGE0_URL = "https://judge0-ce.p.rapidapi.com"
JUDGE0_HEADERS = {
    "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",  # Replace with your RapidAPI key
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
    lang_id = LANGUAGE_MAP.get(language.lower(), 71)  # Default to Python
    data = {
        "source_code": code,
        "language_id": lang_id,
        "stdin": stdin
    }
    resp = requests.post(f"{JUDGE0_URL}/submissions?base64_encoded=false&wait=false", json=data, headers=JUDGE0_HEADERS)
    if resp.status_code == 201:
        return resp.json()["token"]
    return None

def get_result(token):
    for _ in range(20):
        resp = requests.get(f"{JUDGE0_URL}/submissions/{token}?base64_encoded=false", headers=JUDGE0_HEADERS)
        if resp.status_code == 200:
            result = resp.json()
            if result["status"]["id"] in [1, 2]:  # In Queue or Processing
                time.sleep(1)
                continue
            return result.get("stdout", "")
        time.sleep(1)
    return "Judge0 timeout or error" 