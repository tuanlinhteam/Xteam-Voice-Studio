import os
import sys
import subprocess
import hashlib
import platform
import json
import uuid
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Cấu hình địa chỉ Vercel API
SETTINGS_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "XteamVoiceStudio" / "license_settings.json"

def get_server_url() -> str:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("server_url", "https://xteamvoice.vercel.app")
        except Exception:
            pass
    return "https://xteamvoice.vercel.app"

def save_server_url(url: str):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"server_url": url.strip()}, f, ensure_ascii=False, indent=2)

def get_machine_id() -> str:
    """
    Tạo Mã máy (HWID) duy nhất và ổn định trên mọi phiên bản Windows (10/11)
    Format: XTM-XXXX-XXXX-XXXX
    """
    raw_parts = []
    
    if platform.system() == "Windows":
        # 1. PowerShell CIM UUID
        try:
            cmd = ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_ComputerSystemProduct).UUID']
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            uuid_out = p.stdout.strip()
            if uuid_out and len(uuid_out) > 10:
                raw_parts.append(uuid_out)
        except Exception:
            pass

        # 2. Machine GUID từ Windows Registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if guid:
                raw_parts.append(guid)
        except Exception:
            pass

    # 3. MAC address & Machine specs
    raw_parts.append(str(uuid.getnode()))
    raw_parts.append(platform.node())
    raw_parts.append(platform.processor())

    combined = "@@".join(raw_parts)
    hash_hex = hashlib.sha256(combined.encode("utf-8")).hexdigest().upper()
    
    return f"XTM-{hash_hex[0:4]}-{hash_hex[4:8]}-{hash_hex[8:12]}"

def check_remote_license(custom_server: Optional[str] = None) -> Dict[str, Any]:
    """
    Gửi mã máy lên Vercel License Server để kiểm tra thời hạn
    """
    hwid = get_machine_id()
    server = (custom_server or get_server_url()).rstrip("/")
    api_url = f"{server}/api/check-license"
    
    try:
        res = requests.post(api_url, json={"hwid": hwid}, timeout=6)
        if res.status_code == 200:
            data = res.json()
            return {
                "hwid": hwid,
                "is_active": data.get("active", False),
                "customer_name": data.get("customer_name", "Chưa kích hoạt"),
                "expires_at": data.get("expires_at", ""),
                "days_left": data.get("days_left", 0),
                "plan": data.get("plan", "VIP License"),
                "message": data.get("message", "Bản quyền hợp lệ."),
                "server_url": server
            }
        else:
            return {
                "hwid": hwid,
                "is_active": False,
                "customer_name": "Chưa kích hoạt",
                "message": f"Mã máy chưa được Admin kích hoạt trên hệ thống.",
                "server_url": server
            }
    except Exception as e:
        return {
            "hwid": hwid,
            "is_active": False,
            "customer_name": "Chưa kích hoạt",
            "message": "Chưa kết nối được tới máy chủ Vercel. Vui lòng kiểm tra mạng hoặc liên hệ Admin.",
            "server_url": server
        }
