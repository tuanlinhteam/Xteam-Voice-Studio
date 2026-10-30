"""VieNeu-TTS: engine giọng đọc chạy offline (tùy chọn, tải mô hình lần đầu)."""
import os
import re
import io
import json
import time
import uuid
import wave
import threading
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .tts_engine import CLONES_DIR, apply_pronunciation_dict

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

_tts = None
_state: Dict[str, Optional[str]] = {"state": "idle", "message": "Chưa khởi động VieNeu-TTS", "error": None}
_load_lock = threading.Lock()
_infer_lock = threading.Lock()
_voices_cache: List[dict] = []
_current_model_id: Optional[str] = None


def is_vieneu_voice(voice_id: str) -> bool:
    return voice_id.startswith("vn:") or voice_id.startswith("clone:")


def is_installed() -> bool:
    try:
        return importlib.util.find_spec("vieneu") is not None
    except Exception:
        return False


def get_current_model_id() -> str:
    global _current_model_id
    if not _current_model_id:
        try:
            from .tts_engine import load_app_settings
            _current_model_id = load_app_settings().get("active_model", "v3turbo_int8")
        except Exception:
            _current_model_id = "v3turbo_int8"
    return _current_model_id


def status() -> dict:
    return {"installed": is_installed(), "current_model": get_current_model_id(), **_state}


def switch_model(model_id: str):
    """Chuyển đổi mô hình AI và nạp lại mô hình tương ứng."""
    global _tts, _voices_cache, _current_model_id
    with _load_lock:
        _current_model_id = model_id
        _tts = None
        _voices_cache = []
    
    if model_id == "supertonic_3":
        _state.update(state="ready", message="Mô hình Supertonic 3 (31 ngôn ngữ) đã sẵn sàng", error=None)
        return
    
    start_load(model_id)


def _load_model(model_id: Optional[str] = None):
    global _tts, _voices_cache, _current_model_id
    with _load_lock:
        if _tts is not None:
            return
        if not model_id:
            model_id = get_current_model_id()
        _current_model_id = model_id

        if model_id == "supertonic_3":
            _state.update(state="ready", message="Mô hình Supertonic 3 (31 ngôn ngữ) đã sẵn sàng", error=None)
            return

        try:
            model_names = {
                "v3turbo_int8": "VieNeu-TTS v3 Turbo (INT8 CPU)",
                "v3turbo_gpu": "VieNeu-TTS v3 Turbo (GPU NVIDIA)",
                "v3turbo_fp32": "VieNeu-TTS v3 Turbo (FP32 Studio Quality)",
                "v3nano": "VieNeu-TTS v3 Nano (CPU 24kHz)",
            }
            display_name = model_names.get(model_id, model_id)
            _state.update(
                state="loading",
                message=f"Đang tải và nạp {display_name}...",
                error=None,
            )
            from vieneu import Vieneu
            if model_id == "v3nano":
                _tts = Vieneu(mode="v3nano")
            elif model_id == "v3turbo_fp32":
                _tts = Vieneu(mode="v3turbo", precision="fp32")
            elif model_id == "v3turbo_gpu":
                try:
                    _tts = Vieneu(mode="v3turbo", device="cuda")
                except Exception:
                    _tts = Vieneu(mode="v3turbo")
            else:
                _tts = Vieneu(mode="v3turbo")

            _voices_cache = _build_preset_voices()
            _state.update(state="ready", message=f"{display_name} đã sẵn sàng (chạy offline)", error=None)
        except Exception as e:
            _tts = None
            _state.update(state="error", message=f"Không khởi động được {model_id}: {e}", error=str(e))


def start_load(model_id: Optional[str] = None):
    """Bắt đầu nạp mô hình ở luồng nền (không chặn giao diện)."""
    if _state["state"] == "loading":
        return
    if not is_installed():
        _state.update(state="error", message="Bản này chưa có thư viện VieNeu-TTS.", error="not_installed")
        return
    _state.update(state="loading", message="Đang khởi động mô hình AI...", error=None)
    threading.Thread(target=_load_model, args=(model_id,), daemon=True).start()


def ensure_loaded():
    if _tts is None:
        if not is_installed():
            raise RuntimeError("Bản này chưa có thư viện VieNeu-TTS.")
        _load_model()
    if _tts is None:
        raise RuntimeError(_state.get("message") or "Mô hình AI chưa sẵn sàng")


def _build_preset_voices() -> List[dict]:
    out = []
    try:
        for label, name in _tts.list_preset_voices():
            gender, region, style = "Nam", "Miền Bắc", ""
            if " — " in label:
                parts = [p.strip() for p in label.split(" — ", 1)[1].split("·")]
                if len(parts) >= 1:
                    gender = parts[0] or gender
                if len(parts) >= 2:
                    region = "Miền " + parts[1].replace("Miền", "").strip()
                if len(parts) >= 3:
                    style = parts[2]
            out.append({
                "id": f"vn:{name}",
                "name": name,
                "gender": "Nữ" if "Nữ" in gender else "Nam",
                "region": region,
                "style": style,
                "sample": f"Xin chào, tôi là {name}. Rất vui được đọc nội dung cho bạn.",
                "engine": "vieneu",
            })
    except Exception:
        pass
    return out


def preset_voices() -> List[dict]:
    if not _voices_cache:
        return [
            {"id": "vn:pnnbao_female", "name": "Bảo Ngọc", "gender": "Nữ", "region": "Miền Bắc", "style": "Tự nhiên / Chuẩn", "sample": "Xin chào, tôi là Bảo Ngọc. Rất vui được đọc nội dung cho bạn.", "engine": "vieneu"},
            {"id": "vn:pnnbao_male", "name": "Bảo Nam", "gender": "Nam", "region": "Miền Bắc", "style": "Trầm ấm / Truyền cảm", "sample": "Xin chào, tôi là Bảo Nam. Rất vui được đọc nội dung cho bạn.", "engine": "vieneu"},
            {"id": "vn:sg_female", "name": "Phương Vy", "gender": "Nữ", "region": "Miền Nam", "style": "Dịu dàng / Nam Bộ", "sample": "Xin chào, tôi là Phương Vy. Rất vui được đồng hành cùng bạn.", "engine": "vieneu"},
            {"id": "vn:sg_male", "name": "Minh Khôi", "gender": "Nam", "region": "Miền Nam", "style": "Trẻ trung / Nam Bộ", "sample": "Xin chào, tôi là Minh Khôi.", "engine": "vieneu"},
        ]
    return list(_voices_cache)


# ---------- Giọng nhân bản ----------
def list_clones() -> List[dict]:
    items = []
    for meta in sorted(CLONES_DIR.glob("clone_*.json")):
        try:
            with open(meta, "r", encoding="utf-8") as f:
                d = json.load(f)
            if (CLONES_DIR / d["file"]).exists():
                items.append({
                    "id": f"clone:{d['id']}",
                    "name": f"{d['name']} (Nhân bản)",
                    "gender": "Tự động",
                    "region": "Nhân bản",
                    "style": "Giọng của bạn",
                    "sample": "Xin chào, đây là giọng nhân bản của tôi.",
                    "engine": "vieneu",
                    "is_cloned": True,
                })
        except Exception:
            continue
    return items


def _clone_ref_path(voice_id: str) -> Path:
    cid = voice_id.split(":", 1)[1]
    with open(CLONES_DIR / f"{cid}.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    return CLONES_DIR / d["file"]


def save_clone(name: str, filename: str, content: bytes) -> dict:
    cid = f"clone_{uuid.uuid4().hex[:6]}"
    ext = Path(filename).suffix.lower() or ".wav"
    audio_file = f"{cid}{ext}"
    (CLONES_DIR / audio_file).write_bytes(content)
    with open(CLONES_DIR / f"{cid}.json", "w", encoding="utf-8") as f:
        json.dump({"id": cid, "name": name.strip(), "file": audio_file, "created": int(time.time())},
                  f, ensure_ascii=False, indent=2)
    return {"id": f"clone:{cid}", "name": f"{name.strip()} (Nhân bản)"}


def delete_clone(voice_id: str) -> bool:
    cid = voice_id.split(":", 1)[1]
    meta = CLONES_DIR / f"{cid}.json"
    if not meta.exists():
        return False
    try:
        with open(meta, "r", encoding="utf-8") as f:
            d = json.load(f)
        (CLONES_DIR / d["file"]).unlink(missing_ok=True)
    except Exception:
        pass
    meta.unlink(missing_ok=True)
    return True


# ---------- Tổng hợp giọng ----------
def clean_text(text: str) -> str:
    text = apply_pronunciation_dict(text)
    text = re.sub(r"\[\s*nghỉ[^\]]*\]", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    return re.sub(r"\s+", " ", text).strip() or "Không có nội dung."


def synth_pcm(text: str, voice_id: str, speed: float = 1.0) -> Tuple[np.ndarray, int]:
    """Trả về (mảng int16 mono, sample_rate)."""
    ensure_loaded()
    kwargs = {}
    if voice_id.startswith("clone:"):
        kwargs["ref_audio"] = str(_clone_ref_path(voice_id))
    else:
        kwargs["voice"] = voice_id.split(":", 1)[1]
    with _infer_lock:
        audio = _tts.infer(text=clean_text(text), **kwargs)
    audio = np.asarray(audio, dtype=np.float32).squeeze()
    sr = int(getattr(_tts, "sample_rate", 48000))
    if abs(speed - 1.0) > 0.02 and audio.size > 2048:
        try:
            import librosa
            audio = librosa.effects.time_stretch(audio, rate=float(speed)).astype(np.float32)
        except Exception:
            pass
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    return pcm, sr


def pcm_to_wav_bytes(pcm: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
