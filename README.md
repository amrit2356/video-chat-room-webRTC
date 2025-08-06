# Video Chat Room - WebRTC Application

A professional video chat room application built with Python, WebRTC, and modern web technologies following SOLID design principles.

## ✨ Features

- **🎥 Real-time video chat** - Up to 5 users per room
- **🎤 Audio/Video controls** - Toggle video and audio on/off
- **📹 Recording capabilities** - Record sessions with automatic file management
- **📁 File upload system** - Upload audio/video files to session folders
- **🔧 Session management** - Unique session IDs and organized file storage
- **📊 Statistics dashboard** - Real-time application statistics
- **🎨 Modern UI** - Responsive design with drag-and-drop file upload
- **🏗️ Clean architecture** - SOLID principles, dependency injection, separation of concerns

## 🏗️ Architecture

The application follows SOLID design principles with clear separation of concerns:

```
├── main.py                 # Entry point and web server setup
├── config.py              # Configuration settings
├── models.py              # Data models and dataclasses
├── interfaces.py          # Abstract interfaces (DIP)
├── application.py         # Main application controller
├── managers/              # Business logic implementations
│   ├── connection_manager.py    # WebSocket connection management
│   ├── room_manager.py         # Room and user management
│   ├── session_manager.py      # Session folder management
│   ├── storage_manager.py      # File storage operations
│   ├── webrtc_manager.py       # WebRTC peer connections
│   └── recording_manager.py    # Recording session management
├── templates/
│   └── index.html         # Frontend interface
└── sessions/              # Session data storage (auto-created)
```

## 🚀 Quick Start

You can run this application either locally with Python or using Docker. Choose the method that works best for your environment.

### Option 1: Local Development

#### 1. Installation

```bash
# Clone or create the project directory
mkdir video_chat_room
cd video_chat_room

# Create all the Python files (copy from the artifacts above)

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configuration

The application uses environment variables for configuration. Default values are provided in `config.py`:

```bash
# Optional: Set environment variables
export HOST=localhost
export PORT=8080
export MAX_USERS_PER_ROOM=5
export LOG_LEVEL=INFO
```

#### 3. Run the Application

```bash
python main.py
```

#### 4. Access the Application

Open your browser and navigate to: `http://localhost:8080`

### Option 2: Docker Deployment

#### 🐳 Using Docker Compose (Recommended)

The easiest way to run the application is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd video-chat-room-webRTC

# Build and start the application
docker-compose -f .docker/docker-compose.yml up -d

# View logs (optional)
docker-compose -f .docker/docker-compose.yml logs -f

# Stop the application
docker-compose -f .docker/docker-compose.yml down
```

#### 🐳 Using Docker directly

If you prefer to use Docker without Compose:

```bash
# Build the Docker image
docker build -f .docker/Dockerfile -t video-chat-room .

# Run the container
docker run -d \
  --name video-chat-room \
  -p 8080:8080 \
  -v video_sessions:/app/sessions \
  -v video_recordings:/app/recordings \
  -e HOST=0.0.0.0 \
  -e PORT=8080 \
  -e MAX_USERS_PER_ROOM=5 \
  video-chat-room

# View logs
docker logs -f video-chat-room

# Stop the container
docker stop video-chat-room
docker rm video-chat-room
```

#### 🔧 Docker Configuration

The Docker setup includes:

- **Persistent storage**: Session data and recordings are stored in Docker volumes
- **Health checks**: Automatic container health monitoring
- **Non-root user**: Enhanced security with dedicated app user
- **System dependencies**: All required libraries for WebRTC and media processing
- **Environment variables**: Full configuration support

**Default Docker Environment Variables:**
```bash
HOST=0.0.0.0
PORT=8080
MAX_USERS_PER_ROOM=5
LOG_LEVEL=INFO
SESSIONS_BASE_PATH=sessions
MAX_FILE_SIZE=104857600
CORS_ORIGINS=*
```

**Volumes:**
- `video_sessions:/app/sessions` - Persistent session data
- `video_recordings:/app/recordings` - Persistent recording files

#### 🛠️ Development with Docker

For development, you can mount your source code into the container:

```bash
# Uncomment the volume mounts in docker-compose.yml:
# - ../src:/app/src
# - ../templates:/app/templates
# - ../main.py:/app/main.py

# Then run with compose
docker-compose -f .docker/docker-compose.yml up -d
```

#### 🏥 Health Monitoring

The application includes health checks accessible at:
- Local: `http://localhost:8080/health`
- Docker: Automatic container health monitoring every 30 seconds

## 🎯 Usage

### Basic Video Chat
1. Enter a room ID (or use the default)
2. Click "Join Room" and allow camera/microphone access
3. Share the room ID with others to join the same room
4. Use the media controls to toggle video/audio

### Recording
1. Join a room
2. Click "Start Recording" to begin session recording
3. Upload additional files using the file upload area
4. All files are organized by unique session ID

### File Management
- Drag and drop files to the upload area
- Files are automatically organized in session folders
- View session files via the `/sessions/{session_id}/files` endpoint

## 📊 API Endpoints

- `GET /` - Main application interface
- `GET /ws` - WebSocket endpoint for real-time communication
- `POST /upload?session_id=<id>` - Upload files to a session
- `GET /sessions/{session_id}/files` - List files in a session
- `GET /stats` - Application statistics
- `GET /health` - Health check endpoint

## 🔧 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `localhost` | Server host |
| `PORT` | `8080` | Server port |
| `MAX_USERS_PER_ROOM` | `5` | Maximum users per room |
| `SESSIONS_BASE_PATH` | `sessions` | Base path for session storage |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_FILE_SIZE` | `100MB` | Maximum file upload size |

## 🏗️ SOLID Principles Implementation

### Single Responsibility Principle (SRP)
- Each manager class has one clear purpose
- `ConnectionManager` only handles WebSocket connections
- `RoomManager` only manages rooms and membership
- `StorageManager` only handles file operations

### Open/Closed Principle (OCP)
- Interfaces allow for easy extension without modification
- New features can be added by implementing existing interfaces

### Liskov Substitution Principle (LSP)
- All implementations can be substituted for their interfaces
- Dependency injection allows for easy testing and swapping

### Interface Segregation Principle (ISP)
- Small, focused interfaces avoid forcing unnecessary dependencies
- Each interface serves a specific purpose

### Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions, not concretions
- All managers depend on interfaces, not concrete implementations

## 🧪 Testing

The modular architecture makes testing straightforward:

```python
# Example: Testing the RoomManager
from managers.room_manager import RoomManager
from tests.mocks import MockConnectionManager

def test_join_room():
    mock_conn_mgr = MockConnectionManager()
    room_mgr = RoomManager(mock_conn_mgr)
    
    # Test room joining logic
    assert room_mgr.join_room("user1", "room1") == True
```

## 🔒 Security Considerations

- CORS configuration for cross-origin requests
- File upload size limits
- Input validation on all endpoints
- WebSocket connection cleanup
- Session isolation

## 📈 Performance Features

- Automatic resource cleanup
- Efficient peer-to-peer connections
- Session-based file organization
- Connection state monitoring
- Graceful error handling

## 🤝 Contributing

1. Follow the existing architecture patterns
2. Implement new features by creating interfaces first
3. Add proper error handling and logging
4. Update tests for new functionality
5. Document any new configuration options

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

Built with:
- [aiohttp](https://github.com/aio-libs/aiohttp) - Async HTTP client/server
- [aiortc](https://github.com/aiortc/aiortc) - WebRTC implementation for Python
- Modern web standards (WebRTC, WebSockets, ES6+)