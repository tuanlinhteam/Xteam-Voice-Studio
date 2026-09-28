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
    voice_info = next((v for v in VOICES if v["id"] == voice_id), VOICES[0])
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
