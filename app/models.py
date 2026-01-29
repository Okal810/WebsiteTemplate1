"""
SQLAlchemy Database Models - OPTIMIZED
With indices for fast search queries and polling.
"""
from flask_sqlalchemy import SQLAlchemy
import time

db = SQLAlchemy()

# ==================== APPLICATIONS ====================

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.String(50), primary_key=True)
    application_type = db.Column(db.String(50))
    roblox_user = db.Column(db.String(50), nullable=False)
    discord_name = db.Column(db.String(50), nullable=False)
    
    age = db.Column(db.Integer)
    about_me = db.Column(db.Text)
    daily_time = db.Column(db.String(100))
    motivation = db.Column(db.Text)
    why_us = db.Column(db.Text)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    
    # OPTIMIZATION 1: Index on status
    # Admins often filter by "pending". Without an index, the dashboard becomes slow.
    status = db.Column(db.String(20), default='pending', index=True)
    
    ip_hash = db.Column(db.String(64))
    
    # OPTIMIZATION 2: Index on timestamp
    # Allows admins to sort by "Newest first" without burning CPU.
    timestamp = db.Column(db.Float, default=lambda: time.time(), index=True)
    
    def to_dict(self):
        result = {
            'id': self.id,
            'applicationType': self.application_type,
            'roblox_user': self.roblox_user,
            'discord_name': self.discord_name,
            'age': self.age,
            'about_me': self.about_me,
            'daily_time': self.daily_time,
            'status': self.status,
            'ip_hash': self.ip_hash,
            'timestamp': self.timestamp
        }
        if self.motivation: result['motivation'] = self.motivation
        if self.why_us: result['why_us'] = self.why_us
        if self.strengths: result['strengths'] = self.strengths
        if self.weaknesses: result['weaknesses'] = self.weaknesses
        return result

# ==================== FORUM (High Traffic Area) ====================

class ForumPost(db.Model):
    __tablename__ = 'forum_posts'
    
    id = db.Column(db.String(50), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), default='Anonym')
    ip_hash = db.Column(db.String(64))
    
    # OPTIMIZATION 3: The MOST IMPORTANT index
    # Enables delta polling (WHERE timestamp > X) in milliseconds.
    timestamp = db.Column(db.Float, default=lambda: time.time(), index=True)
    
    # cascade='all, delete-orphan' ensures comments are deleted when post is deleted
    comments = db.relationship('ForumComment', backref='post', lazy=True, 
                               cascade='all, delete-orphan')
    
    def to_dict(self, include_comments=True):
        result = {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'ip_hash': self.ip_hash,
            'timestamp': self.timestamp
        }
        if include_comments:
            # Sort comments chronologically
            sorted_comments = sorted(self.comments, key=lambda x: x.timestamp)
            result['comments'] = [c.to_dict() for c in sorted_comments]
        return result

class ForumComment(db.Model):
    __tablename__ = 'forum_comments'
    
    id = db.Column(db.String(50), primary_key=True)
    
    # OPTIMIZATION 4: Index on Foreign Key
    # Accelerates loading of comments for a post significantly.
    post_id = db.Column(db.String(50), db.ForeignKey('forum_posts.id'), nullable=False, index=True)
    
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), default='Anonym')
    ip_hash = db.Column(db.String(64))
    timestamp = db.Column(db.Float, default=lambda: time.time())
    
    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'content': self.content,
            'author': self.author,
            'ip_hash': self.ip_hash,
            'timestamp': self.timestamp
        }

# ==================== SECURITY & ADMIN ====================

class Warn(db.Model):
    __tablename__ = 'warns'
    id = db.Column(db.String(50), primary_key=True)
    # Index is useful here if you frequently check "Does user X have warnings?"
    roblox_user = db.Column(db.String(50), index=True) 
    reason = db.Column(db.Text)
    timestamp = db.Column(db.Float, default=lambda: time.time())
    
    def to_dict(self):
        return {'id': self.id, 'roblox_user': self.roblox_user, 'reason': self.reason, 'timestamp': self.timestamp}

class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.String(50), primary_key=True)
    start_time = db.Column(db.Float, nullable=False)
    end_time = db.Column(db.Float)
    duration = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')
    
    def to_dict(self):
        return {'id': self.id, 'start_time': self.start_time, 'end_time': self.end_time, 'duration': self.duration, 'status': self.status}

class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    ip_hash = db.Column(db.String(64), primary_key=True)
    reason = db.Column(db.String(200))
    expires_at = db.Column(db.Float)
    moderator = db.Column(db.String(50), default='auto_mod')
    timestamp = db.Column(db.Float, default=lambda: time.time())
    
    def to_dict(self):
        return {'ip_hash': self.ip_hash, 'reason': self.reason, 'expires_at': self.expires_at, 'moderator': self.moderator, 'timestamp': self.timestamp}

class IPWarning(db.Model):
    __tablename__ = 'ip_warnings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Already correct: index=True was already here!
    ip_hash = db.Column(db.String(64), nullable=False, index=True)
    reason = db.Column(db.String(200))
    moderator = db.Column(db.String(50), default='auto_mod')
    timestamp = db.Column(db.Float, default=lambda: time.time())
    
    def to_dict(self):
        return {'id': self.id, 'ip_hash': self.ip_hash, 'reason': self.reason, 'moderator': self.moderator, 'timestamp': self.timestamp}

class AdminSession(db.Model):
    __tablename__ = 'admin_sessions'
    token = db.Column(db.String(64), primary_key=True)
    ip_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.Float, default=lambda: time.time())
    expires_at = db.Column(db.Float, nullable=False)
