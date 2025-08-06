"""
Session Manager implementation for handling session folders.
"""

import os
import shutil
import logging
from typing import Set

from src.interfaces import ISessionManager
from src.config import SESSIONS_BASE_PATH

logger = logging.getLogger(__name__)


class SessionManager(ISessionManager):
    """Manages session folders and their lifecycle."""
    
    def __init__(self, base_path: str = SESSIONS_BASE_PATH):
        self.base_path = base_path
        self._active_sessions: Set[str] = set()
        
        # Create base directory if it doesn't exist
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            logger.info(f"Created sessions base directory: {base_path}")
        
        # Load existing session folders
        self._load_existing_sessions()
        logger.info(f"SessionManager initialized with base path: {base_path}")
    
    def _load_existing_sessions(self):
        """Load existing session folders on startup."""
        try:
            if os.path.exists(self.base_path):
                for item in os.listdir(self.base_path):
                    item_path = os.path.join(self.base_path, item)
                    if os.path.isdir(item_path):
                        self._active_sessions.add(item)
                        logger.debug(f"Loaded existing session: {item}")
            
            logger.info(f"Loaded {len(self._active_sessions)} existing sessions")
        except Exception as e:
            logger.error(f"Error loading existing sessions: {e}")
    
    async def create_session_folder(self, session_id: str) -> str:
        """Create a folder for a session and return the path."""
        session_path = os.path.join(self.base_path, session_id)
        
        try:
            if not os.path.exists(session_path):
                os.makedirs(session_path, exist_ok=True)
                self._active_sessions.add(session_id)
                logger.info(f"Created session folder: {session_path}")
            else:
                logger.debug(f"Session folder already exists: {session_path}")
            
            return session_path
            
        except Exception as e:
            logger.error(f"Error creating session folder {session_path}: {e}")
            raise
    
    async def get_session_path(self, session_id: str) -> str:
        """Get the path for a session, creating it if needed."""
        session_path = os.path.join(self.base_path, session_id)
        
        if not os.path.exists(session_path):
            return await self.create_session_folder(session_id)
        
        return session_path
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session folder exists."""
        session_path = os.path.join(self.base_path, session_id)
        return os.path.exists(session_path) and os.path.isdir(session_path)
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session folder and its contents."""
        try:
            session_path = os.path.join(self.base_path, session_id)
            
            if os.path.exists(session_path):
                # Remove the entire directory and its contents
                shutil.rmtree(session_path)
                self._active_sessions.discard(session_id)
                logger.info(f"Cleaned up session folder: {session_path}")
                return True
            else:
                logger.warning(f"Session folder does not exist: {session_path}")
                self._active_sessions.discard(session_id)
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def get_active_sessions(self) -> Set[str]:
        """Get all active session IDs."""
        return self._active_sessions.copy()
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        return len(self._active_sessions)
    
    async def get_session_size(self, session_id: str) -> int:
        """Get the total size of a session folder in bytes."""
        session_path = os.path.join(self.base_path, session_id)
        
        if not os.path.exists(session_path):
            return 0
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(session_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            logger.error(f"Error calculating session size for {session_id}: {e}")
            return 0
    
    async def get_session_file_count(self, session_id: str) -> int:
        """Get the number of files in a session folder."""
        session_path = os.path.join(self.base_path, session_id)
        
        if not os.path.exists(session_path):
            return 0
        
        try:
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(session_path):
                file_count += len(filenames)
            return file_count
        except Exception as e:
            logger.error(f"Error counting files in session {session_id}: {e}")
            return 0
    
    async def cleanup_empty_sessions(self) -> int:
        """Clean up all empty session folders. Returns the number cleaned up."""
        cleaned_count = 0
        
        try:
            sessions_to_cleanup = []
            
            for session_id in self._active_sessions.copy():
                file_count = await self.get_session_file_count(session_id)
                if file_count == 0:
                    sessions_to_cleanup.append(session_id)
            
            for session_id in sessions_to_cleanup:
                if await self.cleanup_session(session_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} empty session folders")
            
        except Exception as e:
            logger.error(f"Error during empty session cleanup: {e}")
        
        return cleaned_count
    
    def get_stats(self) -> dict:
        """Get session statistics."""
        return {
            "active_sessions": len(self._active_sessions),
            "base_path": self.base_path,
            "base_path_exists": os.path.exists(self.base_path)
        }