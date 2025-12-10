#!/usr/bin/env python3
"""
Startup script for the Exam Cheat Detection Web Application.
This script ensures proper path setup and starts the Flask-SocketIO server.
"""

import sys
import os

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)


def main():
    """Start the web application."""
    print("🚀 Starting Exam Cheat Detection Web Application")
    print("=" * 50)

    # Check if required directories exist
    required_dirs = [
        'src/cheat_detection_web_app_v2',
        'src/detection',
        'data/samples',
        'output'
    ]

    for dir_path in required_dirs:
        full_path = os.path.join(current_dir, dir_path)
        if not os.path.exists(full_path):
            print(f"❌ Required directory missing: {dir_path}")
            return False
        else:
            print(f"✅ Directory found: {dir_path}")

    # Check if YOLO model exists
    model_files = ['yolo11m.pt', 'yolo11n.pt', 'yolo11s.pt']
    model_found = False
    for model_file in model_files:
        if os.path.exists(os.path.join(current_dir, model_file)):
            print(f"✅ YOLO model found: {model_file}")
            model_found = True
            break

    if not model_found:
        print("❌ No YOLO model files found. Please ensure at least one model file exists.")
        return False

    print("\n" + "=" * 50)
    print("🌐 Starting web server...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        # Import and run the Flask app (v2)
        from src.cheat_detection_web_app_v2.app import app, socketio
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
