"""
Recording Manager implementation for handling recording sessions.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from src.interfaces import IStorageManager, IRoomManager, IRecordingManager
from src.models import RecordingSession

logger = logging.getLogger(__name__)


class RecordingManager(IRecordingManager):
    """Manages recording sessions for rooms."""
    
    def __init__(self, storage_manager: IStorageManager, room_manager: IRoomManager):
        self.storage_manager = storage_manager
        self.room_manager = room_manager
        self._active_recordings: Dict[str, RecordingSession] = {}
        self._recording_history: Dict[str, RecordingSession] = {}
        logger.info("RecordingManager initialized")
    
    async def start_recording(self, room_id: str) -> str:
        """Start recording for a room and return the session ID."""
        room = self.room_manager.get_room(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")
        
        # Check if recording is already active for this room
        if room_id in self._active_recordings:
            existing_session = self._active_recordings[room_id]
            logger.warning(f"Recording already active for room {room_id}, session {existing_session.session_id}")
            return existing_session.session_id
        
        # Create new recording session
        recording = RecordingSession(
            session_id=room.session_id,
            room_id=room_id,
            started_at=datetime.now(),
            status="active"
        )
        
        # Add to active recordings
        self._active_recordings[room_id] = recording
        
        # Ensure session folder exists
        await self.storage_manager.session_manager.create_session_folder(room.session_id)
        
        logger.info(f"Started recording for room {room_id}, session {room.session_id}")
        return room.session_id
    
    async def stop_recording(self, room_id: str) -> Optional[RecordingSession]:
        """Stop recording for a room and return the recording session."""
        if room_id not in self._active_recordings:
            logger.warning(f"No active recording found for room {room_id}")
            return None
        
        # Get and update recording session
        recording = self._active_recordings[room_id]
        recording.ended_at = datetime.now()
        recording.status = "stopped"
        
        # Move from active to history
        del self._active_recordings[room_id]
        self._recording_history[recording.session_id] = recording
        
        logger.info(f"Stopped recording for room {room_id}, session {recording.session_id}")
        logger.info(f"Recording duration: {recording.duration:.2f} seconds")
        
        return recording
    
    async def save_recording(self, session_id: str, filename: str, data: bytes) -> str:
        """Save recording data to the session folder."""
        try:
            filepath = await self.storage_manager.save_file(session_id, filename, data)
            
            # Update recording session files list
            recording = await self.get_recording_session(session_id)
            if recording:
                import os
                recording.files.append(os.path.basename(filepath))
            
            logger.info(f"Saved recording file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving recording for session {session_id}: {e}")
            
            # Mark recording as error if it exists in active recordings
            for recording in self._active_recordings.values():
                if recording.session_id == session_id:
                    recording.status = "error"
                    break
            
            raise
    
    def get_active_recordings(self) -> Dict[str, RecordingSession]:
        """Get all active recording sessions."""
        return self._active_recordings.copy()
    
    async def get_recording_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get a recording session by session ID."""
        # Check active recordings first
        for recording in self._active_recordings.values():
            if recording.session_id == session_id:
                return recording
        
        # Check recording history
        return self._recording_history.get(session_id)
    
    def is_room_recording(self, room_id: str) -> bool:
        """Check if a room is currently being recorded."""
        return room_id in self._active_recordings
    
    def get_room_recording_session(self, room_id: str) -> Optional[RecordingSession]:
        """Get the active recording session for a room."""
        return self._active_recordings.get(room_id)
    
    async def force_stop_recording(self, room_id: str, reason: str = "forced") -> Optional[RecordingSession]:
        """Force stop a recording session with a reason."""
        if room_id not in self._active_recordings:
            return None
        
        recording = self._active_recordings[room_id]
        recording.ended_at = datetime.now()
        recording.status = f"stopped ({reason})"
        
        # Move to history
        del self._active_recordings[room_id]
        self._recording_history[recording.session_id] = recording
        
        logger.warning(f"Force stopped recording for room {room_id}: {reason}")
        return recording
    
    async def cleanup_room_recording(self, room_id: str) -> bool:
        """Clean up recording when a room is deleted."""
        if room_id in self._active_recordings:
            await self.force_stop_recording(room_id, "room deleted")
            return True
        return False
    
    def get_recording_duration(self, room_id: str) -> Optional[float]:
        """Get the current duration of an active recording in seconds."""
        if room_id not in self._active_recordings:
            return None
        
        recording = self._active_recordings[room_id]
        current_time = datetime.now()
        return (current_time - recording.started_at).total_seconds()
    
    async def get_session_recording_files(self, session_id: str) -> list:
        """Get list of recording files for a session."""
        try:
            files = await self.storage_manager.get_session_files(session_id)
            # Filter for common recording file types
            recording_extensions = ['.mp4', '.webm', '.wav', '.mp3', '.ogg', '.m4a']
            recording_files = [
                f for f in files 
                if any(f.lower().endswith(ext) for ext in recording_extensions)
            ]
            return recording_files
        except Exception as e:
            logger.error(f"Error getting recording files for session {session_id}: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get recording statistics."""
        total_recordings = len(self._recording_history)
        active_recordings = len(self._active_recordings)
        
        # Calculate total recording time
        total_duration = 0
        for recording in self._recording_history.values():
            if recording.duration:
                total_duration += recording.duration
        
        # Calculate average recording duration
        avg_duration = total_duration / total_recordings if total_recordings > 0 else 0
        
        return {
            "total_recordings": total_recordings,
            "active_recordings": active_recordings,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration
        }
    
    async def cleanup_old_recordings(self, days_old: int = 30) -> int:
        """Clean up old recording sessions from history. Returns count cleaned up."""
        if days_old <= 0:
            return 0
        
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        sessions_to_remove = []
        for session_id, recording in self._recording_history.items():
            if recording.ended_at and recording.ended_at.timestamp() < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self._recording_history[session_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old recording sessions")
        
        return cleaned_count