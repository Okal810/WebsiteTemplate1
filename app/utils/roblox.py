import urllib.request
import json

def resolve_roblox_user_logic(username):
    try:
        url = "https://users.roblox.com/v1/usernames/users"
        payload = {
            "usernames": [username],
            "excludeBannedUsers": True
        }
        
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        response = urllib.request.urlopen(req, json.dumps(payload).encode('utf-8'))
        resp_data = json.loads(response.read())
        
        if resp_data.get('data') and len(resp_data['data']) > 0:
            return resp_data['data'][0], None
        
        return None, "User not found"
    except Exception as e:
        return None, str(e)
