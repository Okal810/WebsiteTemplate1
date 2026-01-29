import os
import secrets
import time
import json

# Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load secrets from .env file
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    def read_env(path, encoding='utf-8'):
        with open(path, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip().replace('\ufeff', '')
                if not line or line.startswith('#'): continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    try:
        read_env(env_path, 'utf-8')
    except UnicodeDecodeError:
        read_env(env_path, 'latin-1')


# Flask Configuration
SECRET_KEY = secrets.token_hex(32)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

# Security Configuration
IP_HASH_SALT = os.environ.get("IP_HASH_SALT", secrets.token_hex(32))

# Data Directories and Files
DATA_DIR = os.path.join(BASE_DIR, 'data')

# SQLAlchemy Database Configuration
DATABASE_FILE = os.path.join(DATA_DIR, 'database.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_FILE}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Legacy JSON files (kept for backwards compatibility)
DATA_FILE = os.path.join(DATA_DIR, 'applications.json')
WARNS_FILE = os.path.join(DATA_DIR, 'warns.json')
SHIFTS_FILE = os.path.join(DATA_DIR, 'shifts.json')

# X-Stream Configuration
XSTREAM_DIR = os.path.join(BASE_DIR, 'xstream')
XSTREAM_UPLOAD_FOLDER = os.path.join(XSTREAM_DIR, 'uploads')
XSTREAM_DATA_FILE = os.path.join(DATA_DIR, 'videos.json')
LIVE_STREAMS_FILE = os.path.join(DATA_DIR, 'live_streams.json')
LIVE_CHAT_FILE = os.path.join(DATA_DIR, 'live_chat.json')
FORUM_POSTS_FILE = os.path.join(DATA_DIR, 'forum_posts.json')
BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')
IP_WARNINGS_FILE = os.path.join(DATA_DIR, 'ip_warnings.json')
CREDENTIALS_FILE = os.path.join(os.path.dirname(BASE_DIR), 'admin_credentials.txt')
ADMIN_CREDENTIALS_FILE = CREDENTIALS_FILE

# Webhooks
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
CREDENTIALS_WEBHOOK_URL = os.environ.get("CREDENTIALS_WEBHOOK_URL")

# Limits
MAX_RATE_LIMITS = 10000
MAX_CSRF_TOKENS = 5000
MAX_ADMIN_SESSIONS = 100
MAX_FAILED_LOGINS = 1000
MAX_CONTENT_HISTORY = 5
MAX_FORUM_POST_RATE_LIMITS = 5000
MAX_FORUM_COMMENT_RATE_LIMITS = 5000

# Other
START_TIME = time.time()

# Ensure directories exist
for folder in [DATA_DIR, XSTREAM_UPLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize files
def init_files():
    files_with_empty_list = [
        DATA_FILE, WARNS_FILE, SHIFTS_FILE, XSTREAM_DATA_FILE, 
        LIVE_STREAMS_FILE, FORUM_POSTS_FILE
    ]
    files_with_empty_dict = [
        LIVE_CHAT_FILE, BLACKLIST_FILE, IP_WARNINGS_FILE
    ]
    
    for file_path in files_with_empty_list:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump([], f)
                
    for file_path in files_with_empty_dict:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)

init_files()
