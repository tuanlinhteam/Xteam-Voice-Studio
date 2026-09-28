let voices = [];
let selectedVoiceId = "north_male_news_1";
let dictionary = {};
let currentPreviewAudio = null;
let currentPreviewBtn = null;

let currentLicense = null;

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  fetchVoices();
  setupTextareaStats();
  loadHistory();
  loadDictionary();
  checkLicenseStatus(false);
});

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(el => {
    el.classList.remove("bg-brand-600", "text-white", "shadow-sm");
    el.classList.add("text-slate-400");
  });

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetTab && targetNav) {
    targetTab.classList.remove("hidden");
    targetNav.classList.remove("text-slate-400");
    targetNav.classList.add("bg-brand-600", "text-white", "shadow-sm");
  }
  lucide.createIcons();
}

// Fetch Voices List
async function fetchVoices() {
  try {
    const res = await fetch("/voices");
    const data = await res.json();
    if (data.voices) {
      voices = data.voices;
      renderVoices("all");
    }
  } catch (err) {
    console.error("Lỗi tải danh sách giọng:", err);
  }
}

// Render Voice Cards with both Preview and Stop buttons
function renderVoices(filterRegion) {
  const container = document.getElementById("voices-list");
  container.innerHTML = "";

  const filtered = filterRegion === "all" ? voices : voices.filter(v => v.region === filterRegion);

  filtered.forEach(v => {
    const isSelected = v.id === selectedVoiceId;
    const card = document.createElement("div");
    card.className = `p-3 rounded-xl border cursor-pointer transition flex items-center justify-between gap-2 ${
      isSelected 
        ? "bg-brand-950/60 border-brand-500 shadow-md shadow-brand-500/10" 
        : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
    }`;
    card.onclick = () => selectVoice(v.id);

    card.innerHTML = `
      <div class="flex items-center space-x-3 overflow-hidden">
        <div class="w-8 h-8 rounded-lg flex-shrink-0 ${v.gender === 'Nữ' ? 'bg-pink-950/80 text-pink-400 border border-pink-800/40' : 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'} flex items-center justify-center font-bold text-xs">
          ${v.gender === 'Nữ' ? '♀' : '♂'}
        </div>
        <div class="truncate">
          <div class="flex items-center space-x-2">
            <span class="text-sm font-semibold text-white truncate">${v.name}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 flex-shrink-0">${v.region}</span>
          </div>
          <p class="text-[11px] text-slate-400 truncate">${v.style}</p>
        </div>
      </div>

      <!-- Action Buttons: Thử & Dừng -->
      <div class="flex items-center space-x-1.5 flex-shrink-0">
        <button id="preview-btn-${v.id}" onclick="event.stopPropagation(); playVoicePreview('${v.id}')" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-brand-600 text-slate-300 hover:text-white transition flex items-center space-x-1 text-xs" title="Nghe thử giọng này">
          <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
          <span>Thử</span>
        </button>
        <button id="stop-btn-${v.id}" onclick="event.stopPropagation(); stopVoicePreview('${v.id}')" class="px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-red-600/80 text-slate-400 hover:text-white transition flex items-center space-x-1 text-xs" title="Dừng phát giọng này">
          <i data-lucide="square" class="w-3 h-3 fill-current"></i>
          <span>Dừng</span>
        </button>
      </div>
    `;
    container.appendChild(card);
  });
  lucide.createIcons();
}

function filterVoices(region) {
  document.querySelectorAll(".voice-filter-btn").forEach(btn => {
    if (btn.getAttribute("data-region") === region) {
      btn.className = "voice-filter-btn px-2.5 py-1 text-xs rounded-lg font-medium bg-brand-600 text-white";
    } else {
      btn.className = "voice-filter-btn px-2.5 py-1 text-xs rounded-lg font-medium bg-slate-800 text-slate-300 hover:bg-slate-700";
    }
  });
  renderVoices(region);
}

function selectVoice(id) {
  selectedVoiceId = id;
  const currentFilter = document.querySelector(".voice-filter-btn.bg-brand-600")?.getAttribute("data-region") || "all";
  renderVoices(currentFilter);
}

// Voice Preview with live animation and reliable audio playback
async function playVoicePreview(id) {
  const btn = document.getElementById(`preview-btn-${id}`);
  
  // Stop any currently playing audio
  stopCurrentPreview();

  if (btn) {
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-brand-400"></i><span>...</span>`;
    btn.classList.add("bg-brand-950", "text-brand-300");
    lucide.createIcons();
  }

  try {
    const audioUrl = `/api/tts/preview?voice_id=${id}&t=${Date.now()}`;
    const audio = new Audio(audioUrl);
    currentPreviewAudio = audio;
    currentPreviewBtn = btn;

    audio.oncanplaythrough = () => {
      if (btn && currentPreviewAudio === audio) {
        btn.innerHTML = `<i data-lucide="volume-2" class="w-3.5 h-3.5"></i><span>Đang phát</span>`;
        btn.classList.remove("bg-brand-950");
        btn.classList.add("bg-brand-600", "text-white");
        lucide.createIcons();
      }
      audio.play().catch(e => console.warn(e));
    };

    audio.onended = () => {
      stopCurrentPreview();
    };

    audio.onerror = () => {
      stopCurrentPreview();
      if (btn) {
        btn.innerHTML = `<i data-lucide="volume-x" class="w-3.5 h-3.5 text-red-400"></i><span>Thử lại</span>`;
        lucide.createIcons();
      }
    };

  } catch (err) {
    stopCurrentPreview();
  }
}

// Stop preview function
function stopVoicePreview(id) {
  stopCurrentPreview();
}

function stopCurrentPreview() {
  if (currentPreviewAudio) {
    currentPreviewAudio.pause();
    currentPreviewAudio.currentTime = 0;
    currentPreviewAudio = null;
  }
  if (currentPreviewBtn) {
    currentPreviewBtn.innerHTML = `<i data-lucide="volume-2" class="w-3.5 h-3.5"></i><span>Thử</span>`;
    currentPreviewBtn.classList.remove("bg-brand-600", "text-white", "bg-brand-950", "text-brand-300");
    currentPreviewBtn.classList.add("bg-slate-800", "text-slate-300");
    currentPreviewBtn = null;
    lucide.createIcons();
  }
}

// Textarea Stats & Helpers
function setupTextareaStats() {
  const textarea = document.getElementById("tts-input");
  if (textarea) {
    textarea.addEventListener("input", updateStats);
  }
}

function updateStats() {
  const text = document.getElementById("tts-input").value;
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  
  const speed = parseFloat(document.getElementById("speed-slider")?.value || 1.0);
  const seconds = Math.round((words / 2.5) / speed);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const durationStr = `~${mins}:${secs < 10 ? '0' : ''}${secs} audio`;

  document.getElementById("char-count").innerText = `${chars.toLocaleString()} ký tự`;
  document.getElementById("word-count").innerText = `${words.toLocaleString()} từ`;
  document.getElementById("est-duration").innerText = durationStr;
}

function insertTag(tag) {
  const textarea = document.getElementById("tts-input");
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;
  textarea.value = val.substring(0, start) + " " + tag + " " + val.substring(end);
  textarea.focus();
  textarea.selectionStart = textarea.selectionEnd = start + tag.length + 2;
  updateStats();
}

function cleanText() {
  const textarea = document.getElementById("tts-input");
  let text = textarea.value;
  text = text.replace(/[\r\n]+/g, "\n");
  text = text.replace(/^[•\-\*]\s+/gm, "");
  text = text.replace(/[ \t]+/g, " ");
  textarea.value = text.trim();
  updateStats();
}

function handleFileImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (event) => {
    document.getElementById("tts-input").value = event.target.result;
    updateStats();
  };
  reader.readAsText(file);
}

// Main Audio Generation
async function generateAudio() {
  const text = document.getElementById("tts-input").value.trim();
  if (!text) {
    alert("Vui lòng nhập văn bản cần chuyển thành giọng nói!");
    return;
  }

  // Stop any playing preview
  stopCurrentPreview();

  const btn = document.getElementById("btn-generate");
  const origContent = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i><span>Đang tổng hợp giọng nói AI...</span>`;
  lucide.createIcons();

  const speed = parseFloat(document.getElementById("speed-slider").value);
  const includeSubtitles = document.getElementById("include-srt").checked;

  try {
    const res = await fetch("/api/tts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        voice_id: selectedVoiceId,
        speed,
        include_subtitles: includeSubtitles
      })
    });

    const data = await res.json();
    if (data.success) {
      const resultBox = document.getElementById("result-box");
      const player = document.getElementById("audio-player");
      const downloadWav = document.getElementById("download-wav-btn");
      const downloadSrt = document.getElementById("download-srt-btn");
      const resultSize = document.getElementById("result-size");

      player.src = data.audio_url;
      player.play();

      downloadWav.href = data.audio_url;
      downloadWav.innerText = "Tải File MP3";
      if (data.srt_url) {
        downloadSrt.href = data.srt_url;
        downloadSrt.classList.remove("hidden");
      } else {
        downloadSrt.classList.add("hidden");
      }

      resultSize.innerText = `${data.size_kb} KB`;
      resultBox.classList.remove("hidden");
      loadHistory();
    } else {
      alert("Không thể tạo giọng nói: " + (data.detail || "Lỗi không xác định"));
    }
  } catch (err) {
    alert("Lỗi kết nối máy chủ TTS: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = origContent;
    lucide.createIcons();
  }
}

// History Management
async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    const container = document.getElementById("history-list");
    if (!container) return;
    container.innerHTML = "";

    if (!data.history || data.history.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-500 text-xs">Chưa có lịch sử tạo giọng. Các file bạn tạo sẽ hiển thị ở đây.</div>`;
      return;
    }

    data.history.forEach(item => {
      const div = document.createElement("div");
      div.className = "p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3";
      div.innerHTML = `
        <div class="flex-1">
          <div class="flex items-center space-x-2 mb-1">
            <span class="text-xs font-bold text-brand-400">${item.created_at}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${item.size_kb} KB</span>
          </div>
          <p class="text-sm text-slate-200 line-clamp-1">${item.text}</p>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="new Audio('/api/audio/${item.filename}').play()" class="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold transition flex items-center space-x-1">
            <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
            <span>Nghe</span>
          </button>
          <a href="/api/audio/${item.filename}" download class="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition" title="Tải Audio">
            <i data-lucide="download" class="w-4 h-4"></i>
          </a>
          <button onclick="deleteHistory('${item.id}')" class="p-2 bg-slate-800 hover:bg-red-600/80 text-slate-400 hover:text-white rounded-lg transition" title="Xóa">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      `;
      container.appendChild(div);
    });
    lucide.createIcons();
  } catch (e) {}
}

async function deleteHistory(id) {
  if (!confirm("Bạn có chắc muốn xóa bản ghi này?")) return;
  await fetch(`/api/history/${id}`, { method: "DELETE" });
  loadHistory();
}

// Dictionary Modal & API
async function loadDictionary() {
  try {
    const res = await fetch("/api/dictionary");
    const data = await res.json();
    dictionary = data.dictionary || {};
    renderDictionary();
  } catch (e) {}
}

function renderDictionary() {
  const container = document.getElementById("dict-list");
  if (!container) return;
  container.innerHTML = "";

  const entries = Object.entries(dictionary);
  if (entries.length === 0) {
    container.innerHTML = `<div class="p-3 text-center text-xs text-slate-500">Chưa có từ nào trong từ điển.</div>`;
    return;
  }

  entries.forEach(([word, read]) => {
    const div = document.createElement("div");
    div.className = "flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800 text-xs";
    div.innerHTML = `
      <div>
        <span class="font-bold text-white">${word}</span>
        <span class="text-slate-400 mx-1">→</span>
        <span class="text-brand-300 font-medium">"${read}"</span>
      </div>
      <button onclick="removeDictEntry('${word}')" class="text-slate-500 hover:text-red-400">
        <i data-lucide="trash" class="w-3.5 h-3.5"></i>
      </button>
    `;
    container.appendChild(div);
  });
  lucide.createIcons();
}

function openDictModal() {
  document.getElementById("dict-modal").classList.remove("hidden");
  renderDictionary();
}

function closeDictModal() {
  document.getElementById("dict-modal").classList.add("hidden");
}

async function addDictEntry() {
  const word = document.getElementById("dict-word").value.trim();
  const read = document.getElementById("dict-read").value.trim();
  if (!word || !read) return;

  dictionary[word] = read;
  await fetch("/api/dictionary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dictionary)
  });

  document.getElementById("dict-word").value = "";
  document.getElementById("dict-read").value = "";
  renderDictionary();
}

async function removeDictEntry(word) {
  delete dictionary[word];
  await fetch("/api/dictionary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dictionary)
  });
  renderDictionary();
}

// License Verification & Management
async function checkLicenseStatus(showAlert = false) {
  const dot = document.getElementById("lic-dot");
  const text = document.getElementById("lic-text");

  try {
    const res = await fetch("/api/license/status");
    const data = await res.json();
    currentLicense = data;

    // Update Modal
    document.getElementById("modal-hwid").innerText = data.hwid || "Không xác định";
    document.getElementById("modal-customer-name").innerText = data.customer_name || "Chưa kích hoạt";
    document.getElementById("modal-expires-at").innerText = data.expires_at || "Chưa kích hoạt";
    document.getElementById("modal-days-left").innerText = data.is_active ? `${data.days_left} ngày` : "0 ngày";

    const badge = document.getElementById("modal-status-badge");
    if (data.is_active) {
      badge.className = "font-bold px-2 py-0.5 rounded bg-brand-500/20 text-brand-400 border border-brand-500/30";
      badge.innerText = "Đã kích hoạt (VIP)";

      // Update Header
      if (dot && text) {
        dot.className = "w-2 h-2 rounded-full bg-brand-400";
        text.className = "text-brand-300 font-semibold";
        text.innerText = `${data.customer_name} (${data.days_left} ngày)`;
      }

      if (showAlert) {
        alert(`Bản quyền của bạn hợp lệ!\nTên: ${data.customer_name}\nThời hạn: ${data.expires_at} (Còn ${data.days_left} ngày)`);
      }
    } else {
      badge.className = "font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30";
      badge.innerText = "Chưa kích hoạt / Hết hạn";

      // Update Header
      if (dot && text) {
        dot.className = "w-2 h-2 rounded-full bg-red-400 animate-ping";
        text.className = "text-red-400 font-semibold";
        text.innerText = "Chưa kích hoạt";
      }

      if (showAlert) {
        alert(`Mã máy ${data.hwid} chưa được kích hoạt hoặc đã hết hạn!\nVui lòng sao chép mã máy và gửi Admin Xteam.`);
      } else {
        // Auto open license modal on first startup if inactive
        openLicenseModal();
      }
    }
  } catch (err) {
    console.error("Lỗi kiểm tra bản quyền:", err);
  }
}

function openLicenseModal() {
  document.getElementById("license-modal").classList.remove("hidden");
  lucide.createIcons();
}

function closeLicenseModal() {
  document.getElementById("license-modal").classList.add("hidden");
}

function copyMachineId() {
  const hwid = document.getElementById("modal-hwid").innerText;
  navigator.clipboard.writeText(hwid).then(() => {
    const btnText = document.getElementById("copy-btn-text");
    btnText.innerText = "Đã chép!";
    setTimeout(() => { btnText.innerText = "Sao chép"; }, 2000);
  }).catch(() => {
    alert("Mã máy của bạn là: " + hwid);
  });
}

