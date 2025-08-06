"""
Abstract interfaces for the Video Chat Room application.
Following the Dependency Inversion Principle (SOLID).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from aiohttp import web_ws
from aiortc import RTCPeerConnection

from src.models import User, Room, RecordingSession


class IConnectionManager(ABC):
    """Interface for managing WebSocket connections."""
    
    @abstractmethod
    async def add_connection(self, user_id: str, websocket: web_ws.WebSocketResponse) -> User:
        """Add a new user connection."""
        pass
    
    @abstractmethod
    async def remove_connection(self, user_id: str) -> None:
        """Remove a user connection and cleanup resources."""
        pass
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        pass
    
    @abstractmethod
    def get_all_users(self) -> Dict[str, User]:
        """Get all connected users."""
        pass
    
    @abstractmethod
    async def cleanup_user_resources(self, user: User) -> None:
        """Clean up all resources associated with a user."""
        pass


class IRoomManager(ABC):
    """Interface for managing chat rooms."""
    
    @abstractmethod
    async def create_room(self, room_id: str, max_users: int = 5) -> Room:
        """Create a new room or return existing one."""
        pass
    
    @abstractmethod
    async def join_room(self, user_id: str, room_id: str) -> bool:
        """Add a user to a room. Returns True if successful."""
        pass
    
    @abstractmethod
    async def leave_room(self, user_id: str) -> Optional[str]:
        """Remove a user from their current room. Returns the room ID they left."""
        pass
    
    @abstractmethod
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        pass
    
    @abstractmethod
    def get_room_users(self, room_id: str) -> List[str]:
        """Get list of user IDs in a room."""
        pass
    
    @abstractmethod
    def get_all_rooms(self) -> Dict[str, Room]:
        """Get all rooms."""
        pass


class ISessionManager(ABC):
    """Interface for managing session folders and data."""
    
    @abstractmethod
    async def create_session_folder(self, session_id: str) -> str:
        """Create a folder for a session and return the path."""
        pass
    
    @abstractmethod
    async def get_session_path(self, session_id: str) -> str:
        """Get the path for a session, creating it if needed."""
        pass
    
    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session folder exists."""
        pass
    
    @abstractmethod
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session folder and its contents."""
        pass


class IStorageManager(ABC):
    """Interface for file storage operations."""
    
    @abstractmethod
    async def save_file(self, session_id: str, filename: str, data: bytes) -> str:
        """Save a file to the session folder and return the file path."""
        pass
    
    @abstractmethod
    async def get_session_files(self, session_id: str) -> List[str]:
        """Get list of files in a session folder."""
        pass
    
    @abstractmethod
    async def get_file_path(self, session_id: str, filename: str) -> Optional[str]:
        """Get the full path to a file in a session."""
        pass
    
    @abstractmethod
    async def delete_file(self, session_id: str, filename: str) -> bool:
        """Delete a file from a session folder."""
        pass
    
    @abstractmethod
    async def get_session_size(self, session_id: str) -> int:
        """Get the total size of all files in a session (in bytes)."""
        pass


class IWebRTCManager(ABC):
    """Interface for managing WebRTC peer connections."""
    
    @abstractmethod
    async def create_peer_connection(self, user_id: str, target_id: str) -> RTCPeerConnection:
        """Create a peer connection between two users."""
        pass
    
    @abstractmethod
    async def handle_offer(self, user_id: str, target_id: str, offer_data: dict) -> None:
        """Handle a WebRTC offer from one user to another."""
        pass
    
    @abstractmethod
    async def handle_answer(self, user_id: str, target_id: str, answer_data: dict) -> None:
        """Handle a WebRTC answer from one user to another."""
        pass
    
    @abstractmethod
    async def handle_ice_candidate(self, user_id: str, target_id: str, candidate_data: dict) -> None:
        """Handle an ICE candidate from one user to another."""
        pass
    
    @abstractmethod
    async def cleanup_peer_connection(self, user_id: str, target_id: str) -> None:
        """Clean up a peer connection between two users."""
        pass


class IRecordingManager(ABC):
    """Interface for managing recording sessions."""
    
    @abstractmethod
    async def start_recording(self, room_id: str) -> str:
        """Start recording for a room and return the session ID."""
        pass
    
    @abstractmethod
    async def stop_recording(self, room_id: str) -> Optional[RecordingSession]:
        """Stop recording for a room and return the recording session."""
        pass
    
    @abstractmethod
    async def save_recording(self, session_id: str, filename: str, data: bytes) -> str:
        """Save recording data to the session folder."""
        pass
    
    @abstractmethod
    def get_active_recordings(self) -> Dict[str, RecordingSession]:
        """Get all active recording sessions."""
        pass
    
    @abstractmethod
    async def get_recording_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get a recording session by session ID."""
        pass


class INotificationManager(ABC):
    """Interface for managing notifications and broadcasts."""
    
    @abstractmethod
    async def broadcast_to_room(self, room_id: str, message: dict, exclude: Optional[str] = None) -> None:
        """Broadcast a message to all users in a room."""
        pass
    
    @abstractmethod
    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Send a message to a specific user."""
        pass
    
    @abstractmethod
    async def notify_user_joined(self, room_id: str, user_id: str) -> None:
        """Notify all users in a room that someone joined."""
        pass
    
    @abstractmethod
    async def notify_user_left(self, room_id: str, user_id: str) -> None:
        """Notify all users in a room that someone left."""
        pass