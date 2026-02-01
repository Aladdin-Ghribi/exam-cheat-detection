"""
Migration script to hash existing plain-text passwords in users.json
Run this ONCE before deploying the secure version
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.auth_utils import hash_password


def migrate_passwords():
    """Migrate plain-text passwords to bcrypt hashes"""
    users_file = Path(__file__).parent / 'data' / 'users.json'
    
    if not users_file.exists():
        print("❌ users.json not found")
        return False
    
    # Backup original file
    backup_file = users_file.with_suffix('.json.backup')
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    with open(backup_file, 'w') as f:
        json.dump(users, f, indent=2)
    print(f"✅ Backup created: {backup_file}")
    
    # Hash passwords
    migrated = 0
    for user in users:
        password = user.get('password', '')
        
        # Check if already hashed (bcrypt hashes start with $2b$)
        if password.startswith('$2b$'):
            print(f"⏭️  Skipping {user['username']} (already hashed)")
            continue
        
        # Hash the password
        user['password'] = hash_password(password)
        migrated += 1
        print(f"🔒 Hashed password for: {user['username']}")
    
    # Save updated users
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"\n✅ Migration complete: {migrated} passwords hashed")
    print(f"📁 Original backed up to: {backup_file}")
    return True


if __name__ == '__main__':
    print("🔐 Password Migration Tool")
    print("=" * 50)
    
    response = input("This will hash all plain-text passwords. Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate_passwords()
    else:
        print("❌ Migration cancelled")
