import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from ai_scanner import is_unwanted_image

# Base configuration for your SQLite DB and Quarantine Staging
BASE_DIR = Path.home() / "SmartCleanup_Project"
QUARANTINE_DIR = BASE_DIR / "Quarantine_Staging"
DB_PATH = BASE_DIR / "quarantine.db"
EXPIRATION_HOURS = 0.01389

# 1. Define strict exclusions to prevent OS corruption
EXCLUDED_DIRECTORIES = {
    "C:\\Windows", 
    "C:\\Program Files", 
    "C:\\Program Files (x86)", 
    "C:\\ProgramData",
    "/bin", "/sbin", "/etc", "/usr", "/var", "/boot" # Linux guardrails
}

# 2. Define safe file types to test (do not test on .exe, .dll, or .sys)
TARGET_EXTENSIONS = {'.txt', '.tmp', '.log'}

def setup_environment():
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quarantine_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT NOT NULL,
            quarantine_path TEXT NOT NULL,
            quarantine_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiration_time TIMESTAMP NOT NULL,
            status TEXT CHECK(status IN ('pending', 'restored', 'deleted')) DEFAULT 'pending'   
        )
    ''')
    conn.commit()
    conn.close()

def quarantine_file(filepath):
    filename = filepath.name
    # Append a timestamp to prevent overwriting files with the same name from different folders
    safe_filename = f"{int(time.time())}_{filename}"
    quarantine_path = QUARANTINE_DIR / safe_filename
    
    expiration_time = datetime.now() + timedelta(hours=EXPIRATION_HOURS)
    shutil.move(str(filepath), str(quarantine_path))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO quarantine_queue (original_path, quarantine_path, expiration_time, status)
        VALUES (?, ?, ?, 'pending')
    ''', (str(filepath), str(quarantine_path), expiration_time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    print(f"[*] Quarantined: {filename} from {filepath.parent}")

def process_expired_files():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT id, quarantine_path FROM quarantine_queue 
        WHERE status = 'pending' AND expiration_time <= ?
    ''', (current_time,))
    
    for record_id, q_path in cursor.fetchall():
        q_file = Path(q_path)
        if q_file.exists():
            os.remove(q_file)
            print(f"[!] Permanently Deleted: {q_file.name}")
        cursor.execute("UPDATE quarantine_queue SET status = 'deleted' WHERE id = ?", (record_id,))
        
    conn.commit()
    conn.close()

def is_protected(dir_path):
    """Checks if the current directory is inside a restricted OS path."""
    for excluded in EXCLUDED_DIRECTORIES:
        if str(dir_path).startswith(excluded):
            return True
    return False

def is_whitelisted(filepath):
    """Checks if the user explicitly restored this file in the past."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM quarantine_queue 
        WHERE original_path = ? AND status = 'restored'
    ''', (str(filepath),))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def run_daemon():
    setup_environment()
    # Define the starting point. Restricting the scan to your dummy folder initially.
    SCAN_ROOT = Path.home() / "SmartCleanup_Project" / "Downloads_Dummy"
    print(f"Daemon Active. Scanning User Directory: {SCAN_ROOT}")
    
    try:
        while True:
            # os.walk traverses every folder and subfolder from the root down
            for root, dirs, files in os.walk(SCAN_ROOT):
                # Prune the search tree to skip excluded directories entirely
                if is_protected(root) or str(QUARANTINE_DIR) in root:
                    dirs[:] = [] 
                    continue
                
            for file in files:
                    filepath = Path(root) / file
                    file_ext = filepath.suffix.lower()
                    
                    # Skip if the user previously restored this exact file
                    if is_whitelisted(filepath):
                        continue
                    
                    # PIPELINE 1: AI Evaluation for Images
                    if file_ext in {'.jpg', '.jpeg', '.png'}:
                        if is_unwanted_image(filepath):
                            quarantine_file(filepath)
                            
                    # PIPELINE 2: Standard cleanup for known junk (your previous code)
                    elif file_ext in TARGET_EXTENSIONS:
                        quarantine_file(filepath)
            
                    process_expired_files()
                    time.sleep(10) # Increased sleep time to prevent high CPU usage
            
    except KeyboardInterrupt:
        print("\nDaemon terminated.")

if __name__ == "__main__":
    run_daemon()