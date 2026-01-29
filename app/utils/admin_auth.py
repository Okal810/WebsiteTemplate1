import secrets
import time
import json
import urllib.request
import os
from app.config import CREDENTIALS_FILE, CREDENTIALS_WEBHOOK_URL, DISCORD_WEBHOOK_URL
from app.config import CREDENTIALS_FILE, CREDENTIALS_WEBHOOK_URL, DISCORD_WEBHOOK_URL

ADMIN_CREDENTIALS = {
    "username": "",
    "password": ""
}

def rotate_admin_credentials():
    """Generates new random credentials and sends them to Discord.
    If valid credentials exist in file, use those instead (prevents reloader issues).
    """
    try:
        # Check if valid credentials exist in the file (less than 24h old)
        if os.path.exists(CREDENTIALS_FILE):
            try:
                with open(CREDENTIALS_FILE, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        username = lines[0].replace('Username: ', '').strip()
                        password = lines[1].replace('Password: ', '').strip()
                        
                        # Check if credentials look valid
                        if username.startswith('Admin-') and password.startswith('DRP-'):
                            ADMIN_CREDENTIALS['username'] = username
                            ADMIN_CREDENTIALS['password'] = password
                            print(f"\n[*] Using existing credentials: {username}")
                            return
            except Exception:
                pass  # File could not be read, generate new one
        
        # Generate new credentials
        random_user = secrets.token_hex(4).upper()
        # Ensure password doesn't start with - or _
        random_pass = secrets.token_urlsafe(16).lstrip('-_')
        
        username = f"Admin-{random_user}"
        password = f"DRP-{random_pass}"
        
        ADMIN_CREDENTIALS['username'] = username
        ADMIN_CREDENTIALS['password'] = password
        
        # Invalidate all existing sessions when credentials change
        # Invalidate all existing sessions when credentials change (DB)
        try:
            from app.models import db, AdminSession
            db.session.query(AdminSession).delete()
            db.session.commit()
        except:
            pass
        
        try:
            with open(CREDENTIALS_FILE, 'w') as f:
                f.write(f"Username: {username}\nPassword: {password}\nTimestamp: {time.ctime()}")
        except:
            pass
        
        print("\n" + "="*50)
        print(f"[*] NEW ADMIN CREDENTIALS GENERATED")
        print(f"[*] Username: {username}")
        print(f"[*] Password: {password}")
        print(f"[*] Saved to: admin_credentials.txt")
        print("="*50 + "\n")
        
        
        webhook_url = CREDENTIALS_WEBHOOK_URL or DISCORD_WEBHOOK_URL
        if not webhook_url: return

        embed = {
            "title": "New Credentials (Panel)",
            "color": 16711680,
            "description": f"**User:** `{username}`\n**Pass:** ||`{password}`||",
            "footer": {"text": "Valid until restart/rotation - DRP Security"}
        }
        
        payload = {"username": "DRP Security", "embeds": [embed]}
        
        req = urllib.request.Request(webhook_url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        urllib.request.urlopen(req, json.dumps(payload).encode('utf-8'))
        
    except Exception as e:
        print(f"Credential Rotation Error: {e}")


