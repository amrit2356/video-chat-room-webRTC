"""
Connection Manager implementation for handling WebSocket connections.
"""

import logging
from typing import Dict, Optional
from aiohttp import web_ws

from src.interfaces import IConnectionManager
from src.models import User

logger = logging.getLogger(__name__)


class ConnectionManager(IConnectionManager):
    """Manages WebSocket connections and user lifecycle."""
    
    def __init__(self):
        self._connections: Dict[str, User] = {}
        logger.info("ConnectionManager initialized")
    
    async def add_connection(self, user_id: str, websocket: web_ws.WebSocketResponse) -> User:
        """Add a new user connection."""
        user = User(id=user_id, websocket=websocket)
        self._connections[user_id] = user
        logger.info(f"Added connection: {user_id}")
        return user
    
    async def remove_connection(self, user_id: str) -> None:
        """Remove a user connection and cleanup resources."""
        if user_id not in self._connections:
            logger.warning(f"Attempted to remove non-existent connection: {user_id}")
            return
        
        user = self._connections[user_id]
        
        # Clean up user resources
        await self.cleanup_user_resources(user)
        
        # Remove from connections
        del self._connections[user_id]
        logger.info(f"Removed connection: {user_id}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self._connections.get(user_id)
    
    def get_all_users(self) -> Dict[str, User]:
        """Get all connected users."""
        return self._connections.copy()
    
    async def cleanup_user_resources(self, user: User) -> None:
        """Clean up all resources associated with a user."""
        try:
            # Close all peer connections
            for target_id, pc in user.peer_connections.items():
                try:
                    await pc.close()
                    logger.debug(f"Closed peer connection from {user.id} to {target_id}")
                except Exception as e:
                    logger.error(f"Error closing peer connection from {user.id} to {target_id}: {e}")
            
            # Clear peer connections
            user.peer_connections.clear()
            
            # Close WebSocket if still open
            if not user.websocket.closed:
                try:
                    await user.websocket.close()
                    logger.debug(f"Closed WebSocket for user {user.id}")
                except Exception as e:
                    logger.error(f"Error closing WebSocket for user {user.id}: {e}")
            
            logger.info(f"Cleaned up resources for user: {user.id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup for user {user.id}: {e}")
    
    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self._connections)
    
    def get_users_in_room(self, room_id: str) -> Dict[str, User]:
        """Get all users currently in a specific room."""
        return {
            user_id: user for user_id, user in self._connections.items()
            if user.room_id == room_id
        }
    
    async def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Check if WebSocket is still open
        return not user.websocket.closed
    
    def get_stats(self) -> Dict[str, int]:
        """Get connection statistics."""
        total_connections = len(self._connections)
        users_in_rooms = sum(1 for user in self._connections.values() if user.room_id)
        users_without_rooms = total_connections - users_in_rooms
        
        return {
            "total_connections": total_connections,
            "users_in_rooms": users_in_rooms,
            "users_without_rooms": users_without_rooms
        }