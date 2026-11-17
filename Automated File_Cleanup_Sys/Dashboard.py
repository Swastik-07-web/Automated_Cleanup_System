import sqlite3
import shutil
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Connect to the same database the daemon uses
BASE_DIR = Path.home() / "SmartCleanup_Project"
DB_PATH = BASE_DIR / "quarantine.db"

def fetch_pending_files():
    """Fetches files that are waiting in the quarantine queue."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, original_path, quarantine_path, expiration_time 
        FROM quarantine_queue WHERE status = 'pending'
    ''')
    records = cursor.fetchall()
    conn.close()
    return records

def restore_file(record_id, original_path, quarantine_path, window):
    """Moves the file back to its original location and updates the DB."""
    if os.path.exists(quarantine_path):
        # Create the original directory if it was deleted
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.move(quarantine_path, original_path)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE quarantine_queue SET status = 'restored' WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    
    messagebox.showinfo("Restored", "File safely returned to its original folder!")
    refresh_list(window)

def delete_file(record_id, quarantine_path, window):
    """Bypasses the timer and deletes the file immediately."""
    if os.path.exists(quarantine_path):
        os.remove(quarantine_path)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE quarantine_queue SET status = 'deleted' WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    
    messagebox.showinfo("Deleted", "File permanently removed.")
    refresh_list(window)

def refresh_list(window):
    """Clears and reloads the UI with current pending files."""
    for widget in window.winfo_children():
        widget.destroy()
        
    tk.Label(window, text="Smart Cleanup: Quarantine Queue", font=("Arial", 14, "bold")).pack(pady=10)
    
    records = fetch_pending_files()
    
    if not records:
        tk.Label(window, text="No files currently pending deletion.", font=("Arial", 11)).pack(pady=20)
        return

    for record in records:
        rec_id, orig_path, quar_path, exp_time = record
        filename = Path(orig_path).name
        
        frame = tk.Frame(window, bd=2, relief="groove", padx=10, pady=10)
        frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame, text=f"File: {filename}", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(frame, text=f"Deletes at: {exp_time}", fg="red").pack(anchor="w")
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(anchor="e")
        
        tk.Button(btn_frame, text="Keep (Restore)", bg="lightgreen", 
                  command=lambda r=rec_id, o=orig_path, q=quar_path: restore_file(r, o, q, window)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete Now", bg="salmon", 
                  command=lambda r=rec_id, q=quar_path: delete_file(r, q, window)).pack(side="left")

def run_dashboard():
    root = tk.Tk()
    root.title("Smart Cleanup Dashboard")
    root.geometry("450x400")
    refresh_list(root)
    root.mainloop()

if __name__ == "__main__":
    run_dashboard()