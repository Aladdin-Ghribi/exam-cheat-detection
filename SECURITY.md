# 🔒 Security Implementation Guide

## Overview
This document outlines the security measures implemented in the Exam Cheat Detection System.

---

## 🚀 Quick Start - Security Setup

### 1. Install Additional Dependencies
```bash
pip install bcrypt pyjwt python-dotenv
```

### 2. Migrate Existing Passwords
```bash
python migrate_passwords.py
```
This will hash all plain-text passwords in `users.json`.

### 3. Setup Environment Variables
```bash
# Copy template
cp .env.example .env

# Generate secure keys (Linux/Mac)
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env and replace placeholder values
```

### 4. Verify Security Configuration
```bash
python -c "from src.utils.config import Config; Config.validate()"
```

---

## 🔐 Security Features Implemented

### 1. Authentication & Authorization
- ✅ **Bcrypt Password Hashing** (12 rounds)
- ✅ **JWT Token-Based Authentication** (24-hour expiration)
- ✅ **Role-Based Access Control** (Administrator/Proctor)
- ✅ **Session Management** with secure cookies

### 2. Input Validation
- ✅ **Username Validation** (alphanumeric, 3-50 chars)
- ✅ **Password Strength** (min 8 chars, letters + numbers)
- ✅ **Email Validation** (RFC-compliant regex)
- ✅ **Student ID Sanitization**
- ✅ **Filename Sanitization** (prevent path traversal)

### 3. Rate Limiting & Brute Force Protection
- ✅ **Login Rate Limiting** (5 attempts per 15 minutes)
- ✅ **API Rate Limiting** (configurable per endpoint)
- ✅ **Account Lockout** after failed attempts
- ✅ **IP-Based Throttling**

### 4. CSRF Protection
- ✅ **CSRF Token Generation** per session
- ✅ **Token Validation** on state-changing requests
- ✅ **SameSite Cookie** attribute

### 5. Secure Configuration
- ✅ **Environment Variables** for secrets
- ✅ **Secret Key Rotation** support
- ✅ **Configuration Validation** on startup
- ✅ **Sensitive Data Exclusion** from logs

### 6. Audit Logging
- ✅ **Login/Logout Events**
- ✅ **User Management Actions**
- ✅ **Configuration Changes**
- ✅ **Alert Confirmations**
- ✅ **Evidence Deletion Tracking**

---

## 🛡️ Security Best Practices

### For Deployment

1. **HTTPS Only**
   - Use SSL/TLS certificates (Let's Encrypt recommended)
   - Set `SESSION_COOKIE_SECURE=True` in production

2. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   ufw allow 443/tcp  # HTTPS
   ufw allow 22/tcp   # SSH (restrict to specific IPs)
   ufw enable
   ```

3. **Reverse Proxy (Nginx)**
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       # Security headers
       add_header X-Frame-Options "SAMEORIGIN" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-XSS-Protection "1; mode=block" always;
       add_header Strict-Transport-Security "max-age=31536000" always;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **Database Security** (when migrating from JSON)
   - Use parameterized queries (prevent SQL injection)
   - Encrypt sensitive columns
   - Regular backups with encryption

5. **File Upload Security**
   - Validate file types (magic bytes, not just extension)
   - Scan uploads with antivirus
   - Store outside web root
   - Generate random filenames

---

## 🔍 Security Checklist

### Before Production Deployment

- [ ] All passwords hashed with bcrypt
- [ ] `.env` file created with unique secrets
- [ ] `.env` added to `.gitignore`
- [ ] HTTPS enabled with valid certificate
- [ ] Debug mode disabled (`DEBUG=False`)
- [ ] Rate limiting enabled
- [ ] Audit logging configured
- [ ] Firewall rules configured
- [ ] Regular backup strategy in place
- [ ] Security headers configured (via Nginx/Apache)
- [ ] CORS properly configured (if needed)
- [ ] File upload limits enforced
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies updated (run `pip list --outdated`)

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Rotate JWT secret keys quarterly
- [ ] Update dependencies monthly
- [ ] Review user accounts quarterly
- [ ] Test backup restoration quarterly
- [ ] Security audit annually

---

## 🚨 Incident Response

### If Credentials Compromised

1. **Immediate Actions**
   ```bash
   # Rotate all secrets
   python -c "import secrets; print('NEW_SECRET:', secrets.token_hex(32))"
   
   # Update .env with new secrets
   # Restart application
   
   # Force all users to re-login
   # (JWT tokens will expire automatically)
   ```

2. **Reset Affected User Passwords**
   ```python
   from src.utils.auth_utils import hash_password
   # Update user password in users.json
   ```

3. **Review Audit Logs**
   ```bash
   grep "LOGIN_FAILURE" logs/audit.log
   grep "UNAUTHORIZED" logs/app.log
   ```

### If Breach Detected

1. Take system offline immediately
2. Preserve logs for forensic analysis
3. Notify affected users
4. Conduct security audit
5. Implement additional controls
6. Document incident and response

---

## 📞 Security Contacts

- **Security Issues**: Report to your security team
- **Vulnerability Disclosure**: Follow responsible disclosure
- **Emergency**: Have incident response plan ready

---

## 🔗 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated**: 2025-01-14
**Version**: 1.0
