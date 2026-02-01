import os
import shutil
import random
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from email.utils import parsedate_to_datetime


class SecureEraser:

    @staticmethod
    def get_trusted_time():
        """
        Get the current UTC time from a trusted high-availability public server (Google).
        Falls back to system time if internet is unavailable.

        Returns:
            datetime: Current UTC datetime
        """
        try:
            # HEAD request to google.com - very fast and reliable
            req = urllib.request.Request(
                "http://www.google.com", method="HEAD")
            req.add_header(
                'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

            with urllib.request.urlopen(req, timeout=3) as response:
                date_str = response.headers['Date']
                if date_str:
                    # Parse 'Fri, 30 Dec 2025 10:00:00 GMT'
                    network_time = parsedate_to_datetime(date_str)
                    # Normalize to naive UTC for consistent comparisons
                    return network_time.replace(tzinfo=None)
        except Exception as e:
            print(
                f"Time Check Warning: Could not reach trusted time server: {e}")
            print("Falling back to local system time.")

        return datetime.utcnow()

    @staticmethod
    def secure_delete_file(file_path, passes=1):
        """
        Securely delete a file by overwriting it with random data.

        Args:
            file_path (str|Path): Path to the file to delete
            passes (int): Number of overwrite passes (default: 1)
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return

        try:
            file_size = path.stat().st_size

            with open(path, "wb") as f:
                for _ in range(passes):
                    # Pass 1: Random data (simulating "shred")
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            # Remove the file after overwriting
            os.remove(path)
            # print(f"Securely deleted file: {path.name}")

        except Exception as e:
            print(f"Error securely deleting {path}: {e}")
            # Fallback to standard delete
            try:
                if path.exists():
                    os.remove(path)
            except:
                pass

    @staticmethod
    def secure_delete_tree(directory_path):
        """
        Recursively securely delete a directory and all its contents.

        Args:
            directory_path (str|Path): Path to the directory to delete
        """
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            return

        # Walk bottom-up to delete files first
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = Path(root) / name
                SecureEraser.secure_delete_file(file_path)

            for name in dirs:
                dir_path = Path(root) / name
                try:
                    dir_path.rmdir()  # Remove empty directory
                except OSError:
                    # Fallback to rmtree
                    shutil.rmtree(dir_path, ignore_errors=True)

        try:
            path.rmdir()
            print(f"Securely deleted directory: {path.name}")
        except OSError:
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def is_expired(folder_name, retention_days):
        """
        Check if a session folder is expired based on its timestamp.
        Uses Trusted Network Time to prevent system clock tampering.

        Args:
            folder_name (str): Name of the folder (e.g., 'sess_20251230_103000')
            retention_days (int): Number of days to retain data

        Returns:
            bool: True if expired, False otherwise
        """
        try:
            # Expected format examples:
            # sess_20251230_103000
            # sess_20251230_103000_123 (sometimes has suffixes)
            # 20251230_103000_123_score (evidence folders)

            parts = folder_name.split('_')

            # Try to find the date part (YYYYMMDD)
            date_str = None
            for part in parts:
                if len(part) == 8 and part.isdigit() and part.startswith('20'):
                    date_str = part
                    break

            if not date_str:
                return False

            # Parse date
            date_obj = datetime.strptime(date_str, "%Y%m%d")

            # Get TRUE current time (Network Time)
            current_time = SecureEraser.get_trusted_time()

            # Check age
            age = current_time - date_obj
            return age.days >= retention_days

        except Exception as e:
            # If we can't parse it, safe to assume not expired or skip it
            return False
