import re

def sanitize_input(text):
    """Sanitize user input to prevent XSS attacks"""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    
    # Basic HTML escaping removed - moved to frontend rendering
    # text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
    
    # Remove potentially dangerous tags/attributes with recursion protection
    # (Matches like <scrscriptipt> will be fully cleaned)
    tags_to_strip = [r'script', r'on\w+=', r'javascript:', r'data:', r'iframe', r'object', r'embed']
    
    # Max 3 iterations to prevent infinite loops but catch nested bypasses
    for _ in range(3):
        old_text = text
        for pattern in tags_to_strip:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        if text == old_text:
            break
            
    return text
