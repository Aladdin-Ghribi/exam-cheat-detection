# Deployment Guide

## Quick Deployment

### Option 1: Automated Script
```bash
python deploy.py
cd src/cheat_detection_web_app
python app.py
```

### Option 2: Manual Build
```bash
# Build React frontend
cd frontend
npm install
npm run build

# Run Flask backend
cd ../src/cheat_detection_web_app
python app.py
```

## Production Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Nginx + Flask
1. Build React: `npm run build`
2. Copy build files to web server
3. Configure Nginx with provided config
4. Run Flask backend as service

## Environment Configuration

### Development
- API URL: http://localhost:5000
- Socket URL: http://localhost:5000

### Production
- Set REACT_APP_API_URL in .env.production
- Set REACT_APP_SOCKET_URL in .env.production
- Configure CORS in Flask app

## Server Requirements

### Minimum Specs
- CPU: 4 cores
- RAM: 8GB
- Storage: 10GB
- Network: 100Mbps

### Recommended Specs
- CPU: 8 cores
- RAM: 16GB
- Storage: 50GB SSD
- Network: 1Gbps

## Troubleshooting

### SPA Routing Issues
- Ensure server redirects all routes to index.html
- Check .htaccess or Nginx config
- Verify React Router basename

### API Connection Issues
- Check CORS configuration
- Verify environment variables
- Test API endpoints directly

### WebSocket Issues
- Check Socket.IO version compatibility
- Verify proxy configuration
- Test WebSocket connection