# Thông báo phần mềm bên thứ ba — Xteam Voice Studio

Xteam Voice Studio sử dụng các thành phần mã nguồn mở dưới đây. Mỗi thành phần giữ nguyên bản quyền và giấy phép của tác giả gốc.

## Thư viện LGPL

| Thành phần | Giấy phép | Mã nguồn |
|---|---|---|
| libsndfile (đọc/ghi WAV, MP3) | LGPL-2.1-or-later | https://github.com/libsndfile/libsndfile |
| LAME (bộ mã MP3, trong libsndfile) | LGPL-2.0-or-later | https://lame.sourceforge.io |
| mpg123 (bộ giải mã MP3, trong libsndfile) | LGPL-2.1 | https://www.mpg123.de |
| libsoxr (đổi tần số lấy mẫu, qua gói `soxr`) | LGPL-2.1-or-later | https://github.com/dofuuz/python-soxr |

## Mô hình AI cốt lõi

| Mô hình | Giấy phép | Nguồn |
|---|---|---|
| VieNeu-TTS v3 Turbo (ONNX int8) | Apache-2.0 | https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo |
| MOSS Audio Tokenizer Nano (ONNX) | Apache-2.0 | https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX |

## Các thư viện khác

Ứng dụng sử dụng các thư viện mã nguồn mở theo giấy phép MIT, BSD, Apache-2.0, tiêu biểu như: Python, FastAPI, Uvicorn, ONNX Runtime, React, Tailwind CSS, Lucide Icons. Bản quyền thuộc tác giả của từng thư viện.
