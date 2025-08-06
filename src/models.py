"""
Data models for the Video Chat Room application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from aiohttp import web_ws
from aiortc import RTCPeerConnection


@dataclass
class User:
    """Represents a user in the video chat system."""
    id: str
    websocket: web_ws.WebSocketResponse
    room_id: Optional[str] = None
    peer_connections: Dict[str, RTCPeerConnection] = field(default_factory=dict)
    joined_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"User(id={self.id}, room={self.room_id})"


@dataclass
class Room:
    """Represents a chat room with multiple users."""
    id: str
    users: List[str] = field(default_factory=list)
    max_users: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str = field(default_factory=lambda: None)
    
    def __post_init__(self):
        if self.session_id is None:
            import uuid
            self.session_id = str(uuid.uuid4())
    
    @property
    def is_full(self) -> bool:
        """Check if the room has reached its maximum capacity."""
        return len(self.users) >= self.max_users
    
    @property
    def user_count(self) -> int:
        """Get the current number of users in the room."""
        return len(self.users)
    
    def __str__(self) -> str:
        return f"Room(id={self.id}, users={self.user_count}/{self.max_users})"


@dataclass
class RecordingSession:
    """Represents a recording session for a room."""
    session_id: str
    room_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    files: List[str] = field(default_factory=list)
    status: str = "active"  # active, stopped, error
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the recording session in seconds."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if the recording session is currently active."""
        return self.status == "active" and self.ended_at is None
    
    def __str__(self) -> str:
        return f"RecordingSession(id={self.session_id}, room={self.room_id}, status={self.status})"


@dataclass
class FileUpload:
    """Represents an uploaded file."""
    filename: str
    original_filename: str
    session_id: str
    file_type: str  # audio, video
    uploaded_at: datetime = field(default_factory=datetime.now)
    file_size: int = 0
    file_path: str = ""
    
    def __str__(self) -> str:
        return f"FileUpload(filename={self.filename}, type={self.file_type}, size={self.file_size})"


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message."""
    type: str
    data: dict
    user_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> dict:
        """Convert the message to a JSON-serializable dictionary."""
        return {
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            **self.data
        }
    
    @classmethod
    def from_json(cls, data: dict, user_id: str) -> 'WebSocketMessage':
        """Create a message from JSON data."""
        msg_type = data.pop("type", "unknown")
        return cls(type=msg_type, data=data, user_id=user_id)