# Security Implementation Guide

## Overview
This document outlines the comprehensive security features implemented in the Exam Cheat Detection system.

## Installation Steps

### 1. Install Security Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Hash Existing Passwords
```powershell
python hash_passwords.py
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and update values:
```powershell
copy .env.example .env
```

Edit `.env` and change:
- `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `JWT_SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `ALLOWED_ORIGINS` - Set to your domain (e.g., `https://yourdomain.com`)

### 4. Run Secure Application
```powershell
python src/cheat_detection_web_app_v2/app_secure.py
```

## Security Features Implemented

### ✅ Authentication & Authorization
- **JWT Token-based authentication** - Secure, stateless authentication
- **Bcrypt password hashing** - Industry-standard password protection
- **Token expiration** - Auto-logout after inactivity (default: 2 hours)
- **Server-side session validation** - Prevents unauthorized access

### ✅ Rate Limiting
- **Login attempts** - 5 per minute (configurable)
- **API calls** - 100 per minute, 200 per day (configurable)
- **Prevents brute force attacks**

### ✅ Security Headers
- **X-Content-Type-Options: nosniff** - Prevents MIME sniffing
- **X-Frame-Options: DENY** - Prevents clickjacking
- **X-XSS-Protection** - Enables XSS filter
- **Strict-Transport-Security** - Forces HTTPS
- **Content-Security-Policy** - Restricts resource loading
- **Cache-Control** - Prevents caching of sensitive pages

### ✅ Input Validation & Sanitization
- **XSS Protection** - Removes dangerous characters
- **SQL Injection Prevention** - Parameterized queries (when using DB)
- **Path Traversal Protection** - Validates file paths
- **Length limits** - Prevents buffer overflow attacks

### ✅ CORS Protection
- **Restricted origins** - Only allowed domains can connect
- **Configurable via environment variables**

### ✅ File Upload Security
- **Size limits** - Max 5MB per file (configurable)
- **Type validation** - Only images allowed
- **Secure file storage** - Sanitized paths

### ✅ Audit Logging
- **Login attempts** - Success and failures logged
- **User actions** - All security-relevant events tracked
- **IP address tracking** - For forensic analysis
- **Timestamp logging** - Complete audit trail

### ✅ Session Management
- **Secure cookies** - HttpOnly, Secure, SameSite flags
- **Session timeout** - Auto-expire after inactivity
- **Token invalidation** - Logout clears all sessions

### ✅ Environment Configuration
- **Secrets in .env** - Not in source code
- **.gitignore protection** - Prevents committing secrets
- **Debug mode control** - Disabled in production

### ✅ Error Handling
- **Generic error messages** - Don't reveal system details
- **Proper logging** - Errors logged for debugging
- **Graceful degradation** - System remains stable

## Security Checklist

### Completed ✅
- [x] Passwords hashed with bcrypt
- [x] JWT token authentication
- [x] Rate limiting on login
- [x] Input validation and sanitization
- [x] Security headers (CSP, X-Frame-Options, etc.)
- [x] CORS restricted to specific origins
- [x] Server-side session management
- [x] Audit logging enabled
- [x] Debug mode configurable
- [x] Secret keys in environment variables
- [x] XSS protection
- [x] File upload size limits
- [x] Cache-control headers
- [x] Token expiration

### Pending (Production Requirements) ⚠️
- [ ] HTTPS enabled (requires SSL certificate)
- [ ] CSRF protection (add flask-wtf)
- [ ] Evidence encryption at rest
- [ ] Database migration (from JSON to PostgreSQL)
- [ ] Regular dependency updates (setup dependabot)
- [ ] Penetration testing
- [ ] GDPR compliance review

## Frontend Updates Required

### Update login.html
Replace the login function to use JWT tokens:

```javascript
async function handleLogin() {
    const username = document.getElementById('usernameInput').value.trim();
    const password = document.getElementById('passwordInput').value.trim();
    const errorMessage = document.getElementById('errorMessage');
    
    if (!username || !password) {
        errorMessage.textContent = 'Please enter both username and password';
        errorMessage.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Store JWT token
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = '/dashboard';
        } else {
            errorMessage.textContent = data.error || 'Login failed';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Connection error. Please try again.';
        errorMessage.style.display = 'block';
    }
}
```

### Update dashboard.html
Add authentication check at the top:

```javascript
// Check authentication on page load
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    try {
        const response = await fetch('/api/verify-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        });
        
        if (!response.ok) {
            localStorage.clear();
            window.location.href = '/';
        }
    } catch (error) {
        localStorage.clear();
        window.location.href = '/';
    }
}

// Run on page load
checkAuth();

// Add token to all API requests
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}
```

### Update profile.js logout
```javascript
yesBtn.addEventListener('click', () => {
    confirmModal.remove();
    localStorage.clear();  // Clear token
    window.location.replace('/logout');
});
```

## Testing

### Test Login
```powershell
# Test with correct credentials
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

# Test with wrong credentials
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"wrong\"}"
```

### Test Rate Limiting
```powershell
# Try 6 login attempts rapidly (should block 6th)
for i in {1..6}; do
  curl -X POST http://localhost:5000/api/login \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"admin\",\"password\":\"wrong\"}"
done
```

### Test Token Verification
```powershell
# Get token from login, then verify
curl -X POST http://localhost:5000/api/verify-token \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"YOUR_TOKEN_HERE\"}"
```

## Production Deployment

### 1. Enable HTTPS
```python
# Use gunicorn with SSL
gunicorn --certfile=cert.pem --keyfile=key.pem -w 4 -b 0.0.0.0:443 app_secure:app
```

### 2. Use Production WSGI Server
```powershell
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app_secure:app
```

### 3. Set Production Environment
```
FLASK_ENV=production
DEBUG_MODE=False
ALLOWED_ORIGINS=https://yourdomain.com
```

### 4. Use Reverse Proxy (Nginx)
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring & Maintenance

### Check Logs
```powershell
# View audit logs
type logs\app.log | findstr AUDIT

# View error logs
type logs\app.log | findstr ERROR
```

### Update Dependencies
```powershell
pip list --outdated
pip install --upgrade package-name
```

### Rotate Secrets
Periodically update SECRET_KEY and JWT_SECRET_KEY in `.env`

## Support

For security issues, contact: security@yourcompany.com

## License

Proprietary - All Rights Reserved
