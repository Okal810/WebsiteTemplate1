import time
import re
import hashlib
import math
from collections import Counter
from app.config import MAX_CONTENT_HISTORY

RECENT_CONTENT_HASHES = {}
RECENT_IPS_TRACKED = []

BLACKLIST_KEYWORDS = [
    'huso', 'nazi', 'hitler', 'negger', 'fick', 'schlampe', 'wichser',
    'copypasta', 'testbewerbung', 'arschloch', 'fotze'
]

def get_cosine_similarity(text1, text2):
    """Calculates a simple cosine similarity between two texts."""
    def text_to_vector(text):
        # Simple regex for words, removes special characters
        words = re.findall(r'\w+', text.lower())
        return Counter(words)

    vec1 = text_to_vector(text1)
    vec2 = text_to_vector(text2)

    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def check_semantic_similarity(content, threshold=0.85):
    """
    Checks if the content is too similar to an existing application.
    Returns (is_similar, reason).
    """
    from app.models import Application
    try:
        # We only check the last 50 applications to save performance
        recent_apps = Application.query.order_by(Application.timestamp.desc()).limit(50).all()
        for app in recent_apps:
            # Compare about me
            if app.about_me:
                score = get_cosine_similarity(content, app.about_me)
                if score > threshold:
                    return True, "Über-mich"
            
            # Compare motivation if available
            if app.motivation:
                score = get_cosine_similarity(content, app.motivation)
                if score > threshold:
                    return True, "Motivation"
        
        return False, None
    except Exception:
        return False, None

def contains_blacklisted_keywords(text):
    """Checks if the text contains forbidden words."""
    if not text: return False
    lowered = text.lower()
    for word in BLACKLIST_KEYWORDS:
        if word in lowered:
            return True
    return False


def check_duplicate_fields(data, min_length=5):
    """
    Checks if multiple fields have the same content (spam indicator).
    Returns True if duplicates were found.
    """
    values = {}
    duplicates = []
    
    # Fields that are allowed to be the same (e.g., roblox_user and discord_name)
    allowed_same = [('roblox_user', 'discord_name'), ('discord_name', 'roblox_user')]
    
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        val_clean = value.strip().lower()
        if len(val_clean) >= min_length:
            if val_clean in values:
                existing_key = values[val_clean]
                # Check if this combination is allowed
                if (key, existing_key) not in allowed_same and (existing_key, key) not in allowed_same:
                    duplicates.append((existing_key, key))
            else:
                values[val_clean] = key
    
    return len(duplicates) > 0, duplicates


def load_blacklist():
    """Loads the blacklist from the database."""
    from app.models import Blacklist
    try:
        entries = Blacklist.query.all()
        return {entry.ip_hash: entry.to_dict() for entry in entries}
    except Exception:
        return {}


def load_warnings():
    """Loads all IP warnings from the database, grouped by IP hash."""
    from app.models import IPWarning
    try:
        warnings = IPWarning.query.order_by(IPWarning.timestamp).all()
        result = {}
        for w in warnings:
            if w.ip_hash not in result:
                result[w.ip_hash] = []
            result[w.ip_hash].append(w.to_dict())
        return result
    except Exception:
        return {}


def is_ip_blacklisted(ip_hash):
    """Checks if an IP is blocked."""
    from app.models import db, Blacklist
    try:
        entry = Blacklist.query.get(ip_hash)
        if entry:
            # Expired?
            if entry.expires_at and time.time() > entry.expires_at:
                db.session.delete(entry)
                db.session.commit()
                return False, {}
            return True, entry.to_dict()
        return False, {}
    except Exception:
        return False, {}


def add_to_blacklist(ip_hash, reason, duration_hours=24, moderator=None):
    """Adds an IP to the blacklist or updates the entry."""
    from app.models import db, Blacklist
    try:
        expires_at = time.time() + (duration_hours * 3600) if duration_hours else None
        
        entry = Blacklist.query.get(ip_hash)
        if entry:
            entry.reason = reason
            entry.expires_at = expires_at
            entry.moderator = moderator or "auto_mod"
            entry.timestamp = time.time()
        else:
            entry = Blacklist(
                ip_hash=ip_hash,
                reason=reason,
                expires_at=expires_at,
                moderator=moderator or "auto_mod",
                timestamp=time.time()
            )
            db.session.add(entry)
        
        db.session.commit()
    except Exception:
        db.session.rollback()


def add_ip_warning(ip_hash, reason, moderator="auto_mod"):
    """Adds an IP warning and checks for automatic block."""
    from app.models import db, IPWarning
    try:
        new_warning = IPWarning(
            ip_hash=ip_hash,
            reason=reason,
            moderator=moderator,
            timestamp=time.time()
        )
        db.session.add(new_warning)
        db.session.commit()
        
        # Count warnings
        warn_count = IPWarning.query.filter_by(ip_hash=ip_hash).count()
        
        auto_blocked = False
        if warn_count >= 3:
            auto_blocked = True
            reason_bl = f"Auto-Mod: Too many warnings ({warn_count})" if warn_count < 10 else "Auto-Mod: Extreme spamming behavior"
            duration = 24 if warn_count < 10 else None
            add_to_blacklist(ip_hash, reason_bl, duration_hours=duration)
        
        return warn_count, auto_blocked
    except Exception:
        db.session.rollback()
        return 0, False


def remove_from_blacklist(ip_hash):
    """Removes an IP from the blacklist."""
    from app.models import db, Blacklist
    try:
        entry = Blacklist.query.get(ip_hash)
        if entry:
            db.session.delete(entry)
            db.session.commit()
    except Exception:
        db.session.rollback()


def cleanup_expired_entries():
    """Cleans up expired blacklist entries."""
    from app.models import db, Blacklist
    try:
        current_time = time.time()
        expired = Blacklist.query.filter(
            Blacklist.expires_at.isnot(None),
            Blacklist.expires_at < current_time
        ).all()
        
        for entry in expired:
            db.session.delete(entry)
        
        if expired:
            db.session.commit()
    except Exception:
        db.session.rollback()


def looks_like_spam(text):
    if not text or len(text) < 3:
        return False
    lowered = text.lower().strip()
    
    # 1. Repeated characters (e.g., aaaaaa)
    if re.search(r'(.)\1{4,}', lowered): return True
    
    # 2. Keyboard patterns
    keyboard_patterns = ['asdf', 'qwer', 'zxcv', 'hjkl', 'yxcv', 'uiop']
    for pattern in keyboard_patterns:
        if (pattern * 2) in lowered: return True
        
    # 3. Known test words
    if re.match(r'^test+$', lowered): return True
    
    # 4. Only numbers
    if lowered.isdigit() and len(lowered) < 4: return True
    
    # 5. Senseless consonant accumulation (low vowel ratio)
    if len(lowered) >= 8:
        vowels = len(re.findall(r'[aeiouäöü]', lowered))
        letters = len(re.findall(r'[a-zäöü]', lowered))
        if letters > 0 and (vowels / letters) < 0.15: return True
        
    # 6. Repetitive words (Copy-Paste Spam)
    words = lowered.split()
    if len(words) > 10:
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.3: return True
        
    # 7. Blacklist keywords
    if contains_blacklisted_keywords(lowered):
        return True
        
    return False


def check_content_repetition(ip_hash, content):
    if not content or len(content) < 10:
        return False, False
    
    # Memory Leak Prevention: Eviction Policy for IPs
    if ip_hash not in RECENT_CONTENT_HASHES:
        if len(RECENT_IPS_TRACKED) >= 1000:  # Limit tracked IPs to 1000
            oldest_ip = RECENT_IPS_TRACKED.pop(0)
            if oldest_ip in RECENT_CONTENT_HASHES:
                del RECENT_CONTENT_HASHES[oldest_ip]
        
        RECENT_CONTENT_HASHES[ip_hash] = []
        RECENT_IPS_TRACKED.append(ip_hash)
    
    content_hash = hashlib.md5(content.encode()).hexdigest()
    if content_hash in RECENT_CONTENT_HASHES[ip_hash]:
        return True, False # Repetition detected, but don't auto-warn
    
    RECENT_CONTENT_HASHES[ip_hash].append(content_hash)
    if len(RECENT_CONTENT_HASHES[ip_hash]) > MAX_CONTENT_HISTORY:
        RECENT_CONTENT_HASHES[ip_hash].pop(0)
        
    return False, False
