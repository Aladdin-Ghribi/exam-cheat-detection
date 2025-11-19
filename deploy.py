#!/usr/bin/env python3
"""
Deployment script for Exam Monitoring System
Builds React frontend and integrates with Flask backend
"""

import os
import subprocess
import shutil
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run shell command and handle errors"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {cmd}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {cmd}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def main():
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"
    backend_dir = project_root / "src" / "cheat_detection_web_app"
    
    print("🚀 Starting deployment process...")
    
    # Build React frontend
    print("\n📦 Building React frontend...")
    os.chdir(frontend_dir)
    run_command("npm install")
    run_command("npm run build")
    
    # Copy build to Flask static/templates
    print("\n📁 Copying build files to Flask...")
    build_dir = frontend_dir / "build"
    
    # Copy static files
    static_src = build_dir / "static"
    static_dest = backend_dir / "static"
    if static_dest.exists():
        shutil.rmtree(static_dest)
    shutil.copytree(static_src, static_dest)
    
    # Update spa.html with correct asset paths
    index_file = build_dir / "index.html"
    spa_file = backend_dir / "templates" / "spa.html"
    
    with open(index_file, 'r') as f:
        content = f.read()
    
    # Update asset paths for Flask
    content = content.replace('/static/', '/static/')
    content = content.replace('href="/favicon.ico"', 'href="{{ url_for("static", filename="favicon.ico") }}"')
    
    with open(spa_file, 'w') as f:
        f.write(content)
    
    print("\n✅ Deployment preparation complete!")
    print("\nTo run the application:")
    print("1. cd src/cheat_detection_web_app")
    print("2. python app.py")
    print("3. Open http://localhost:5000")

if __name__ == "__main__":
    main()