"""
Main entry point for the Video Chat Room application.
"""

import asyncio
import logging
import os
from aiohttp import web
import aiohttp_cors

from src.video_app import VideoChatApplication
from src.config import HOST, PORT, LOG_LEVEL, CORS_ORIGINS

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def index_handler(request):
    """Serve the main HTML page."""
    try:
        # Read the HTML template
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        
        if not os.path.exists(template_path):
            # Fallback to inline HTML if template file doesn't exist
            logger.warning(f"Template file not found at {template_path}, using fallback")
            return web.Response(text="Template file not found", status=404)
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return web.Response(text=html_content, content_type='text/html')
        
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return web.Response(text="Internal server error", status=500)


async def health_handler(request):
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "service": "video-chat-room"
    })


async def create_app():
    """Create and configure the aiohttp application."""
    # Initialize the main application
    app_instance = VideoChatApplication()
    
    # Create aiohttp app
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        origin: aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
        for origin in CORS_ORIGINS
    })
    
    # Routes
    app.router.add_get('/', index_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_get('/ws', app_instance.websocket_handler)
    app.router.add_post('/upload', app_instance.upload_file)
    app.router.add_get('/sessions/{session_id}/files', app_instance.get_session_files)
    app.router.add_get('/stats', app_instance.get_stats)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Store app instance for cleanup
    app['chat_app'] = app_instance
    
    logger.info("Application created and configured")
    return app


async def cleanup_handler(app):
    """Cleanup handler for graceful shutdown."""
    logger.info("Starting application cleanup...")
    
    try:
        chat_app = app.get('chat_app')
        if chat_app:
            # Clean up all active connections
            all_users = chat_app.connection_manager.get_all_users()
            for user_id in list(all_users.keys()):
                await chat_app.cleanup_user(user_id)
            
            # Clean up any remaining resources
            await chat_app.webrtc_manager.cleanup_all_user_connections('')
            
            logger.info("Application cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


async def init_app():
    """Initialize the application with cleanup handlers."""
    app = await create_app()
    
    # Add cleanup handler
    app.on_cleanup.append(cleanup_handler)
    
    return app


def main():
    """Main entry point."""
    logger.info(f"Starting Video Chat Room server on {HOST}:{PORT}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"CORS origins: {CORS_ORIGINS}")
    
    try:
        web.run_app(init_app(), host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server stopped")


if __name__ == '__main__':
    main()