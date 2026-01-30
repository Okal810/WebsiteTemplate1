"""
Centralized Validation Configuration

All validation thresholds and constants in one place.
Eliminates magic numbers and ensures consistency across the codebase.
"""


class ValidationConfig:
    """Configuration constants for application validation."""
    
    # ==================== LENGTH LIMITS ====================
    
    # About Me / Text fields
    MIN_ABOUT_ME_LENGTH = 15
    MAX_ABOUT_ME_LENGTH = 5000
    
    # Roblox username
    MIN_ROBLOX_NAME_LENGTH = 3
    MAX_ROBLOX_NAME_LENGTH = 20
    
    # Discord username
    MIN_DISCORD_NAME_LENGTH = 2
    MAX_DISCORD_NAME_LENGTH = 32
    
    # Age
    MIN_AGE = 1
    MAX_AGE = 99
    
    # ==================== RATE LIMITING ====================
    
    # Time between application submissions (seconds)
    RATE_LIMIT_SECONDS = 60
    
    # Minimum time to fill out form before submission (bot detection)
    MIN_SUBMIT_DELAY_SECONDS = 5
    
    # ==================== SPAM DETECTION ====================
    
    # Paste detection threshold (characters)
    PASTE_WARNING_THRESHOLD = 500
    
    # Semantic similarity threshold (0.0 to 1.0)
    SIMILARITY_THRESHOLD = 0.85
    
    # ==================== VALID PATTERNS ====================
    
    # Roblox username regex pattern
    ROBLOX_NAME_PATTERN = r'^[a-zA-Z0-9_]+$'
