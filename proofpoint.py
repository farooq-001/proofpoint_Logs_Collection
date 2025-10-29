#!/usr/bin/env python3
import websocket
import json
import time
import os
from datetime import datetime
import shutil
import configparser
import socket
import hashlib

# ===== CONFIGURATION =====
CONFIG_FILE = os.path.join(os.getcwd(), "credentials.conf")
DEDUPE_WINDOW = 1000  # Number of recent messages to check for duplicates

def load_config():
    """Load configuration from credentials.conf."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Configuration file {CONFIG_FILE} not found")
    
    config.read(CONFIG_FILE)
    if 'Proofpoint' not in config:
        raise KeyError("Section [Proofpoint] not found in credentials.conf")
        
    return {
        'CLUSTER_ID': config['Proofpoint'].get('CLUSTER_ID', ''),
        'ACCESS_TOKEN': config['Proofpoint'].get('ACCESS_TOKEN', ''),
        'TCP_HOST': config['Proofpoint'].get('TCP_HOST', '127.0.0.1'),
        'TCP_PORT': config['Proofpoint'].getint('TCP_PORT', 12229)
    }

# Load credentials
try:
    config = load_config()
    CLUSTER_ID = config['CLUSTER_ID']
    ACCESS_TOKEN = config['ACCESS_TOKEN']
    TCP_HOST = config['TCP_HOST']
    TCP_PORT = config['TCP_PORT']
except (FileNotFoundError, KeyError) as e:
    print(f"Configuration error: {e}")
    exit(1)

# Log folder is now wherever the script is run
LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "proofpoint_stream.log")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
MAX_BACKUP_FILES = 4               # keep 2 rotated backups

# Deduplication set
seen_messages = set()

# ===== HELPERS =====
def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

def rotate_logs():
    """Rotate log if it exceeds MAX_FILE_SIZE and maintain backup count."""
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) >= MAX_FILE_SIZE:
        for i in reversed(range(1, MAX_BACKUP_FILES)):
            old_file = f"{LOG_FILE}.{i}"
            new_file = f"{LOG_FILE}.{i+1}"
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
        shutil.move(LOG_FILE, f"{LOG_FILE}.1")

def send_to_tcp(message):
    """Send message to TCP host and port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TCP_HOST, TCP_PORT))
            s.sendall((message + "\n").encode('utf-8'))
    except socket.error as e:
        print(f"TCP send error: {e}")

def is_duplicate(message):
    """Check if message is a duplicate based on its hash."""
    message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
    if message_hash in seen_messages:
        return True
    seen_messages.add(message_hash)
    if len(seen_messages) > DEDUPE_WINDOW:
        seen_messages.pop()
    return False

# ===== CALLBACKS =====
def on_message(ws, message):
    if not is_duplicate(message):
        rotate_logs()
        with open(LOG_FILE, "a") as f:
            f.write(message + "\n")
        send_to_tcp(message)

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed: {close_status_code}, {close_msg}")
    # Reconnect after short delay; PoD will resume logs within 1 hour
    reconnect_delay = 10
    print(f"Reconnecting in {reconnect_delay} seconds...")
    time.sleep(reconnect_delay)
    connect_ws()

def on_open(ws):
    print(f"Connected at {datetime.utcnow().isoformat()}")

# ===== CONNECT FUNCTION =====
def connect_ws():
    ws_url = f"wss://logstream.proofpoint.com/v1/stream?cid={CLUSTER_ID}&type=message"
    ws = websocket.WebSocketApp(
        ws_url,
        header=[f"Authorization: Bearer {ACCESS_TOKEN}"],
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever(ping_interval=30, ping_timeout=10)

# ===== MAIN =====
if __name__ == "__main__":
    ensure_log_dir()
    connect_ws()
