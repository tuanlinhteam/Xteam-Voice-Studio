import os
import sys
import re
import json
import time
import asyncio
import io
from pathlib import Path
from typing import List, Dict, Any, Optional

import edge_tts

# Determine Persistent Data Directory
if os.environ.get("LOCALAPPDATA"):
    DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "XteamVoiceStudio"
else:
    DATA_DIR = Path.home() / "XteamVoiceStudio"

HISTORY_DIR = DATA_DIR / "history"
CLONES_DIR = DATA_DIR / "clones"
PREVIEWS_DIR = DATA_DIR / "previews"
DICT_FILE = DATA_DIR / "pronunciation-dict.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

for folder in [DATA_DIR, HISTORY_DIR, CLONES_DIR, PREVIEWS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Default pronunciation dict
if not DICT_FILE.exists():
    default_dict = {
        "KTX": "ký túc xá",
        "SGK": "sách giáo khoa",
        "TPHCM": "thành phố Hồ Chí Minh",
        "HN": "Hà Nội",
        "AI": "trí tuệ nhân tạo",
        "TTS": "chuyển văn bản thành giọng nói",
        "Xteam": "Ích-tim",
        "CIT": "Si-ai-ti"
    }
    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(default_dict, f, ensure_ascii=False, indent=2)

def load_app_settings() -> dict:
    import uuid
    defaults = {
        "active_model": "v3turbo_int8",
        "lan_enabled": False,
        "lan_api_key": "xteam_sec_" + uuid.uuid4().hex[:16],
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    else:
        try:
            save_app_settings(defaults)
        except Exception:
            pass
    return defaults

def save_app_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_local_lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check_gpu_status() -> dict:
    import subprocess
    try:
        res = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            gpu_info = res.stdout.strip().split("\n")[0]
            return {"available": True, "gpu_name": gpu_info}
    except Exception:
        pass
    return {"available": False, "gpu_name": None}

SUPERTONIC_VOICES = [
    {"id": "st:M2", "name": "Watson (M2)", "gender": "Nam", "region": "Quốc tế (31 thứ tiếng)", "style": "Trầm / Phim tài liệu (Mặc định)", "engine": "supertonic", "base": "en-US-GuyNeural", "sample": "History has witnessed extraordinary moments."},
    {"id": "st:F1", "name": "Luna (F1)", "gender": "Nữ", "region": "Quốc tế (31 thứ tiếng)", "style": "Điềm tĩnh / Chăm sóc", "engine": "supertonic", "base": "en-US-JennyNeural", "sample": "This morning, I took a walk in the park."},
    {"id": "st:F2", "name": "Moka (F2)", "gender": "Nữ", "region": "Quốc tế (31 thứ tiếng)", "style": "Tươi sáng / Trẻ trung", "engine": "supertonic", "base": "en-US-JennyNeural", "sample": "Hello everyone! Welcome to my channel."},
    {"id": "st:F3", "name": "Nora (F3)", "gender": "Nữ", "region": "Quốc tế (31 thứ tiếng)", "style": "Phát thanh viên / Tin tức", "engine": "supertonic", "base": "en-US-JennyNeural", "sample": "Here is the latest international news update."},
    {"id": "st:F4", "name": "Chloe (F4)", "gender": "Nữ", "region": "Quốc tế (31 thứ tiếng)", "style": "Dứt khoát / Đào tạo", "engine": "supertonic", "base": "en-US-JennyNeural", "sample": "Welcome to our professional training program."},
    {"id": "st:F5", "name": "Stella (F5)", "gender": "Nữ", "region": "Quốc tế (31 thứ tiếng)", "style": "Dịu dàng / Sách nói", "engine": "supertonic", "base": "en-US-JennyNeural", "sample": "Once upon a time in a peaceful land."},
    {"id": "st:M1", "name": "Keld (M1)", "gender": "Nam", "region": "Quốc tế (31 thứ tiếng)", "style": "Năng động / Quảng cáo", "engine": "supertonic", "base": "en-US-GuyNeural", "sample": "Don't miss out on this amazing opportunity today!"},
    {"id": "st:M3", "name": "Alphonse (M3)", "gender": "Nam", "region": "Quốc tế (31 thứ tiếng)", "style": "Chỉn chu / Thuyết trình", "engine": "supertonic", "base": "en-US-GuyNeural", "sample": "Good morning ladies and gentlemen."},
    {"id": "st:M4", "name": "Oliver (M4)", "gender": "Nam", "region": "Quốc tế (31 thứ tiếng)", "style": "Thân thiện / Thiếu nhi", "engine": "supertonic", "base": "en-US-GuyNeural", "sample": "Let's explore science and nature together."},
    {"id": "st:M5", "name": "Ethan (M5)", "gender": "Nam", "region": "Quốc tế (31 thứ tiếng)", "style": "Ấm áp / Kể chuyện", "engine": "supertonic", "base": "en-US-GuyNeural", "sample": "Sit back and relax with today's story."}
]

# Built-in Voice List (25 voices, 3 regions, Male & Female with tailored acoustic pitch/rate profiles)
VOICES = [
    # Miền Bắc
    {"id": "north_female_news_1", "name": "Ngọc Mai", "gender": "Nữ", "region": "Miền Bắc", "style": "Tin tức / Chuẩn", "base": "vi-VN-HoaiMyNeural", "pitch": "+0Hz", "rate": "+0%", "sample": "Chào mừng bạn đến với Xteam Voice Studio."},
    {"id": "north_female_story_1", "name": "Hoài An", "gender": "Nữ", "region": "Miền Bắc", "style": "Kể chuyện / Truyền cảm", "base": "vi-VN-HoaiMyNeural", "pitch": "-4Hz", "rate": "-6%", "sample": "Ngày xửa ngày xưa, tại một thung lũng xinh đẹp."},
    {"id": "north_female_natural_1", "name": "Thu Hà", "gender": "Nữ", "region": "Miền Bắc", "style": "Tự nhiên / Trẻ trung", "base": "vi-VN-HoaiMyNeural", "pitch": "+6Hz", "rate": "+4%", "sample": "Hôm nay thời tiết thật đẹp, cùng mình đi dạo nhé."},
    {"id": "north_female_soft_1", "name": "Bảo Ngọc", "gender": "Nữ", "region": "Miền Bắc", "style": "Dịu dàng / Tâm sự", "base": "vi-VN-HoaiMyNeural", "pitch": "-8Hz", "rate": "-8%", "sample": "Hãy lắng nghe những giai điệu bình yên này."},
    {"id": "north_male_news_1", "name": "Minh Đức", "gender": "Nam", "region": "Miền Bắc", "style": "Bản tin / Trầm ấm", "base": "vi-VN-NamMinhNeural", "pitch": "+0Hz", "rate": "+0%", "sample": "Bản tin công nghệ hôm nay có những nội dung đáng chú ý."},
    {"id": "north_male_story_1", "name": "Hải Đăng", "gender": "Nam", "region": "Miền Bắc", "style": "Đọc truyện / Cuốn hút", "base": "vi-VN-NamMinhNeural", "pitch": "-6Hz", "rate": "-5%", "sample": "Bóng đêm dần buông xuống bao trùm toàn bộ cánh rừng."},
    {"id": "north_male_deep_1", "name": "Tuấn Anh", "gender": "Nam", "region": "Miền Bắc", "style": "Trầm mạnh / Tài liệu", "base": "vi-VN-NamMinhNeural", "pitch": "-12Hz", "rate": "-8%", "sample": "Lịch sử đã chứng kiến những bước ngoặt vĩ đại."},
    {"id": "north_male_natural_1", "name": "Quang Minh", "gender": "Nam", "region": "Miền Bắc", "style": "Năng động / Review", "base": "vi-VN-NamMinhNeural", "pitch": "+4Hz", "rate": "+6%", "sample": "Chào các bạn, hôm nay chúng ta cùng trên tay sản phẩm này."},

    # Miền Nam
    {"id": "south_female_gentle_1", "name": "Mỹ Linh", "gender": "Nữ", "region": "Miền Nam", "style": "Ngọt ngào / Dễ thương", "base": "vi-VN-HoaiMyNeural", "pitch": "+8Hz", "rate": "+2%", "sample": "Cảm ơn bạn đã luôn đồng hành cùng Xteam nha."},
    {"id": "south_female_news_1", "name": "Phương Thảo", "gender": "Nữ", "region": "Miền Nam", "style": "Thời sự / Rõ ràng", "base": "vi-VN-HoaiMyNeural", "pitch": "+2Hz", "rate": "+4%", "sample": "Bản tin chuyển động kinh tế phát sóng hàng ngày."},
    {"id": "south_female_story_1", "name": "Lan Hương", "gender": "Nữ", "region": "Miền Nam", "style": "Kể chuyện / Cảm xúc", "base": "vi-VN-HoaiMyNeural", "pitch": "-5Hz", "rate": "-4%", "sample": "Con đò nhỏ trôi nhẹ êm đềm trên dòng sông quê."},
    {"id": "south_female_podcast_1", "name": "Thanh Trúc", "gender": "Nữ", "region": "Miền Nam", "style": "Podcast / Trò chuyện", "base": "vi-VN-HoaiMyNeural", "pitch": "+4Hz", "rate": "+0%", "sample": "Chào mọi người đã quay trở lại với tập podcast hôm nay."},
    {"id": "south_male_news_1", "name": "Nam Khánh", "gender": "Nam", "region": "Miền Nam", "style": "Phát thanh / Đĩnh đạc", "base": "vi-VN-NamMinhNeural", "pitch": "+2Hz", "rate": "+2%", "sample": "Chào buổi sáng quý thính giả gần xa."},
    {"id": "south_male_natural_1", "name": "Gia Huy", "gender": "Nam", "region": "Miền Nam", "style": "Hào sảng / Thân thiện", "base": "vi-VN-NamMinhNeural", "pitch": "+6Hz", "rate": "+6%", "sample": "Bữa nay cùng mình khám phá những điều thú vị nghen."},
    {"id": "south_male_story_1", "name": "Quốc Bảo", "gender": "Nam", "region": "Miền Nam", "style": "Trầm / Đọc sách", "base": "vi-VN-NamMinhNeural", "pitch": "-8Hz", "rate": "-6%", "sample": "Mỗi trang sách mở ra là một chân trời mới."},
    {"id": "south_male_warm_1", "name": "Trung Dũng", "gender": "Nam", "region": "Miền Nam", "style": "Ấm áp / Chia sẻ", "base": "vi-VN-NamMinhNeural", "pitch": "-4Hz", "rate": "-2%", "sample": "Hy vọng bạn có một ngày thật nhiều niềm vui và may mắn."},

    # Miền Trung
    {"id": "central_female_soft_1", "name": "Hương Giang", "gender": "Nữ", "region": "Miền Trung", "style": "Nhẹ nhàng / Dịu êm", "base": "vi-VN-HoaiMyNeural", "pitch": "-2Hz", "rate": "-4%", "sample": "Dòng sông Hương êm đềm soi bóng cố đô cổ kính."},
    {"id": "central_female_news_1", "name": "Nhã Uyên", "gender": "Nữ", "region": "Miền Trung", "style": "Trang nhã / Rõ ràng", "base": "vi-VN-HoaiMyNeural", "pitch": "+3Hz", "rate": "+0%", "sample": "Thông tin phát triển du lịch miền Trung được cập nhật."},
    {"id": "central_female_story_1", "name": "Bích Trâm", "gender": "Nữ", "region": "Miền Trung", "style": "Kể chuyện / Lắng đọng", "base": "vi-VN-HoaiMyNeural", "pitch": "-6Hz", "rate": "-6%", "sample": "Những chiều mưa xứ Huế luôn mang một nét trầm mặc."},
    {"id": "central_male_deep_1", "name": "Bảo Long", "gender": "Nam", "region": "Miền Trung", "style": "Trầm ấm / Chuẩn mực", "base": "vi-VN-NamMinhNeural", "pitch": "-10Hz", "rate": "-4%", "sample": "Chào mừng bạn đến với vùng đất di sản văn hóa."},
    {"id": "central_male_warm_1", "name": "Thanh Tùng", "gender": "Nam", "region": "Miền Trung", "style": "Chân thành / Truyền cảm", "base": "vi-VN-NamMinhNeural", "pitch": "-4Hz", "rate": "+0%", "sample": "Mảnh đất miền Trung chan chứa tình người sâu nặng."},

    # Phong cách đặc biệt
    {"id": "sp_female_ai_1", "name": "X-Siri AI", "gender": "Nữ", "region": "Toàn quốc", "style": "Trợ lý ảo / Công nghệ", "base": "vi-VN-HoaiMyNeural", "pitch": "+12Hz", "rate": "+8%", "sample": "Tôi có thể hỗ trợ gì cho công việc của bạn hôm nay?"},
    {"id": "sp_male_doc_1", "name": "Hùng Cường", "gender": "Nam", "region": "Toàn quốc", "style": "Thuyết minh phim / Hùng tráng", "base": "vi-VN-NamMinhNeural", "pitch": "-14Hz", "rate": "-6%", "sample": "Cuộc hành trình vĩ đại bắt đầu từ những bước chân đầu tiên."},
    {"id": "sp_female_kids_1", "name": "Bé Mai", "gender": "Nữ", "region": "Toàn quốc", "style": "Thiếu nhi / Hoạt hình", "base": "vi-VN-HoaiMyNeural", "pitch": "+16Hz", "rate": "+10%", "sample": "Chào các bạn nhỏ, hôm nay chúng ta cùng học bài nhé!"},
    {"id": "sp_male_fast_1", "name": "Tiến Đạt", "gender": "Nam", "region": "Toàn quốc", "style": "Quảng cáo / Nhanh dứt khoát", "base": "vi-VN-NamMinhNeural", "pitch": "+6Hz", "rate": "+15%", "sample": "Cơ hội ưu đãi siêu lớn chỉ có duy nhất trong hôm nay!"}
]

def load_pronunciation_dict() -> Dict[str, str]:
    if DICT_FILE.exists():
        try:
            with open(DICT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_pronunciation_dict(data: Dict[str, str]):
    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def apply_pronunciation_dict(text: str, custom_dict: Optional[Dict[str, str]] = None) -> str:
    pdict = custom_dict or load_pronunciation_dict()
    if not pdict:
        return text
    for word, replacement in sorted(pdict.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        text = pattern.sub(replacement, text)
    return text

def preprocess_text_for_speech(raw_text: str) -> str:
    text = apply_pronunciation_dict(raw_text)
    text = re.sub(r'\[cười\]', '... haha ...', text, flags=re.IGNORECASE)
    text = re.sub(r'\[thở dài\]', '... phù ...', text, flags=re.IGNORECASE)
    text = re.sub(r'\[hắng giọng\]', '... hèm ...', text, flags=re.IGNORECASE)
    
    def pause_replace(m):
        return " ... "
    text = re.sub(r'\[nghỉ\s*[\d\.]+\s*(?:s|ms)?\]', pause_replace, text, flags=re.IGNORECASE)
    return text.strip()

async def synthesize_speech_edge(text: str, voice_id: str, speed: float = 1.0, output_path: Optional[Path] = None) -> bytes:
    all_known_voices = VOICES + SUPERTONIC_VOICES
    voice_info = next((v for v in all_known_voices if v["id"] == voice_id), VOICES[0])
    base_voice = voice_info.get("base", "vi-VN-HoaiMyNeural")
    pitch_offset = voice_info.get("pitch", "+0Hz")
    
    speed_pct = int(round((speed - 1.0) * 100))
    rate_str = f"{speed_pct:+d}%" if speed_pct != 0 else "+0%"
    
    clean_text = preprocess_text_for_speech(text)
    if not clean_text:
        clean_text = "Không có nội dung."
        
    communicate = edge_tts.Communicate(
        text=clean_text,
        voice=base_voice,
        rate=rate_str,
        pitch=pitch_offset
    )
    
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
            
    if output_path:
        with open(output_path, "wb") as f:
            f.write(audio_data)
            
    return bytes(audio_data)

def generate_srt_subtitles(text: str, speed: float = 1.0) -> str:
    sentences = re.split(r'(?<=[.!?\n])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    
    srt_lines = []
    curr_time = 0.0
    
    def fmt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"
    
    idx = 1
    for sent in sentences:
        words_count = len(sent.split())
        dur = max(1.2, words_count * 0.36) / max(0.5, min(speed, 2.0))
        
        start_fmt = fmt_time(curr_time)
        end_fmt = fmt_time(curr_time + dur)
        
        clean_sent = re.sub(r'\[.*?\]', '', sent).strip()
        if not clean_sent:
            clean_sent = sent
            
        srt_lines.append(f"{idx}\n{start_fmt} --> {end_fmt}\n{clean_sent}\n")
        curr_time += dur + 0.15
        idx += 1
        
    return "\n".join(srt_lines)


# ===================== SRT TIMED SPEECH =====================
import array
import wave

def _srt_time_to_sec(t: str) -> float:
    t = t.strip().replace(".", ",")
    hms, ms = t.split(",")
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0

def parse_srt(srt_text: str):
    """Tách file SRT thành danh sách (index, start, end, text)."""
    srt_text = srt_text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None:
            continue
        try:
            a, b = lines[ti].split("-->")
            start, end = _srt_time_to_sec(a), _srt_time_to_sec(b.split()[0])
        except Exception:
            continue
        text = " ".join(l.strip() for l in lines[ti + 1:])
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text and end > start:
            cues.append((len(cues) + 1, start, end, text))
    return cues

def _decode_mp3(mp3_bytes: bytes, rate: int = 24000):
    import miniaudio
    d = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16,
                         nchannels=1, sample_rate=rate)
    return d.samples  # array('h')

async def synthesize_srt_audio(srt_text: str, voice_id: str, speed: float, output_path: Path, fit: bool = True):
    """Đọc từng câu SRT, ép vừa khung thời gian, ghép thành 1 file WAV khớp mốc thời gian."""
    from . import vieneu_engine as vn
    use_vn = vn.is_vieneu_voice(voice_id)
    RATE = 48000 if use_vn else 24000
    cues = parse_srt(srt_text)
    if not cues:
        raise ValueError("File SRT không hợp lệ hoặc không có câu nào.")

    sem = asyncio.Semaphore(1 if use_vn else 4)

    async def render(text, spd):
        async with sem:
            if use_vn:
                pcm, sr = await asyncio.to_thread(vn.synth_pcm, text, voice_id, spd)
                if sr != RATE:
                    import numpy as np
                    idx = np.linspace(0, len(pcm) - 1, int(len(pcm) * RATE / sr))
                    pcm = np.interp(idx, np.arange(len(pcm)), pcm).astype(np.int16)
                return array.array("h", pcm.tobytes())
            data = await synthesize_speech_edge(text, voice_id, spd)
        return _decode_mp3(data, RATE)

    async def work(cue):
        _, start, end, text = cue
        target = end - start
        samples = await render(text, speed)
        dur = len(samples) / RATE
        if fit and dur > target * 1.02:
            new_speed = min(2.0 if not use_vn else 1.6, speed * dur / target)
            if new_speed > speed + 0.02:
                samples = await render(text, new_speed)
        return samples

    results = await asyncio.gather(*(work(c) for c in cues))

    out = array.array("h")
    cursor = 0  # vị trí hiện tại tính bằng mẫu
    drift = []
    for cue, samples in zip(cues, results):
        idx, start, end, _ = cue
        start_s = int(start * RATE)
        if start_s < cursor:
            if (cursor - start_s) / RATE > 0.25:
                drift.append(idx)
            start_s = cursor
        if start_s > cursor:
            out.extend(array.array("h", bytes((start_s - cursor) * 2)))
        out.extend(samples)
        cursor = start_s + len(samples)

    with wave.open(str(output_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())

    return {"cues": len(cues), "duration": round(cursor / RATE, 1), "late_cues": drift}


# ===================== CONVERSATION / MULTI-SPEAKER =====================
async def synthesize_conversation_audio(dialogues: List[Dict[str, Any]], pause_between: float, output_path: Path) -> Dict[str, Any]:
    """Tổng hợp kịch bản hội thoại nhiều nhân vật, mỗi nhân vật 1 giọng đọc và tốc độ riêng."""
    from . import vieneu_engine as vn
    RATE = 48000
    out = array.array("h")
    total_duration = 0.0
    turn_details = []

    for idx, turn in enumerate(dialogues):
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        voice_id = turn.get("voice_id", "north_male_news_1")
        speed = float(turn.get("speed", 1.0))
        speaker = turn.get("speaker") or f"Nhân vật {idx + 1}"

        use_vn = vn.is_vieneu_voice(voice_id)
        if use_vn:
            pcm, sr = await asyncio.to_thread(vn.synth_pcm, text, voice_id, speed)
            if sr != RATE:
                import numpy as np
                target_len = int(len(pcm) * RATE / sr)
                idx_arr = np.linspace(0, len(pcm) - 1, target_len)
                pcm = np.interp(idx_arr, np.arange(len(pcm)), pcm).astype(np.int16)
            samples = array.array("h", pcm.tobytes())
        else:
            mp3_data = await synthesize_speech_edge(text, voice_id, speed)
            samples = _decode_mp3(mp3_data, RATE)

        dur = len(samples) / RATE
        turn_details.append({
            "speaker": speaker,
            "text": text,
            "voice_id": voice_id,
            "duration": round(dur, 2)
        })

        out.extend(samples)
        total_duration += dur

        # Thêm khoảng lặng giữa các câu thoại (trừ câu cuối cùng)
        if idx < len(dialogues) - 1 and pause_between > 0:
            pause_samples = int(pause_between * RATE)
            out.extend(array.array("h", bytes(pause_samples * 2)))
            total_duration += pause_between

    with wave.open(str(output_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())

    return {
        "turns": len(turn_details),
        "duration": round(total_duration, 2),
        "turn_details": turn_details
    }


# ===================== TEXT CLEANING & FILE EXTRACTION =====================
def clean_text_spacing(text: str) -> str:
    """Loại bỏ khoảng trắng thừa, nối dòng gãy trong câu mà không làm hỏng công thức và dấu câu."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    joined = []
    curr = ""
    for line in lines:
        if not line:
            if curr:
                joined.append(curr)
                curr = ""
            joined.append("")
            continue
        if not curr:
            curr = line
        else:
            if curr[-1] in ".?!:;":
                joined.append(curr)
                curr = line
            else:
                curr = curr + " " + line
    if curr:
        joined.append(curr)

    result = "\n".join(joined)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Trích xuất văn bản từ tệp .txt, .pdf, .docx."""
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        for enc in ["utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"]:
            try:
                return file_bytes.decode(enc)
            except Exception:
                continue
        return file_bytes.decode("utf-8", errors="ignore")
    elif ext == ".pdf":
        import io
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                pages_text.append(txt.strip())
        return "\n\n".join(pages_text)
    elif ext in [".docx", ".doc"]:
        import io
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    else:
        raise ValueError(f"Định dạng tệp {ext} chưa được hỗ trợ. Hãy chọn file .txt, .pdf hoặc .docx")


