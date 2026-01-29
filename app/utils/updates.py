import json
import os
import time

UPDATES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'updates.json')

def load_updates():
    """Loads updates from the JSON file."""
    if not os.path.exists(UPDATES_FILE):
        return []
    
    try:
        with open(UPDATES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading updates: {e}")
        return []

def save_update(content, tag, color, version="v2.X"):
    """Adds a new update to the JSON file."""
    updates = load_updates()
    
    # Generate new ID
    new_id = 1
    if updates:
        new_id = max(u.get('id', 0) for u in updates) + 1
        
    date_str = time.strftime("%d.%m.%Y")
    
    new_entry = {
        "id": new_id,
        "date": date_str,
        "tag": tag,
        "color": color,
        "content": content
    }
    
    # Insert at beginning
    updates.insert(0, new_entry)
    
    try:
        os.makedirs(os.path.dirname(UPDATES_FILE), exist_ok=True)
        with open(UPDATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)
        return new_entry
    except Exception as e:
        print(f"Error saving update: {e}")
        return None
