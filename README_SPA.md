# SPA Framework Setup - React Integration

## Framework Selection: React

**Why React?**
- Perfect for real-time applications with WebSocket integration
- Component-based architecture ideal for modular UI (video player, seat map, alerts)
- Excellent state management for shared detection data
- Large ecosystem and team familiarity

## Development Environment Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Servers

**Terminal 1 - Flask Backend:**
```bash
python start_app.py
# Runs on http://localhost:5000
```

**Terminal 2 - React Frontend:**
```bash
cd frontend
npm start
# Runs on http://localhost:3000
```

### 3. Access Application
- **Development**: http://localhost:3000 (React dev server)
- **Production**: http://localhost:5000 (Flask serves built React)

## Architecture

```
┌─────────────────┐    WebSocket    ┌──────────────────┐
│   React SPA     │ ←──────────────→ │   Flask Backend  │
│  (Port 3000)    │                 │   (Port 5000)    │
│                 │    HTTP API     │                  │
│ - Dashboard     │ ←──────────────→ │ - Detection API  │
│ - InstructorView│                 │ - File Upload    │
│ - Settings      │                 │ - WebSocket      │
└─────────────────┘                 └──────────────────┘
```

## Key Benefits Achieved

### ✅ **No More Page Resets**
- Single page application - no navigation reloads
- Persistent WebSocket connection
- Shared state across all views

### ✅ **Real-Time State Management**
- All components share same detection data
- Instructor view updates live while dashboard runs
- Settings changes apply immediately

### ✅ **Better Performance**
- Virtual DOM handles frequent video frame updates
- Component-based rendering only updates changed parts
- Optimized WebSocket handling

### ✅ **Improved UX**
- Instant view switching
- No loading delays
- Smooth transitions

## Component Structure

```
src/
├── App.js                 # Main app with view routing
├── components/
│   ├── Header.js         # Navigation and settings
│   ├── Dashboard.js      # Video processing and metrics
│   ├── InstructorView.js # Seat map, alerts, event log
│   └── SettingsModal.js  # All configuration controls
└── App.css               # Shared styles
```

## Integration Points

### WebSocket Connection
- Single persistent connection in App.js
- Shared across all components
- Automatic reconnection handling

### State Management
- React useState for global detection data
- Real-time updates via WebSocket events
- No external state library needed (simple enough)

### API Integration
- Proxy configuration routes API calls to Flask
- File upload and processing endpoints
- Health check and current data endpoints

## Development Workflow

1. **Backend Changes**: Modify Flask app, restart `python start_app.py`
2. **Frontend Changes**: Edit React components, hot reload automatic
3. **Testing**: Both servers run simultaneously
4. **Production**: `npm run build` creates static files for Flask to serve

## Next Steps

1. Run `cd frontend && npm install`
2. Start both servers as described above
3. Access http://localhost:3000 for development
4. All existing functionality preserved in new SPA architecture

The SPA framework eliminates all navigation issues while providing a much better user experience for real-time exam monitoring.