import os
import sys
import json
import time
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .tts_engine import (
    VOICES,
    HISTORY_DIR,
    CLONES_DIR,
    PREVIEWS_DIR,
    DATA_DIR,
    load_pronunciation_dict,
    save_pronunciation_dict,
    synthesize_speech_edge,
    generate_srt_subtitles
)

from .license_manager import (
    get_machine_id,
    check_remote_license,
    get_server_url,
    save_server_url
)

app = FastAPI(
    title="Xteam Voice Studio API",
    description="Local AI Text-to-Speech Engine with Machine ID License & Emerald Green Interface",
    version="1.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "north_male_news_1"
    speed: float = 1.0
    format: str = "mp3"
    include_subtitles: bool = False

class ServerConfig(BaseModel):
    server_url: str

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Xteam Voice Studio",
        "version": "1.0.1",
        "theme": "emerald-green",
        "hwid": get_machine_id()
    }

@app.get("/api/license/status")
def get_license_status():
    """Kiểm tra mã máy và bản quyền từ xa"""
    return check_remote_license()

@app.post("/api/license/config")
def update_license_server(cfg: ServerConfig):
    save_server_url(cfg.server_url)
    return {"success": True, "server_url": cfg.server_url}

@app.get("/voices")
def get_voices():
    return {
        "success": True,
        "voices": VOICES
    }

@app.get("/api/tts/preview")
async def get_voice_preview(voice_id: str):
    voice = next((v for v in VOICES if v["id"] == voice_id), None)
    if not voice:
        raise HTTPException(status_code=404, detail="Không tìm thấy giọng đọc")
    
    sample_text = voice.get("sample", "Chào mừng bạn đến với Xteam Voice Studio.")
    cache_path = PREVIEWS_DIR / f"preview_{voice_id}.mp3"
    
    if not cache_path.exists():
        try:
            await synthesize_speech_edge(sample_text, voice_id, speed=1.0, output_path=cache_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi tạo âm thanh nghe thử: {str(e)}")
            
    return FileResponse(cache_path, media_type="audio/mpeg", filename=f"preview_{voice_id}.mp3")

@app.get("/api/dictionary")
def get_dictionary():
    return {"dictionary": load_pronunciation_dict()}

@app.post("/api/dictionary")
def update_dictionary(payload: Dict[str, str]):
    save_pronunciation_dict(payload)
    return {"success": True, "dictionary": payload}

@app.post("/api/tts/generate")
async def generate_tts(req: TTSRequest):
    # Kiểm tra bản quyền trước khi tạo
    lic = check_remote_license()
    if not lic.get("is_active"):
        raise HTTPException(status_code=403, detail=f"Bản quyền chưa được kích hoạt hoặc đã hết hạn! Mã máy của bạn là: {lic.get('hwid')}")
    
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")
    
    item_id = str(uuid.uuid4())[:8]
    filename = f"xteam_tts_{int(time.time())}_{item_id}.mp3"
    filepath = HISTORY_DIR / filename
    
    try:
        audio_bytes = await synthesize_speech_edge(req.text, req.voice_id, req.speed, output_path=filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tổng hợp giọng nói: {str(e)}")
        
    srt_content = generate_srt_subtitles(req.text, req.speed) if req.include_subtitles else ""
    srt_filename = f"xteam_tts_{int(time.time())}_{item_id}.srt"
    if srt_content:
        with open(HISTORY_DIR / srt_filename, "w", encoding="utf-8") as f:
            f.write(srt_content)
    
    meta = {
        "id": item_id,
        "filename": filename,
        "srt_filename": srt_filename if srt_content else None,
        "text": req.text[:120] + ("..." if len(req.text) > 120 else ""),
        "full_text": req.text,
        "voice_id": req.voice_id,
        "speed": req.speed,
        "timestamp": int(time.time()),
        "size_kb": round(len(audio_bytes) / 1024, 1),
        "created_at": time.strftime("%H:%M:%S %d/%m/%Y")
    }
    
    meta_path = HISTORY_DIR / f"{filename}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        
    return {
        "success": True,
        "id": item_id,
        "audio_url": f"/api/audio/{filename}",
        "srt_url": f"/api/audio/{srt_filename}" if srt_content else None,
        "srt_content": srt_content,
        "size_kb": meta["size_kb"],
        "metadata": meta
    }

@app.get("/api/audio/{filename}")
def serve_audio(filename: str):
    file_path = HISTORY_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    if filename.endswith(".srt"):
        media_type = "text/plain; charset=utf-8"
        
    return FileResponse(file_path, media_type=media_type, filename=filename)

@app.get("/api/history")
def get_history():
    items = []
    for meta_file in sorted(HISTORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                items.append(data)
        except Exception:
            continue
    return {"history": items}

@app.delete("/api/history/{item_id}")
def delete_history_item(item_id: str):
    found = False
    for meta_file in HISTORY_DIR.glob("*.json"):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("id") == item_id:
                audio_file = HISTORY_DIR / data.get("filename", "")
                srt_file = HISTORY_DIR / (data.get("srt_filename") or "")
                if audio_file.exists():
                    audio_file.unlink()
                if srt_file.exists():
                    srt_file.unlink()
                meta_file.unlink()
                found = True
                break
        except Exception:
            continue
    return {"success": found}

@app.post("/api/tts/clone")
async def clone_voice(voice_name: str = Form(...), sample_file: UploadFile = File(...)):
    clone_id = f"clone_{uuid.uuid4().hex[:6]}"
    save_path = CLONES_DIR / f"{clone_id}_{sample_file.filename}"
    with open(save_path, "wb") as f:
        content = await sample_file.read()
        f.write(content)
        
    clone_voice = {
        "id": clone_id,
        "name": f"{voice_name} (Nhân bản)",
        "gender": "Tự động",
        "region": "Custom",
        "style": "Đã nhân bản",
        "sample": "Giọng nhân bản từ tệp mẫu.",
        "is_cloned": True
    }
    VOICES.insert(0, clone_voice)
    return {"success": True, "voice": clone_voice}

# Serve Frontend static directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    STATIC_DIR = Path(sys._MEIPASS) / "app" / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
