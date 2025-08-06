"""
Main Application Controller for the Video Chat Room.
Orchestrates all managers and handles WebSocket communications.
"""

import json
import logging
import uuid
from typing import Optional

from aiohttp import web, WSMsgType, web_ws

from src.managers import (
    ConnectionManager, RoomManager, SessionManager, 
    StorageManager, WebRTCManager, RecordingManager
)
from src.models import WebSocketMessage
from src.config import MAX_USERS_PER_ROOM

logger = logging.getLogger(__name__)


class VideoChatApplication:
    """Main application controller orchestrating all managers."""
    
    def __init__(self):
        # Initialize managers in dependency order
        self.connection_manager = ConnectionManager()
        self.session_manager = SessionManager()
        self.storage_manager = StorageManager(self.session_manager)
        self.room_manager = RoomManager(self.connection_manager)
        self.webrtc_manager = WebRTCManager(self.connection_manager)
        self.recording_manager = RecordingManager(self.storage_manager, self.room_manager)
        
        logger.info("VideoChatApplication initialized with all managers")
    
    async def websocket_handler(self, request) -> web_ws.WebSocketResponse:
        """Handle WebSocket connections from clients."""
        ws = web_ws.WebSocketResponse()
        await ws.prepare(request)
        
        user_id = str(uuid.uuid4())
        user = await self.connection_manager.add_connection(user_id, ws)
        
        logger.info(f"New WebSocket connection: {user_id}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        ws_message = WebSocketMessage.from_json(data, user_id)
                        await self.handle_message(ws_message)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON received from {user_id}")
                        await self.send_error(user_id, "Invalid message format")
                    except Exception as e:
                        logger.error(f"Error processing message from {user_id}: {e}")
                        await self.send_error(user_id, "Internal server error")
                
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error from {user_id}: {ws.exception()}')
        
        except Exception as e:
            logger.error(f"Error in websocket handler for {user_id}: {e}")
        
        finally:
            await self.cleanup_user(user_id)
        
        return ws
    
    async def handle_message(self, message: WebSocketMessage) -> None:
        """Route WebSocket messages to appropriate handlers."""
        message_type = message.type
        user_id = message.user_id
        data = message.data
        
        logger.debug(f"Handling message {message_type} from {user_id}")
        
        try:
            if message_type == "join_room":
                await self.handle_join_room(user_id, data)
            
            elif message_type == "leave_room":
                await self.handle_leave_room(user_id, data)
            
            elif message_type == "offer":
                await self.handle_webrtc_offer(user_id, data)
            
            elif message_type == "answer":
                await self.handle_webrtc_answer(user_id, data)
            
            elif message_type == "ice_candidate":
                await self.handle_ice_candidate(user_id, data)
            
            elif message_type == "start_recording":
                await self.handle_start_recording(user_id, data)
            
            elif message_type == "stop_recording":
                await self.handle_stop_recording(user_id, data)
            
            else:
                logger.warning(f"Unknown message type: {message_type} from {user_id}")
                await self.send_error(user_id, f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error handling {message_type} from {user_id}: {e}")
            await self.send_error(user_id, f"Error processing {message_type}")
    
    async def handle_join_room(self, user_id: str, data: dict) -> None:
        """Handle user joining a room."""
        room_id = data.get("room_id", "default")
        
        # Attempt to join room
        success = await self.room_manager.join_room(user_id, room_id)
        
        if not success:
            await self.send_error(user_id, f"Cannot join room {room_id} (room full or error)")
            return
        
        # Get room information
        room = self.room_manager.get_room(room_id)
        existing_users = [uid for uid in room.users if uid != user_id]
        
        # Send confirmation to user
        await self.send_to_user(user_id, {
            "type": "room_joined",
            "room_id": room_id,
            "user_id": user_id,
            "session_id": room.session_id,
            "existing_users": existing_users,
            "max_users": room.max_users
        })
        
        # Notify existing users
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "user_count": len(room.users)
        }, exclude=user_id)
        
        logger.info(f"User {user_id} joined room {room_id} ({len(room.users)}/{room.max_users})")
    
    async def handle_leave_room(self, user_id: str, data: dict) -> None:
        """Handle user leaving a room."""
        old_room_id = await self.room_manager.leave_room(user_id)
        
        if old_room_id:
            # Stop any recording if user was the last one
            room = self.room_manager.get_room(old_room_id)
            if not room:  # Room was deleted (empty)
                await self.recording_manager.cleanup_room_recording(old_room_id)
            
            # Notify remaining users
            await self.broadcast_to_room(old_room_id, {
                "type": "user_left",
                "user_id": user_id
            }, exclude=user_id)
            
            # Clean up WebRTC connections
            await self.webrtc_manager.cleanup_all_user_connections(user_id)
            
            # Confirm to user
            await self.send_to_user(user_id, {
                "type": "room_left",
                "room_id": old_room_id
            })
            
            logger.info(f"User {user_id} left room {old_room_id}")
    
    async def handle_webrtc_offer(self, user_id: str, data: dict) -> None:
        """Handle WebRTC offer signaling."""
        target_id = data.get("target_id")
        if not target_id:
            await self.send_error(user_id, "Missing target_id in offer")
            return
        
        await self.webrtc_manager.handle_offer(user_id, target_id, data)
    
    async def handle_webrtc_answer(self, user_id: str, data: dict) -> None:
        """Handle WebRTC answer signaling."""
        target_id = data.get("target_id")
        if not target_id:
            await self.send_error(user_id, "Missing target_id in answer")
            return
        
        await self.webrtc_manager.handle_answer(user_id, target_id, data)
    
    async def handle_ice_candidate(self, user_id: str, data: dict) -> None:
        """Handle ICE candidate signaling."""
        target_id = data.get("target_id")
        if not target_id:
            await self.send_error(user_id, "Missing target_id in ICE candidate")
            return
        
        await self.webrtc_manager.handle_ice_candidate(user_id, target_id, data)
    
    async def handle_start_recording(self, user_id: str, data: dict) -> None:
        """Handle request to start recording."""
        user = self.connection_manager.get_user(user_id)
        if not user or not user.room_id:
            await self.send_error(user_id, "Must be in a room to start recording")
            return
        
        try:
            session_id = await self.recording_manager.start_recording(user.room_id)
            
            # Notify user
            await self.send_to_user(user_id, {
                "type": "recording_started",
                "session_id": session_id,
                "room_id": user.room_id
            })
            
            # Notify all users in room
            await self.broadcast_to_room(user.room_id, {
                "type": "recording_status",
                "status": "started",
                "session_id": session_id
            })
            
            logger.info(f"Recording started by {user_id} in room {user.room_id}")
            
        except ValueError as e:
            await self.send_error(user_id, str(e))
    
    async def handle_stop_recording(self, user_id: str, data: dict) -> None:
        """Handle request to stop recording."""
        user = self.connection_manager.get_user(user_id)
        if not user or not user.room_id:
            await self.send_error(user_id, "Must be in a room to stop recording")
            return
        
        recording = await self.recording_manager.stop_recording(user.room_id)
        
        if recording:
            # Notify user
            await self.send_to_user(user_id, {
                "type": "recording_stopped",
                "session_id": recording.session_id,
                "duration": recording.duration
            })
            
            # Notify all users in room
            await self.broadcast_to_room(user.room_id, {
                "type": "recording_status",
                "status": "stopped",
                "session_id": recording.session_id,
                "duration": recording.duration
            })
            
            logger.info(f"Recording stopped by {user_id} in room {user.room_id}")
        else:
            await self.send_error(user_id, "No active recording found")
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude: Optional[str] = None) -> None:
        """Broadcast a message to all users in a room."""
        room_users = self.room_manager.get_room_users(room_id)
        message_str = json.dumps(message)
        
        sent_count = 0
        for user_id in room_users:
            if user_id != exclude:
                user = self.connection_manager.get_user(user_id)
                if user and not user.websocket.closed:
                    try:
                        await user.websocket.send_str(message_str)
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Error broadcasting to {user_id}: {e}")
        
        logger.debug(f"Broadcasted message to {sent_count} users in room {room_id}")
    
    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Send a message to a specific user."""
        user = self.connection_manager.get_user(user_id)
        if not user or user.websocket.closed:
            return False
        
        try:
            await user.websocket.send_str(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return False
    
    async def send_error(self, user_id: str, error_message: str) -> None:
        """Send an error message to a user."""
        await self.send_to_user(user_id, {
            "type": "error",
            "message": error_message
        })
    
    async def cleanup_user(self, user_id: str) -> None:
        """Clean up all resources when a user disconnects."""
        try:
            # Leave room and notify others
            old_room_id = await self.room_manager.leave_room(user_id)
            if old_room_id:
                await self.broadcast_to_room(old_room_id, {
                    "type": "user_left",
                    "user_id": user_id
                }, exclude=user_id)
                
                # Clean up recording if room is empty
                room = self.room_manager.get_room(old_room_id)
                if not room:  # Room was deleted
                    await self.recording_manager.cleanup_room_recording(old_room_id)
            
            # Clean up WebRTC connections
            await self.webrtc_manager.cleanup_all_user_connections(user_id)
            
            # Remove connection
            await self.connection_manager.remove_connection(user_id)
            
            logger.info(f"Cleaned up user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup for user {user_id}: {e}")
    
    async def upload_file(self, request) -> web.Response:
        """Handle file upload with session management."""
        try:
            # Get session ID from query parameters
            session_id = request.query.get('session_id')
            if not session_id:
                return web.json_response({
                    "success": False,
                    "message": "Session ID required"
                }, status=400)
            
            # Read multipart form data
            reader = await request.multipart()
            field = await reader.next()
            
            if not field or field.name not in ['audio', 'video']:
                return web.json_response({
                    "success": False,
                    "message": "No valid audio or video file found"
                }, status=400)
            
            # Read file data
            data = await field.read()
            filename = field.filename or f"{field.name}_upload.bin"
            
            # Save file
            filepath = await self.storage_manager.save_file(session_id, filename, data)
            
            logger.info(f"File uploaded: {filepath} ({len(data)} bytes)")
            
            return web.json_response({
                "success": True,
                "filename": filename,
                "session_id": session_id,
                "file_size": len(data),
                "message": "File uploaded successfully"
            })
            
        except ValueError as e:
            return web.json_response({
                "success": False,
                "message": str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return web.json_response({
                "success": False,
                "message": "Failed to upload file"
            }, status=500)
    
    async def get_session_files(self, request) -> web.Response:
        """Get list of files in a session."""
        session_id = request.match_info.get('session_id')
        if not session_id:
            return web.json_response({
                "success": False,
                "message": "Session ID required"
            }, status=400)
        
        try:
            files = await self.storage_manager.get_session_file_details(session_id)
            session_size = await self.storage_manager.get_session_size(session_id)
            
            return web.json_response({
                "success": True,
                "session_id": session_id,
                "files": files,
                "total_size": session_size,
                "file_count": len(files)
            })
            
        except Exception as e:
            logger.error(f"Error getting session files: {e}")
            return web.json_response({
                "success": False,
                "message": "Failed to get session files"
            }, status=500)
    
    async def get_stats(self, request) -> web.Response:
        """Get application statistics."""
        try:
            stats = {
                "connections": self.connection_manager.get_stats(),
                "rooms": self.room_manager.get_stats(),
                "sessions": self.session_manager.get_stats(),
                "webrtc": self.webrtc_manager.get_stats(),
                "recordings": self.recording_manager.get_stats(),
                "storage": self.storage_manager.get_stats()
            }
            
            return web.json_response({
                "success": True,
                "stats": stats
            })
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return web.json_response({
                "success": False,
                "message": "Failed to get statistics"
            }, status=500)