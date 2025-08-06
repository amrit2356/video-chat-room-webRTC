"""
Storage Manager implementation for handling file operations.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from src.interfaces import ISessionManager, IStorageManager
from src.config import MAX_FILE_SIZE, ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


class StorageManager(IStorageManager):
    """Manages file storage operations within session folders."""
    
    def __init__(self, session_manager: ISessionManager):
        self.session_manager = session_manager
        self.max_file_size = MAX_FILE_SIZE
        self.allowed_extensions = ALLOWED_EXTENSIONS
        logger.info("StorageManager initialized")
    
    async def save_file(self, session_id: str, filename: str, data: bytes) -> str:
        """Save a file to the session folder and return the file path."""
        # Validate file size
        if len(data) > self.max_file_size:
            raise ValueError(f"File size ({len(data)} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)")
        
        # Get session path
        session_path = await self.session_manager.get_session_path(session_id)
        
        # Generate unique filename
        unique_filename = self._generate_unique_filename(filename)
        filepath = os.path.join(session_path, unique_filename)
        
        try:
            # Write file to disk
            with open(filepath, 'wb') as f:
                f.write(data)
            
            logger.info(f"File saved: {filepath} ({len(data)} bytes)")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving file {filepath}: {e}")
            raise
    
    async def get_session_files(self, session_id: str) -> List[str]:
        """Get list of files in a session folder."""
        session_path = await self.session_manager.get_session_path(session_id)
        
        try:
            if os.path.exists(session_path):
                files = []
                for item in os.listdir(session_path):
                    item_path = os.path.join(session_path, item)
                    if os.path.isfile(item_path):
                        files.append(item)
                return sorted(files)  # Sort for consistent ordering
            return []
        except Exception as e:
            logger.error(f"Error listing files in session {session_id}: {e}")
            return []
    
    async def get_file_path(self, session_id: str, filename: str) -> Optional[str]:
        """Get the full path to a file in a session."""
        session_path = await self.session_manager.get_session_path(session_id)
        filepath = os.path.join(session_path, filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return filepath
        return None
    
    async def delete_file(self, session_id: str, filename: str) -> bool:
        """Delete a file from a session folder."""
        try:
            filepath = await self.get_file_path(session_id, filename)
            if filepath:
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
                return True
            else:
                logger.warning(f"File not found for deletion: {filename} in session {session_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {filename} from session {session_id}: {e}")
            return False
    
    async def get_session_size(self, session_id: str) -> int:
        """Get the total size of all files in a session (in bytes)."""
        return await self.session_manager.get_session_size(session_id)
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename with timestamp and UUID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Split filename and extension
        if '.' in original_filename:
            base_name, ext = os.path.splitext(original_filename)
        else:
            base_name, ext = original_filename, ''
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())[:8]
        
        # Create unique filename
        unique_filename = f"{base_name}_{timestamp}_{unique_id}{ext}"
        
        return unique_filename
    
    def _validate_file_extension(self, filename: str, file_type: str) -> bool:
        """Validate if the file extension is allowed for the given file type."""
        if file_type not in self.allowed_extensions:
            return False
        
        _, ext = os.path.splitext(filename.lower())
        return ext in self.allowed_extensions[file_type]
    
    async def get_file_info(self, session_id: str, filename: str) -> Optional[dict]:
        """Get detailed information about a file."""
        filepath = await self.get_file_path(session_id, filename)
        if not filepath:
            return None
        
        try:
            stat = os.stat(filepath)
            return {
                "filename": filename,
                "filepath": filepath,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": os.path.splitext(filename)[1].lower()
            }
        except Exception as e:
            logger.error(f"Error getting file info for {filepath}: {e}")
            return None
    
    async def get_session_file_details(self, session_id: str) -> List[dict]:
        """Get detailed information about all files in a session."""
        files = await self.get_session_files(session_id)
        file_details = []
        
        for filename in files:
            info = await self.get_file_info(session_id, filename)
            if info:
                file_details.append(info)
        
        return file_details
    
    async def cleanup_old_files(self, session_id: str, days_old: int = 7) -> int:
        """Clean up files older than specified days. Returns number of files deleted."""
        if days_old <= 0:
            return 0
        
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        try:
            files = await self.get_session_files(session_id)
            
            for filename in files:
                filepath = await self.get_file_path(session_id, filename)
                if filepath:
                    stat = os.stat(filepath)
                    if stat.st_mtime < cutoff_time:
                        if await self.delete_file(session_id, filename):
                            deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files from session {session_id}")
            
        except Exception as e:
            logger.error(f"Error during file cleanup for session {session_id}: {e}")
        
        return deleted_count
    
    def get_stats(self) -> dict:
        """Get storage statistics."""
        return {
            "max_file_size": self.max_file_size,
            "allowed_extensions": self.allowed_extensions
        }