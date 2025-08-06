"""
Configuration settings for the Video Chat Room application.
"""

import os

# Server Configuration
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 8080))

# Room Configuration
MAX_USERS_PER_ROOM = int(os.getenv('MAX_USERS_PER_ROOM', 5))
DEFAULT_ROOM_ID = os.getenv('DEFAULT_ROOM_ID', 'default')

# Session Configuration
SESSIONS_BASE_PATH = os.getenv('SESSIONS_BASE_PATH', 'sessions')

# WebRTC Configuration
ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"}
]

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
ALLOWED_EXTENSIONS = {
    'audio': ['.mp3', '.wav', '.ogg', '.m4a', '.webm'],
    'video': ['.mp4', '.webm', '.avi', '.mov', '.mkv']
}