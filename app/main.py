import os
import sys
import json
import time
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response, PlainTextResponse
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
    generate_srt_subtitles,
    synthesize_srt_audio,
    synthesize_conversation_audio,
    clean_text_spacing,
    extract_text_from_file,
    parse_srt,
    load_app_settings,
    save_app_settings,
    get_local_lan_ip,
    check_gpu_status,
    SUPERTONIC_VOICES
)

from . import vieneu_engine as vn

from .license_manager import (
    get_machine_id,
    check_remote_license,
    get_server_url,
    save_server_url
)

app = FastAPI(
    title="Xteam Voice Studio API",
    description="Local AI Text-to-Speech Engine with Machine ID License & Emerald Green Interface",
    version="1.0.4"
)

# Nhật ký hệ thống (System Logs Buffer)
APP_LOGS: List[dict] = []
MAX_LOG_ENTRIES = 500

def add_log(level: str, message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "time": timestamp,
        "level": level.upper(),
        "message": message
    }
    APP_LOGS.append(entry)
    if len(APP_LOGS) > MAX_LOG_ENTRIES:
        APP_LOGS.pop(0)
    try:
        with open("xteam_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
    except Exception:
        pass

# Ghi nhận log khởi động
add_log("INFO", "Khởi động Xteam Voice Studio v1.0.4 (Bản chuẩn)")
add_log("INFO", "Nền tảng vận hành: 100% Cục bộ & Offline bảo mật")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".html", ".js", ".css")) or path in ["/", "/index.html"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "north_male_news_1"
    speed: float = 1.0
    format: str = "mp3"
    include_subtitles: bool = False

class DialogueTurn(BaseModel):
    speaker: Optional[str] = "Nhân vật"
    text: str
    voice_id: str = "north_male_news_1"
    speed: float = 1.0

class ConversationRequest(BaseModel):
    dialogues: List[DialogueTurn]
    pause_between: float = 0.5
    format: str = "wav"

class CleanTextRequest(BaseModel):
    text: str

class ServerConfig(BaseModel):
    server_url: str

class ModelSelectRequest(BaseModel):
    model_id: str

class LanToggleRequest(BaseModel):
    enabled: bool

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
    settings = load_app_settings()
    active_model = settings.get("active_model", "v3turbo_int8")

    edge = [dict(v, engine=v.get("engine", "edge")) for v in VOICES if not v.get("is_cloned")]
    vn_voices = vn.preset_voices()
    all_voices = edge + SUPERTONIC_VOICES + vn_voices + vn.list_clones()

    return {
        "success": True,
        "voices": all_voices,
        "vieneu": vn.status(),
        "active_model": active_model
    }

@app.get("/api/settings/models")
def get_models_status():
    settings = load_app_settings()
    gpu = check_gpu_status()
    active = settings.get("active_model", "v3turbo_int8")

    models = [
        {
            "id": "v3turbo_int8",
            "name": "VieNeu-TTS v3 Turbo",
            "tags": ["INT8 CPU", "Khuyến nghị", "Nhân bản giọng"],
            "downloaded": True,
            "status_text": "Đã tải",
            "notes": "Chạy nhanh nhất trên CPU, âm thanh 48 kHz, ít tốn RAM.",
            "is_active": (active == "v3turbo_int8"),
            "action_type": "active" if (active == "v3turbo_int8") else "apply"
        },
        {
            "id": "v3turbo_gpu",
            "name": "VieNeu-TTS v3 Turbo",
            "tags": ["GPU NVIDIA", "Nhanh nhất"],
            "downloaded": gpu["available"],
            "status_text": f"Sẵn sàng: {gpu['gpu_name']}" if gpu["available"] else "Không thấy GPU NVIDIA dùng được trên máy này.",
            "available": gpu["available"],
            "notes": "Tối ưu hóa chạy trên Card đồ họa NVIDIA.",
            "is_active": (active == "v3turbo_gpu"),
            "action_type": "active" if (active == "v3turbo_gpu") else ("apply" if gpu["available"] else "disabled")
        },
        {
            "id": "v3turbo_fp32",
            "name": "VieNeu-TTS v3 Turbo",
            "tags": ["FP32 Studio Quality", "Nhân bản giọng"],
            "downloaded": True,
            "status_text": "Đã tải · Cần tải thêm ở lần đầu.",
            "notes": "Chất lượng âm thanh phòng thu tối đa 48 kHz.",
            "is_active": (active == "v3turbo_fp32"),
            "action_type": "active" if (active == "v3turbo_fp32") else "apply"
        },
        {
            "id": "supertonic_3",
            "name": "Supertonic 3",
            "tags": ["31 ngôn ngữ", "CPU", "44 kHz"],
            "downloaded": True,
            "status_text": "Đã tải · Không nhân bản giọng. Tiếng Việt nên dùng VieNeu.",
            "notes": "10 giọng nam nữ quốc tế, đọc chuẩn tiếng Anh, Nhật, Hàn, Pháp...",
            "is_active": (active == "supertonic_3"),
            "action_type": "active" if (active == "supertonic_3") else "apply"
        },
        {
            "id": "v3nano",
            "name": "VieNeu-TTS v3 Nano",
            "tags": ["Thử nghiệm", "CPU", "24 kHz", "Nhân bản giọng"],
            "downloaded": False,
            "status_text": "Chưa tải · 400 MB · Chất lượng và tiếng Anh kém hơn Turbo.",
            "notes": "Mô hình siêu nhẹ dành cho máy CPU yếu.",
            "is_active": (active == "v3nano"),
            "action_type": "active" if (active == "v3nano") else "download_apply"
        }
    ]
    return {
        "success": True,
        "active_model": active,
        "models": models,
        "gpu": gpu
    }

@app.post("/api/settings/models/select")
def select_model(req: ModelSelectRequest):
    settings = load_app_settings()
    settings["active_model"] = req.model_id
    save_app_settings(settings)
    add_log("INFO", f"Chuyển đổi sang mô hình AI: {req.model_id}")
    try:
        vn.switch_model(req.model_id)
    except Exception as e:
        add_log("ERROR", f"Lỗi nạp mô hình {req.model_id}: {str(e)}")
        print(f"Error switching model in engine: {e}")
    return {
        "success": True,
        "active_model": req.model_id,
        "message": f"Đã áp dụng thành công mô hình {req.model_id}"
    }

@app.get("/api/settings/lan")
def get_lan_settings():
    settings = load_app_settings()
    local_ip = get_local_lan_ip()
    return {
        "success": True,
        "lan_enabled": settings.get("lan_enabled", False),
        "lan_ip": local_ip,
        "lan_url": f"http://{local_ip}:8001",
        "api_key": settings.get("lan_api_key", "")
    }

@app.post("/api/settings/lan/toggle")
def toggle_lan(req: LanToggleRequest):
    settings = load_app_settings()
    settings["lan_enabled"] = req.enabled
    save_app_settings(settings)
    return {"success": True, "lan_enabled": req.enabled}

@app.post("/api/settings/lan/regen-key")
def regen_lan_key():
    import uuid
    settings = load_app_settings()
    new_key = "xteam_sec_" + uuid.uuid4().hex[:16]
    settings["lan_api_key"] = new_key
    save_app_settings(settings)
    return {"success": True, "api_key": new_key}

@app.get("/api/logs")
def get_logs():
    formatted_lines = [f"[{l['time']}] [{l['level']}] {l['message']}" for l in APP_LOGS]
    return {
        "success": True,
        "logs": APP_LOGS,
        "total": len(APP_LOGS),
        "text": "\n".join(formatted_lines)
    }

@app.delete("/api/logs")
@app.post("/api/logs/clear")
def clear_logs():
    APP_LOGS.clear()
    add_log("INFO", "Đã xóa nhật ký log hệ thống")
    return {"success": True, "message": "Đã làm trống nhật ký log"}

@app.get("/api/vieneu/status")
def vieneu_status():
    return vn.status()

@app.post("/api/vieneu/load")
def vieneu_load():
    vn.start_load()
    return vn.status()

@app.get("/api/tts/preview")
async def get_voice_preview(voice_id: str):
    if vn.is_vieneu_voice(voice_id):
        import hashlib
        cache_wav = PREVIEWS_DIR / f"preview_{hashlib.md5(voice_id.encode('utf-8')).hexdigest()[:12]}.wav"
        if not cache_wav.exists():
            try:
                sample = "Xin chào, đây là giọng đọc thử của Xteam Voice Studio."
                pcm, sr = await asyncio.to_thread(vn.synth_pcm, sample, voice_id, 1.0)
                cache_wav.write_bytes(vn.pcm_to_wav_bytes(pcm, sr))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Lỗi tạo âm thanh nghe thử: {str(e)}")
        return FileResponse(cache_wav, media_type="audio/wav")

    all_v = VOICES + SUPERTONIC_VOICES
    voice = next((v for v in all_v if v["id"] == voice_id), None)
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
    use_vn = vn.is_vieneu_voice(req.voice_id)
    filename = f"xteam_tts_{int(time.time())}_{item_id}.{'wav' if use_vn else 'mp3'}"
    filepath = HISTORY_DIR / filename
    
    try:
        if use_vn:
            pcm, sr = await asyncio.to_thread(vn.synth_pcm, req.text, req.voice_id, req.speed)
            audio_bytes = vn.pcm_to_wav_bytes(pcm, sr)
            filepath.write_bytes(audio_bytes)
        else:
            audio_bytes = await synthesize_speech_edge(req.text, req.voice_id, req.speed, output_path=filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tổng hợp giọng nói: {str(e)}")
        
    srt_content = generate_srt_subtitles(req.text, req.speed) if req.include_subtitles else ""
    srt_filename = filename.rsplit(".", 1)[0] + ".srt"
    if srt_content:
        with open(HISTORY_DIR / srt_filename, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
    # Tự động lưu bản sao vào thư mục Downloads của người dùng
    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, downloads_dir / filename)
        if srt_content:
            shutil.copy2(HISTORY_DIR / srt_filename, downloads_dir / srt_filename)
    except Exception:
        pass
    
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
        
    add_log("SUCCESS", f"Tạo giọng nói: giọng={req.voice_id}, tốc độ={req.speed}x, dung lượng={meta['size_kb']}KB -> {filename}")
    return {
        "success": True,
        "id": item_id,
        "filename": filename,
        "audio_url": f"/api/audio/{filename}",
        "srt_url": f"/api/audio/{srt_filename}" if srt_content else None,
        "srt_content": srt_content,
        "size_kb": meta["size_kb"],
        "metadata": meta
    }


@app.post("/api/tts/generate-with-subtitles")
async def generate_tts_with_subtitles(req: TTSRequest):
    req.include_subtitles = True
    return await generate_tts(req)


@app.post("/api/tts/conversation")
async def generate_conversation(req: ConversationRequest):
    lic = check_remote_license()
    if not lic.get("is_active"):
        raise HTTPException(status_code=403, detail=f"Bản quyền chưa được kích hoạt hoặc đã hết hạn! Mã máy của bạn là: {lic.get('hwid')}")
    
    valid_dialogues = [d.model_dump() for d in req.dialogues if d.text.strip()]
    if not valid_dialogues:
        raise HTTPException(status_code=400, detail="Kịch bản hội thoại cần ít nhất một câu thoại.")

    item_id = str(uuid.uuid4())[:8]
    filename = f"xteam_conv_{int(time.time())}_{item_id}.wav"
    filepath = HISTORY_DIR / filename

    try:
        info = await synthesize_conversation_audio(valid_dialogues, req.pause_between, filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo hội thoại: {str(e)}")

    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, downloads_dir / filename)
    except Exception:
        pass

    summary_text = " | ".join(f"{d['speaker']}: {d['text']}" for d in valid_dialogues[:3])
    meta = {
        "id": item_id,
        "filename": filename,
        "srt_filename": None,
        "text": f"[Hội thoại] {info['turns']} lượt thoại, {info['duration']}s - {summary_text[:100]}",
        "full_text": json.dumps(valid_dialogues, ensure_ascii=False),
        "voice_id": "multi-speaker",
        "speed": 1.0,
        "timestamp": int(time.time()),
        "size_kb": round(filepath.stat().st_size / 1024, 1),
        "created_at": time.strftime("%H:%M:%S %d/%m/%Y"),
        "conversation_details": info["turn_details"]
    }
    with open(HISTORY_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    add_log("SUCCESS", f"Tạo hội thoại: {info['turns']} lượt thoại, {info['duration']}s -> {filename}")
    return {
        "success": True,
        "id": item_id,
        "filename": filename,
        "audio_url": f"/api/audio/{filename}",
        "size_kb": meta["size_kb"],
        "turns": info["turns"],
        "duration": info["duration"],
        "metadata": meta
    }


@app.post("/api/utils/extract-text")
async def extract_text_endpoint(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Tệp tải lên rỗng.")
    try:
        extracted = extract_text_from_file(content, file.filename or "doc.txt")
        return {
            "success": True,
            "filename": file.filename,
            "text": extracted,
            "chars": len(extracted)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc tệp: {str(e)}")


@app.post("/api/utils/clean-text")
def clean_text_endpoint(req: CleanTextRequest):
    return {
        "success": True,
        "cleaned_text": clean_text_spacing(req.text)
    }


@app.get("/api/dictionary/template.csv")
def download_dictionary_template():
    csv_content = "\ufeffTừ gốc,Cách đọc\r\nKTX,ký túc xá\r\nSGK,sách giáo khoa\r\nTPHCM,thành phố Hồ Chí Minh\r\nAI,trí tuệ nhân tạo\r\nTTS,chuyển văn bản thành giọng nói\r\n"
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tu-dien-mau.csv"'}
    )


@app.get("/api/dictionary/export.csv")
def export_dictionary_csv():
    pdict = load_pronunciation_dict()
    lines = ["\ufeffTừ gốc,Cách đọc"]
    for k, v in sorted(pdict.items()):
        k_escaped = f'"{k}"' if ("," in k or '"' in k) else k
        v_escaped = f'"{v}"' if ("," in v or '"' in v) else v
        lines.append(f"{k_escaped},{v_escaped}")
    csv_content = "\r\n".join(lines) + "\r\n"
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tu-dien-phat-am.csv"'}
    )


@app.post("/api/dictionary/import")
async def import_dictionary_csv(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Tệp CSV rỗng.")
    
    text = ""
    for enc in ["utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"]:
        try:
            text = content.decode(enc)
            break
        except Exception:
            continue
    if not text:
        text = content.decode("utf-8", errors="ignore")

    import csv
    import io
    reader = csv.reader(io.StringIO(text))
    pdict = load_pronunciation_dict()
    imported_count = 0
    skipped_count = 0

    for row_idx, row in enumerate(reader, start=1):
        if not row or len(row) < 2:
            skipped_count += 1
            continue
        key, val = row[0].strip(), row[1].strip()
        if row_idx == 1 and (key.lower() in ["từ gốc", "word", "original", "key"] or val.lower() in ["cách đọc", "replacement", "value"]):
            continue
        if key and val:
            pdict[key] = val
            imported_count += 1
        else:
            skipped_count += 1

    save_pronunciation_dict(pdict)
    return {
        "success": True,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "total_words": len(pdict),
        "dictionary": pdict
    }


@app.get("/cit-voice-studio.md")
@app.get("/api-docs.md")
def get_api_docs_markdown():
    docs = """# Xteam Voice Studio Local API Documentation

Base URL: `http://127.0.0.1:8001`

## Các API chính:
- `GET /health`: Kiểm tra trạng thái máy chủ.
- `GET /voices`: Lấy danh sách toàn bộ giọng đọc (Edge TTS + VieNeu-TTS + Voice Clones).
- `POST /api/tts/generate`: Chuyển văn bản thành file WAV/MP3.
- `POST /api/tts/generate-with-subtitles`: Chuyển văn bản thành audio kèm phụ đề SRT.
- `POST /api/tts/conversation`: Hội thoại đa nhân vật nhiều giọng đọc.
- `POST /api/tts/srt`: Lồng tiếng khớp mốc thời gian file SRT.
- `POST /api/utils/extract-text`: Trích xuất chữ từ file Word (.docx), PDF, TXT.
- `POST /api/utils/clean-text`: Chuẩn hóa khoảng trắng và ngắt dòng thông minh.
- `GET /api/dictionary/template.csv` & `/api/dictionary/export.csv` & `POST /api/dictionary/import`: Quản lý từ điển phát âm qua CSV.
"""
    return PlainTextResponse(content=docs, media_type="text/markdown; charset=utf-8")


class SrtRequest(BaseModel):
    srt_text: str
    voice_id: str = "north_male_news_1"
    speed: float = 1.0
    fit: bool = True

class ZipRequest(BaseModel):
    filenames: List[str]

@app.post("/api/tts/srt")
async def generate_from_srt(req: SrtRequest):
    lic = check_remote_license()
    if not lic.get("is_active"):
        raise HTTPException(status_code=403, detail=f"Bản quyền chưa được kích hoạt hoặc đã hết hạn! Mã máy của bạn là: {lic.get('hwid')}")
    if not parse_srt(req.srt_text):
        raise HTTPException(status_code=400, detail="File SRT không hợp lệ hoặc không có câu nào.")

    item_id = str(uuid.uuid4())[:8]
    filename = f"xteam_srt_{int(time.time())}_{item_id}.wav"
    filepath = HISTORY_DIR / filename
    try:
        info = await synthesize_srt_audio(req.srt_text, req.voice_id, req.speed, filepath, req.fit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc theo SRT: {str(e)}")

    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, downloads_dir / filename)
    except Exception:
        pass

    meta = {
        "id": item_id,
        "filename": filename,
        "srt_filename": None,
        "text": f"[SRT] {info['cues']} câu, {info['duration']}s",
        "full_text": req.srt_text,
        "voice_id": req.voice_id,
        "speed": req.speed,
        "timestamp": int(time.time()),
        "size_kb": round(filepath.stat().st_size / 1024, 1),
        "created_at": time.strftime("%H:%M:%S %d/%m/%Y")
    }
    with open(HISTORY_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    add_log("SUCCESS", f"Tạo âm thanh theo SRT: {info['cues']} câu, {info['duration']}s -> {filename}")
    return {
        "success": True,
        "filename": filename,
        "audio_url": f"/api/audio/{filename}",
        "size_kb": meta["size_kb"],
        "cues": info["cues"],
        "duration": info["duration"],
        "late_cues": info["late_cues"],
        "metadata": meta
    }

@app.post("/api/audio/zip")
def zip_audio(req: ZipRequest):
    import zipfile
    zip_name = f"xteam_batch_{int(time.time())}.zip"
    zip_path = HISTORY_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in req.filenames:
            safe = Path(name).name
            fp = HISTORY_DIR / safe
            if fp.exists():
                z.write(fp, arcname=safe)
    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, downloads_dir / zip_name)
    except Exception:
        pass
    return {"success": True, "filename": zip_name, "url": f"/api/audio/{zip_name}"}
@app.get("/api/audio/{filename}")
def serve_audio(filename: str, download: bool = False):
    file_path = HISTORY_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    if filename.endswith(".zip"):
        media_type = "application/zip"
    if filename.endswith(".srt"):
        media_type = "text/plain; charset=utf-8"
        
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'
        
    return FileResponse(file_path, media_type=media_type, filename=filename, headers=headers)

@app.post("/api/audio/save-to-downloads/{filename}")
def save_to_downloads(filename: str):
    file_path = HISTORY_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        dest_path = downloads_dir / filename
        shutil.copy2(file_path, dest_path)
        
        srt_name = filename.rsplit(".", 1)[0] + ".srt"
        srt_path = HISTORY_DIR / srt_name
        if srt_path.exists():
            shutil.copy2(srt_path, downloads_dir / srt_name)
            
        return {
            "success": True,
            "saved_path": str(dest_path),
            "folder": str(downloads_dir),
            "message": f"Đã lưu thành công vào thư mục Downloads!"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/open-downloads-folder")
def open_downloads_folder():
    try:
        downloads_dir = Path.home() / "Downloads"
        if sys.platform == "win32":
            os.startfile(str(downloads_dir))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

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
async def clone_voice(voice_name: str = Form(...), consent: str = Form("false"), sample_file: UploadFile = File(...)):
    lic = check_remote_license()
    if not lic.get("is_active"):
        raise HTTPException(status_code=403, detail="Bản quyền chưa được kích hoạt hoặc đã hết hạn!")
    if consent.lower() != "true":
        raise HTTPException(status_code=400, detail="Bạn cần xác nhận đây là giọng của chính bạn hoặc đã được chủ giọng cho phép.")
    if not voice_name.strip():
        raise HTTPException(status_code=400, detail="Vui lòng đặt tên cho giọng nhân bản.")
    content = await sample_file.read()
    if len(content) < 2000:
        raise HTTPException(status_code=400, detail="File âm thanh mẫu quá ngắn hoặc bị lỗi.")
    if not vn.is_installed():
        raise HTTPException(status_code=400, detail="Bản này chưa có VieNeu-TTS nên chưa thể nhân bản giọng.")
    info = vn.save_clone(voice_name, sample_file.filename or "sample.wav", content)
    # Kiểm tra giọng nhân bản dùng được (nạp mô hình nếu cần)
    try:
        await asyncio.to_thread(vn.synth_pcm, "Xin chào.", info["id"], 1.0)
    except Exception as e:
        vn.delete_clone(info["id"])
        raise HTTPException(status_code=500, detail=f"Không nhân bản được giọng từ file này: {str(e)}")
    return {"success": True, "voice": {"id": info["id"], "name": info["name"]}}

@app.delete("/api/tts/clone/{voice_id}")
def remove_clone(voice_id: str):
    return {"success": vn.delete_clone(voice_id if voice_id.startswith("clone:") else f"clone:{voice_id}")}
# Serve Frontend static directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    STATIC_DIR = Path(sys._MEIPASS) / "app" / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")



