import json
import os

API_KEY_FILE = "api_key.json"


def load_config():
    if not os.path.exists(API_KEY_FILE):
        return {"apikeys": {}}

    with open(API_KEY_FILE, "r", encoding="utf8") as f:
        return json.load(f)


def save_config(data):
    with open(API_KEY_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)


def set_apikey(target_id: str, key: str):
    data = load_config()
    data["apikeys"][target_id] = key
    save_config(data)


def get_apikey(target_id: str):
    data = load_config()
    return data["apikeys"].get(target_id)
