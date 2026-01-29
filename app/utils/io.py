import json
import os
import time
import tempfile

def robust_load_json(file_path, default=None):
    """Load JSON file with fallback to latin-1 on encoding errors."""
    if not os.path.exists(file_path):
        return default if default is not None else {}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content.strip() else (default if default is not None else {})
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
                data = json.loads(content) if content.strip() else (default if default is not None else {})
                # Auto-repair to UTF-8
                save_json_atomic(file_path, data)
                return data
        except:
            return default if default is not None else {}

def save_json_atomic(file_path, data):
    """Saves JSON data atomically by writing to a temporary file and then moving it."""
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Windows-specific: os.replace can fail if the destination file is open
        # But here it is the best option for pseudo-atomicity
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

class FileLock:
    """Simple file-based lock mechanism."""
    def __init__(self, file_path, timeout=5):
        self.lock_file = file_path + ".lock"
        self.timeout = timeout
        self.locked = False

    def __enter__(self):
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                # Try to create the lock file with O_EXCL (atomic)
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f:
                    f.write(str(os.getpid()))
                self.locked = True
                return self
            except FileExistsError:
                # Check if the lock is orphaned (older than 10 seconds)
                try:
                    mtime = os.path.getmtime(self.lock_file)
                    if time.time() - mtime > 10:
                        os.remove(self.lock_file)
                except:
                    pass
                time.sleep(0.1)
        raise TimeoutError(f"Could not obtain lock for {self.lock_file}.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locked:
            try:
                os.remove(self.lock_file)
            except:
                pass
            self.locked = False

def locked_update_json(file_path, update_func, default=None):
    """Reads, updates and saves JSON data using a file locking mechanism."""
    with FileLock(file_path):
        data = robust_load_json(file_path, default=default)
        new_data = update_func(data)
        save_json_atomic(file_path, new_data)
        return new_data
