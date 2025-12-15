import json
import bcrypt
from pathlib import Path

# Hash passwords in users.json
users_file = Path('data/users.json')

with open(users_file, 'r') as f:
    users = json.load(f)

for user in users:
    if 'password' in user and not user['password'].startswith('$2b$'):
        plain_password = user['password']
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        user['password'] = hashed.decode('utf-8')
        print(f"Hashed password for user: {user['username']}")

with open(users_file, 'w') as f:
    json.dump(users, f, indent=2)

print("All passwords hashed successfully!")
