import urllib.request
import json
import time
from app.config import DISCORD_WEBHOOK_URL

def send_discord_notification(app_data):
    if not DISCORD_WEBHOOK_URL:
        return
    
    # Labels for Discord
    labels = {
        'id': 'ID',
        'applicationType': 'Type',
        'roblox_user': 'Roblox Name',
        'discord_name': 'Discord Name',
        'age': 'Age',
        'about_me': 'About Me',
        'daily_time': 'Daily Time',
        'motivation': 'Motivation',
        'timestamp': 'Timestamp'
    }
    
    fields = []
    for k, v in app_data.items():
        if k == 'timestamp':
             v = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(v))
        
        label = labels.get(k, k)
        # Discord limit: field name 256, value 1024
        fields.append({
            "name": label,
            "value": str(v)[:1000] if v else "N/A",
            "inline": True if k not in ['about_me', 'motivation'] else False
        })

    payload = {
        "embeds": [{
            "title": "New application received!",
            "color": 0x00ff00,
            "fields": fields,
            "footer": {"text": "DRP Application System"}
        }]
    }
    
    try:
        req = urllib.request.Request(DISCORD_WEBHOOK_URL)
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        urllib.request.urlopen(req, json.dumps(payload).encode('utf-8'))
    except Exception as e:
        print(f"Error sending Discord notification: {e}")
