"""
Room Manager implementation for handling chat rooms.
"""

import logging
from typing import Dict, List, Optional

from src.interfaces import IConnectionManager, IRoomManager
from src.models import Room
from src.config import MAX_USERS_PER_ROOM

logger = logging.getLogger(__name__)


class RoomManager(IRoomManager):
    """Manages chat rooms and user room membership."""
    
    def __init__(self, connection_manager: IConnectionManager):
        self._rooms: Dict[str, Room] = {}
        self._connection_manager = connection_manager
        logger.info("RoomManager initialized")
    
    async def create_room(self, room_id: str, max_users: int = MAX_USERS_PER_ROOM) -> Room:
        """Create a new room or return existing one."""
        if room_id not in self._rooms:
            room = Room(id=room_id, users=[], max_users=max_users)
            self._rooms[room_id] = room
            logger.info(f"Created room: {room_id} with session: {room.session_id} (max users: {max_users})")
        else:
            logger.debug(f"Room {room_id} already exists")
        
        return self._rooms[room_id]
    
    async def join_room(self, user_id: str, room_id: str) -> bool:
        """Add a user to a room. Returns True if successful."""
        user = self._connection_manager.get_user(user_id)
        if not user:
            logger.warning(f"User {user_id} not found when trying to join room {room_id}")
            return False
        
        # Create room if it doesn't exist
        await self.create_room(room_id)
        room = self._rooms[room_id]
        
        # Check room capacity
        if room.is_full and user_id not in room.users:
            logger.warning(f"Room {room_id} is full ({room.user_count}/{room.max_users})")
            return False
        
        # Leave current room if user is in one
        old_room_id = await self.leave_room(user_id)
        if old_room_id:
            logger.info(f"User {user_id} left room {old_room_id} to join {room_id}")
        
        # Join new room (if not already in it)
        if user_id not in room.users:
            room.users.append(user_id)
            user.room_id = room_id
            logger.info(f"User {user_id} joined room {room_id} ({room.user_count}/{room.max_users})")
        else:
            logger.debug(f"User {user_id} already in room {room_id}")
        
        return True
    
    async def leave_room(self, user_id: str) -> Optional[str]:
        """Remove a user from their current room. Returns the room ID they left."""
        user = self._connection_manager.get_user(user_id)
        if not user or not user.room_id:
            return None
        
        room_id = user.room_id
        room = self._rooms.get(room_id)
        
        if room and user_id in room.users:
            room.users.remove(user_id)
            user.room_id = None
            
            logger.info(f"User {user_id} left room {room_id} ({room.user_count}/{room.max_users} remaining)")
            
            # Clean up empty rooms
            if not room.users:
                del self._rooms[room_id]
                logger.info(f"Deleted empty room: {room_id}")
            
            return room_id
        
        # Clean up user state even if room doesn't exist
        if user:
            user.room_id = None
        
        return None
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        return self._rooms.get(room_id)
    
    def get_room_users(self, room_id: str) -> List[str]:
        """Get list of user IDs in a room."""
        room = self.get_room(room_id)
        return room.users.copy() if room else []
    
    def get_all_rooms(self) -> Dict[str, Room]:
        """Get all rooms."""
        return self._rooms.copy()
    
    def get_user_room_id(self, user_id: str) -> Optional[str]:
        """Get the room ID that a user is currently in."""
        user = self._connection_manager.get_user(user_id)
        return user.room_id if user else None
    
    def is_room_full(self, room_id: str) -> bool:
        """Check if a room is at capacity."""
        room = self.get_room(room_id)
        return room.is_full if room else False
    
    def get_available_rooms(self) -> List[Room]:
        """Get all rooms that are not at capacity."""
        return [room for room in self._rooms.values() if not room.is_full]
    
    def get_room_count(self) -> int:
        """Get the total number of rooms."""
        return len(self._rooms)
    
    def get_stats(self) -> Dict[str, any]:
        """Get room statistics."""
        total_rooms = len(self._rooms)
        full_rooms = sum(1 for room in self._rooms.values() if room.is_full)
        empty_rooms = sum(1 for room in self._rooms.values() if not room.users)
        total_users_in_rooms = sum(len(room.users) for room in self._rooms.values())
        
        return {
            "total_rooms": total_rooms,
            "full_rooms": full_rooms,
            "empty_rooms": empty_rooms,
            "available_rooms": total_rooms - full_rooms,
            "total_users_in_rooms": total_users_in_rooms,
            "average_users_per_room": total_users_in_rooms / total_rooms if total_rooms > 0 else 0
        }
    
    async def cleanup_room(self, room_id: str) -> bool:
        """Force cleanup of a room and all its users."""
        room = self.get_room(room_id)
        if not room:
            return False
        
        # Remove all users from the room
        users_to_remove = room.users.copy()
        for user_id in users_to_remove:
            await self.leave_room(user_id)
        
        # Remove the room
        if room_id in self._rooms:
            del self._rooms[room_id]
            logger.info(f"Force cleaned up room: {room_id}")
            return True
        
        return False