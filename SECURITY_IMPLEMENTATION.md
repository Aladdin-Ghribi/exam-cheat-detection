# 🔐 Security Implementation Checklist

## Phase 1: Immediate Actions (Do First!) 🔴

### Step 1: Install Dependencies
```bash
pip install bcrypt pyjwt python-dotenv flask-limiter
```

### Step 2: Backup Current Data
```bash
cp data/users.json data/users.json.backup
cp data/config.json data/config.json.backup
```

### Step 3: Migrate Passwords
```bash
python migrate_passwords.py
```
**Expected Output**: "✅ Migration complete: X passwords hashed"

### Step 4: Setup Environment Variables
```bash
# Copy template
cp .env.example .env

# Generate secrets (run twice for two different keys)
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env and paste the generated keys
```

### Step 5: Update requirements.txt
Add to `requirements.txt`:
```
bcrypt>=4.0.0
pyjwt>=2.8.0
python-dotenv>=1.0.0
flask-limiter>=3.5.0
```

---

## Phase 2: Update Application Code 🟡

### Step 6: Update app.py - Import Security Modules
Add at the top of `src/cheat_detection_web_app_v2/app.py`:

```python
from src.utils.auth_utils import hash_password, verify_password, generate_token, verify_token, token_required, admin_required
from src.utils.validation import validate_username, validate_password, validate_email, ValidationError
from src.utils.security import rate_limit, check_failed_login_attempts, record_failed_login, clear_failed_login_attempts
from src.utils.audit_logger import audit_logger
from src.utils.config import Config

# Apply configuration
app.config.from_object(Config)
Config.validate()
```

### Step 7: Update Login Route
Replace the `/api/login` route in `app.py`:

```python
@app.route('/api/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def api_login():
    """Authenticate user credentials"""
    data = request.get_json()
    
    try:
        username = validate_username(data.get('username', ''))
        password = validate_password(data.get('password', ''))
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    # Check if account is locked
    if check_failed_login_attempts(username):
        audit_logger.log_login_failure(username, 'Account locked')
        return jsonify({
            'success': False, 
            'error': 'Account locked due to too many failed attempts. Try again in 15 minutes.'
        }), 403
    
    if not USERS_FILE.exists():
        return jsonify({'success': False, 'error': 'User database not found'}), 500
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    for user in users:
        if user.get('username') == username:
            # Verify password (supports both hashed and plain-text during migration)
            password_valid = False
            stored_password = user.get('password', '')
            
            if stored_password.startswith('$2b$'):
                # Bcrypt hash
                password_valid = verify_password(password, stored_password)
            else:
                # Plain-text (legacy, should not exist after migration)
                password_valid = (password == stored_password)
            
            if password_valid:
                # Clear failed attempts
                clear_failed_login_attempts(username)
                
                # Generate JWT token
                token = generate_token(user.get('id'), username, user.get('role'))
                
                # Log success
                audit_logger.log_login_success(user.get('id'), username)
                
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': {
                        'id': user.get('id'),
                        'username': user.get('username'),
                        'email': user.get('email'),
                        'role': user.get('role')
                    }
                })
            else:
                # Record failed attempt
                record_failed_login(username)
                audit_logger.log_login_failure(username, 'Invalid password')
                break
    
    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
```

### Step 8: Protect API Routes
Add `@token_required` decorator to protected routes:

```python
@app.route('/api/config', methods=['GET'])
@token_required
def get_config():
    # ... existing code ...

@app.route('/api/config', methods=['POST'])
@token_required
@admin_required
def update_config():
    # ... existing code ...
    audit_logger.log_config_change(request.user['user_id'], config)
    # ... rest of code ...

@app.route('/api/user/create', methods=['POST'])
@token_required
@admin_required
def create_user():
    # ... existing code ...
```

### Step 9: Update User Creation
In `create_user()` function, hash the password:

```python
# Before saving
from src.utils.auth_utils import hash_password

new_user = {
    'id': new_id,
    'username': username,
    'email': email,
    'password': hash_password(password),  # Hash the password!
    'role': role
}
```

### Step 10: Update Frontend (login.html)
Update the login JavaScript to handle JWT tokens:

```javascript
// After successful login
localStorage.setItem('auth_token', response.token);
localStorage.setItem('user', JSON.stringify(response.user));

// Add token to all API requests
fetch('/api/endpoint', {
    headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
        'Content-Type': 'application/json'
    }
})
```

---

## Phase 3: Testing 🧪

### Step 11: Test Password Migration
```bash
# Try logging in with old credentials
# Should work with hashed passwords
```

### Step 12: Test Rate Limiting
```bash
# Try logging in 6 times with wrong password
# Should get "Rate limit exceeded" on 6th attempt
```

### Step 13: Test JWT Authentication
```bash
# Try accessing /api/config without token
# Should get 401 Unauthorized
```

### Step 14: Test Audit Logging
```bash
# Check logs/audit.log
cat logs/audit.log | grep LOGIN_SUCCESS
```

---

## Phase 4: Production Deployment 🚀

### Step 15: Environment Configuration
```bash
# Set production environment
export FLASK_ENV=production
export DEBUG=False
```

### Step 16: Setup HTTPS
```bash
# Install certbot (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com
```

### Step 17: Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/exam-detection
# Paste configuration from SECURITY.md
sudo nginx -t
sudo systemctl reload nginx
```

### Step 18: Setup Systemd Service
```bash
sudo nano /etc/systemd/system/exam-detection.service
```

```ini
[Unit]
Description=Exam Cheat Detection System
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/exam-cheat-detection
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python start_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable exam-detection
sudo systemctl start exam-detection
```

---

## Phase 5: Monitoring & Maintenance 📊

### Step 19: Setup Log Rotation
```bash
sudo nano /etc/logrotate.d/exam-detection
```

```
/path/to/exam-cheat-detection/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

### Step 20: Regular Security Checks
```bash
# Weekly: Review audit logs
grep "FAILURE\|ERROR" logs/audit.log

# Monthly: Update dependencies
pip list --outdated
pip install --upgrade package-name

# Quarterly: Review user accounts
python -c "import json; print(json.load(open('data/users.json')))"
```

---

## ✅ Completion Checklist

- [ ] Dependencies installed
- [ ] Passwords migrated to bcrypt
- [ ] .env file configured with unique secrets
- [ ] app.py updated with security modules
- [ ] Login route updated with JWT
- [ ] API routes protected with decorators
- [ ] Frontend updated to use JWT tokens
- [ ] Rate limiting tested
- [ ] Audit logging verified
- [ ] HTTPS configured
- [ ] Nginx reverse proxy setup
- [ ] Systemd service created
- [ ] Log rotation configured
- [ ] Security documentation reviewed
- [ ] Backup strategy implemented

---

## 🆘 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Invalid token" errors
```bash
# Check if JWT_SECRET_KEY is set in .env
# Verify token is being sent in Authorization header
```

### "Rate limit exceeded" during testing
```bash
# Wait 60 seconds or restart the application
```

### Migration script fails
```bash
# Check if users.json exists
# Verify file permissions
# Run with: python -u migrate_passwords.py
```

---

**Need Help?** Check SECURITY.md for detailed documentation.
