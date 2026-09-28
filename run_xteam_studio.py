import sys
import os
from pathlib import Path
import threading
import time
import requests

# Ensure current directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import uvicorn
import webview

PORT = 8001
HOST = "127.0.0.1"
APP_URL = f"http://{HOST}:{PORT}"

def start_backend():
    """Chay backend FastAPI o tien trinh nen"""
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning", reload=False)

def wait_for_server():
    """Doi backend san sang truoc khi hien thi cua so desktop"""
    for _ in range(30):
        try:
            r = requests.get(f"{APP_URL}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

if __name__ == "__main__":
    print("=" * 65)
    print("   🌿 DANG KHOI DONG CUA SO NATIVE XTEAM VOICE STUDIO...")
    print(f"   🎨 Giao dien: Emerald Green Theme")
    print(f"   🌐 Local Server: {APP_URL}")
    print("=" * 65)

    # 1. Start backend thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    # 2. Wait for backend
    wait_for_server()

    # 3. Create and launch Native Desktop Window
    window = webview.create_window(
        title="Xteam Voice Studio — Chuyển văn bản thành giọng nói AI",
        url=APP_URL,
        width=1320,
        height=860,
        min_size=(960, 640),
        background_color="#022c22",
        text_select=True
    )
    
    # Run native window loop (blocks until user closes the window)
    webview.start(private_mode=False)
    
    print("[*] Da dong ung dung Xteam Voice Studio.")
    sys.exit(0)
