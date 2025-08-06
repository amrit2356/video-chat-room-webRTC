"""
WebRTC Manager implementation for handling peer-to-peer connections.
"""

import json
import logging
from typing import Optional

from aiortc import RTCPeerConnection
from src.interfaces import IConnectionManager, IWebRTCManager
from src.config import ICE_SERVERS

logger = logging.getLogger(__name__)


class WebRTCManager(IWebRTCManager):
    """Manages WebRTC peer connections between users."""
    
    def __init__(self, connection_manager: IConnectionManager):
        self.connection_manager = connection_manager
        self.ice_servers = ICE_SERVERS
        logger.info(f"WebRTCManager initialized with ICE servers: {self.ice_servers}")
    
    async def create_peer_connection(self, user_id: str, target_id: str) -> RTCPeerConnection:
        """Create a peer connection between two users."""
        user = self.connection_manager.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if connection already exists
        if target_id in user.peer_connections:
            logger.debug(f"Peer connection already exists between {user_id} and {target_id}")
            return user.peer_connections[target_id]
        
        # Create new peer connection
        pc = RTCPeerConnection(configuration={"iceServers": self.ice_servers})
        user.peer_connections[target_id] = pc
        
        # Set up event handlers
        await self._setup_peer_connection_handlers(pc, user_id, target_id)
        
        logger.info(f"Created peer connection between {user_id} and {target_id}")
        return pc
    
    async def _setup_peer_connection_handlers(self, pc: RTCPeerConnection, user_id: str, target_id: str):
        """Set up event handlers for a peer connection."""
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state between {user_id} and {target_id}: {pc.connectionState}")
            
            if pc.connectionState == "failed":
                logger.warning(f"Peer connection failed between {user_id} and {target_id}")
                await self.cleanup_peer_connection(user_id, target_id)
            elif pc.connectionState == "closed":
                logger.info(f"Peer connection closed between {user_id} and {target_id}")
                await self.cleanup_peer_connection(user_id, target_id)
            elif pc.connectionState == "connected":
                logger.info(f"Peer connection established between {user_id} and {target_id}")
        
        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Data channel established between {user_id} and {target_id}: {channel.label}")
            
            @channel.on("open")
            def on_open():
                logger.info(f"Data channel opened: {channel.label}")
            
            @channel.on("message")
            def on_message(message):
                logger.debug(f"Data channel message from {user_id} to {target_id}: {message}")
        
        @pc.on("track")
        def on_track(track):
            logger.info(f"Track received from {user_id} to {target_id}: {track.kind}")
    
    async def handle_offer(self, user_id: str, target_id: str, offer_data: dict) -> None:
        """Handle a WebRTC offer from one user to another."""
        target_user = self.connection_manager.get_user(target_id)
        if not target_user:
            logger.warning(f"Target user {target_id} not found for offer from {user_id}")
            return
        
        if target_user.websocket.closed:
            logger.warning(f"Target user {target_id} WebSocket is closed")
            return
        
        try:
            message = {
                "type": "offer",
                "sdp": offer_data.get("sdp"),
                "from_id": user_id
            }
            
            await target_user.websocket.send_str(json.dumps(message))
            logger.debug(f"Forwarded offer from {user_id} to {target_id}")
            
        except Exception as e:
            logger.error(f"Error forwarding offer from {user_id} to {target_id}: {e}")
    
    async def handle_answer(self, user_id: str, target_id: str, answer_data: dict) -> None:
        """Handle a WebRTC answer from one user to another."""
        target_user = self.connection_manager.get_user(target_id)
        if not target_user:
            logger.warning(f"Target user {target_id} not found for answer from {user_id}")
            return
        
        if target_user.websocket.closed:
            logger.warning(f"Target user {target_id} WebSocket is closed")
            return
        
        try:
            message = {
                "type": "answer",
                "sdp": answer_data.get("sdp"),
                "from_id": user_id
            }
            
            await target_user.websocket.send_str(json.dumps(message))
            logger.debug(f"Forwarded answer from {user_id} to {target_id}")
            
        except Exception as e:
            logger.error(f"Error forwarding answer from {user_id} to {target_id}: {e}")
    
    async def handle_ice_candidate(self, user_id: str, target_id: str, candidate_data: dict) -> None:
        """Handle an ICE candidate from one user to another."""
        target_user = self.connection_manager.get_user(target_id)
        if not target_user:
            logger.warning(f"Target user {target_id} not found for ICE candidate from {user_id}")
            return
        
        if target_user.websocket.closed:
            logger.warning(f"Target user {target_id} WebSocket is closed")
            return
        
        try:
            message = {
                "type": "ice_candidate",
                "candidate": candidate_data.get("candidate"),
                "from_id": user_id
            }
            
            await target_user.websocket.send_str(json.dumps(message))
            logger.debug(f"Forwarded ICE candidate from {user_id} to {target_id}")
            
        except Exception as e:
            logger.error(f"Error forwarding ICE candidate from {user_id} to {target_id}: {e}")
    
    async def cleanup_peer_connection(self, user_id: str, target_id: str) -> None:
        """Clean up a peer connection between two users."""
        user = self.connection_manager.get_user(user_id)
        
        if user and target_id in user.peer_connections:
            try:
                pc = user.peer_connections[target_id]
                
                # Close the peer connection
                if pc.connectionState not in ["closed", "failed"]:
                    await pc.close()
                
                # Remove from user's peer connections
                del user.peer_connections[target_id]
                
                logger.info(f"Cleaned up peer connection between {user_id} and {target_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up peer connection between {user_id} and {target_id}: {e}")
        
        # Also clean up the reverse connection if it exists
        target_user = self.connection_manager.get_user(target_id)
        if target_user and user_id in target_user.peer_connections:
            try:
                pc = target_user.peer_connections[user_id]
                
                if pc.connectionState not in ["closed", "failed"]:
                    await pc.close()
                
                del target_user.peer_connections[user_id]
                
                logger.info(f"Cleaned up reverse peer connection between {target_id} and {user_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up reverse peer connection between {target_id} and {user_id}: {e}")
    
    async def cleanup_all_user_connections(self, user_id: str) -> None:
        """Clean up all peer connections for a user."""
        user = self.connection_manager.get_user(user_id)
        if not user:
            return
        
        # Get list of target IDs to avoid modifying dict during iteration
        target_ids = list(user.peer_connections.keys())
        
        for target_id in target_ids:
            await self.cleanup_peer_connection(user_id, target_id)
        
        logger.info(f"Cleaned up all peer connections for user {user_id}")
    
    def get_connection_count(self, user_id: str) -> int:
        """Get the number of active peer connections for a user."""
        user = self.connection_manager.get_user(user_id)
        return len(user.peer_connections) if user else 0
    
    def get_total_connections(self) -> int:
        """Get the total number of active peer connections across all users."""
        total = 0
        for user in self.connection_manager.get_all_users().values():
            total += len(user.peer_connections)
        return total // 2  # Divide by 2 because each connection is counted twice
    
    def get_user_connections(self, user_id: str) -> list:
        """Get list of users that a specific user is connected to."""
        user = self.connection_manager.get_user(user_id)
        return list(user.peer_connections.keys()) if user else []
    
    def get_stats(self) -> dict:
        """Get WebRTC connection statistics."""
        all_users = self.connection_manager.get_all_users()
        total_connections = sum(len(user.peer_connections) for user in all_users.values()) // 2
        users_with_connections = sum(1 for user in all_users.values() if user.peer_connections)
        
        return {
            "total_peer_connections": total_connections,
            "users_with_connections": users_with_connections,
            "ice_servers_count": len(self.ice_servers)
        }