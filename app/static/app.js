let voices = [];
let selectedVoiceId = localStorage.getItem("xteam_voice_id") || "st:M2";
let dictionary = {};
let currentPreviewAudio = null;
let currentPreviewBtn = null;
let currentPreviewVoiceId = null;
let currentEngine = localStorage.getItem("xteam_engine") || "supertonic";
let vieneuInfo = { state: "idle", installed: true, message: "" };
let vieneuPoll = null;
let cloneFile = null;
const jsq = (s) => String(s).replace(/\\/g, "\\\\").replace(/'/g, "\\'");

let currentLicense = null;

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  updateEngineButtons();
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
    el.classList.remove("bg-teal-600", "text-white", "shadow-sm");
    el.classList.add("text-slate-400");
  });

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetTab && targetNav) {
    targetTab.classList.remove("hidden");
    targetNav.classList.remove("text-slate-400");
    targetNav.classList.add("bg-teal-600", "text-white", "shadow-sm");
  }
  lucide.createIcons();
}

// Fetch Voices List
async function fetchVoices() {
  try {
    const res = await fetch("/voices");
    const data = await res.json();
    if (data.vieneu) vieneuInfo = data.vieneu;
    if (data.active_model) {
      if (!localStorage.getItem("xteam_engine")) {
        currentEngine = (data.active_model === "supertonic_3") ? "supertonic" : "vieneu";
      }
      updateEngineButtons();
      updateVieneuBanner();
    }
    if (data.voices) {
      voices = data.voices;
      if (!selectedVoiceId || !voices.some(v => v.id === selectedVoiceId)) {
        selectedVoiceId = "st:M2";
      }
      populateVoiceDropdowns();
      selectVoice(selectedVoiceId);
      renderVoices(document.querySelector(".voice-filter-btn.bg-teal-600")?.getAttribute("data-region") || "all");
      updateVieneuBanner();
      if (typeof renderConversationRows === "function") {
        renderConversationRows();
      }
    }
  } catch (err) {
    console.error("Lỗi tải danh sách giọng:", err);
  }
}

// Render Voice Cards with clean, smart single preview toggle
function renderVoices(filterRegion) {
  const container = document.getElementById("voices-list");
  if (!container) return;
  container.innerHTML = "";

  let filtered = voices.filter(v => {
    if (currentEngine === "supertonic") return v.engine === "supertonic";
    if (currentEngine === "vieneu") return v.engine === "vieneu" || v.is_cloned;
    return (v.engine || "edge") === "edge" && !v.is_cloned;
  });
  if (filterRegion !== "all" && currentEngine !== "supertonic") {
    filtered = filtered.filter(v => v.region === filterRegion || v.is_cloned);
  }
  filtered.sort((a, b) => (b.is_cloned ? 1 : 0) - (a.is_cloned ? 1 : 0));
  if (!filtered.length) {
    container.innerHTML = `<div class="p-5 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800/80">${currentEngine === "vieneu" ? "Chưa có giọng. Hãy bật VieNeu-TTS ở khung phía trên." : "Không có giọng phù hợp."}</div>`;
    return;
  }

  filtered.forEach(v => {
    const isSelected = v.id === selectedVoiceId;
    const isPlaying = (currentPreviewAudio && currentPreviewVoiceId === v.id);
    const card = document.createElement("div");
    card.className = `p-2.5 rounded-xl border cursor-pointer transition flex items-center justify-between gap-3 ${
      isSelected 
        ? "bg-teal-950/40 border-teal-500 shadow-md shadow-teal-900/20 ring-1 ring-teal-500/40" 
        : "bg-slate-950/50 border-slate-800/90 hover:border-slate-700 hover:bg-slate-900/60"
    }`;
    card.onclick = () => selectVoice(v.id);

    card.innerHTML = `
      <div class="flex items-center space-x-3 overflow-hidden min-w-0">
        <div class="w-8 h-8 rounded-lg flex-shrink-0 ${v.gender === 'Nữ' ? 'bg-pink-950/70 text-pink-400 border border-pink-800/40' : 'bg-teal-950/70 text-teal-400 border border-teal-800/40'} flex items-center justify-center font-bold text-xs shadow-inner">
          ${v.gender === 'Nữ' ? '♀' : '♂'}
        </div>
        <div class="truncate">
          <div class="flex items-center space-x-1.5">
            <span class="text-xs sm:text-sm font-bold text-white truncate">${v.name}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 flex-shrink-0 font-medium">${v.region}</span>
            ${isSelected ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30 font-bold flex-shrink-0">✓ Đang dùng</span>' : ''}
          </div>
          <p class="text-[11px] text-slate-400 truncate mt-0.5">${v.style}</p>
        </div>
      </div>

      <!-- Action Button: Nghe Thử / Dừng 1 nút thông minh gọn gàng -->
      <div class="flex items-center space-x-1 flex-shrink-0">
        <button id="preview-btn-${v.id}" onclick="event.stopPropagation(); playVoicePreview('${jsq(v.id)}')" class="px-2.5 py-1.5 rounded-lg ${isPlaying ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse' : 'bg-slate-800/90 hover:bg-teal-600 text-slate-300 hover:text-white border border-slate-700/80'} transition flex items-center space-x-1 text-xs font-semibold shadow-sm" title="${isPlaying ? 'Dừng phát' : 'Nghe thử giọng này'}">
          <i data-lucide="${isPlaying ? 'square' : 'volume-2'}" class="w-3.5 h-3.5 ${isPlaying ? 'fill-current' : ''}"></i>
          <span>${isPlaying ? 'Dừng' : 'Thử'}</span>
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
      btn.className = "voice-filter-btn px-3 py-1 text-xs rounded-lg font-semibold bg-teal-600 text-white shadow-sm";
    } else {
      btn.className = "voice-filter-btn px-2.5 py-1 text-xs rounded-lg font-medium bg-slate-800/80 text-slate-300 hover:bg-slate-700";
    }
  });
  renderVoices(region);
}

function selectVoice(id) {
  selectedVoiceId = id;
  try { localStorage.setItem("xteam_voice_id", id); } catch (e) {}

  const v = voices.find(x => x.id === id);
  if (v) {
    const targetEngine = v.is_cloned ? "vieneu" : (v.engine || "edge");
    if (targetEngine !== currentEngine) {
      currentEngine = targetEngine;
      try { localStorage.setItem("xteam_engine", targetEngine); } catch (e) {}
      updateEngineButtons();
    }
  }

  const currentFilter = document.querySelector(".voice-filter-btn.bg-teal-600")?.getAttribute("data-region") || "all";
  renderVoices(currentFilter);

  const srtSelect = document.getElementById("srt-voice-select");
  if (srtSelect && srtSelect.value !== id) srtSelect.value = id;
  const batchSelect = document.getElementById("batch-voice-select");
  if (batchSelect && batchSelect.value !== id) batchSelect.value = id;
}

function populateVoiceDropdowns() {
  const srtSelect = document.getElementById("srt-voice-select");
  const batchSelect = document.getElementById("batch-voice-select");
  if (!srtSelect && !batchSelect) return;

  const grouped = {
    supertonic: { label: "🌟 Supertonic 3 (Quốc tế & Đa ngôn ngữ)", voices: [] },
    vieneu: { label: "🤖 VieNeu-TTS (Việt Nam AI)", voices: [] },
    edge: { label: "⚡ Edge-TTS (Tiếng Việt 3 Miền)", voices: [] },
    cloned: { label: "✨ Giọng nhân bản", voices: [] }
  };

  voices.forEach(v => {
    if (v.is_cloned) grouped.cloned.voices.push(v);
    else if (v.engine === "supertonic") grouped.supertonic.voices.push(v);
    else if (v.engine === "vieneu") grouped.vieneu.voices.push(v);
    else grouped.edge.voices.push(v);
  });

  let optionsHtml = "";
  for (const [key, grp] of Object.entries(grouped)) {
    if (grp.voices.length > 0) {
      optionsHtml += `<optgroup label="${grp.label}" class="bg-slate-900 text-teal-400 font-bold">`;
      grp.voices.forEach(v => {
        const isWatson = (v.id === "st:M2");
        const note = isWatson ? " (Mặc định)" : "";
        optionsHtml += `<option value="${v.id}" class="bg-slate-950 text-slate-100 font-medium">${v.name} - ${v.region} [${v.gender}]${note}</option>`;
      });
      optionsHtml += `</optgroup>`;
    }
  }

  if (srtSelect) {
    srtSelect.innerHTML = optionsHtml;
    srtSelect.value = selectedVoiceId;
  }
  if (batchSelect) {
    batchSelect.innerHTML = optionsHtml;
    batchSelect.value = selectedVoiceId;
  }
}

function onVoiceSelectChange(val) {
  selectVoice(val);
}

// Voice Preview with live animation and reliable audio playback
async function playVoicePreview(id) {
  if (currentPreviewVoiceId === id && currentPreviewAudio) {
    stopCurrentPreview();
    return;
  }

  stopCurrentPreview();

  const btn = document.getElementById(`preview-btn-${id}`);
  currentPreviewVoiceId = id;
  currentPreviewBtn = btn;

  if (btn) {
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-teal-400"></i><span>...</span>`;
    btn.className = "px-2.5 py-1.5 rounded-lg bg-teal-950 text-teal-300 border border-teal-700/80 transition flex items-center space-x-1 text-xs font-semibold shadow-sm";
    lucide.createIcons();
  }

  try {
    const audioUrl = `/api/tts/preview?voice_id=${encodeURIComponent(id)}&t=${Date.now()}`;
    const audio = new Audio(audioUrl);
    currentPreviewAudio = audio;

    audio.oncanplaythrough = () => {
      if (btn && currentPreviewAudio === audio) {
        btn.innerHTML = `<i data-lucide="square" class="w-3 h-3 fill-current"></i><span>Dừng</span>`;
        btn.className = "px-2.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition flex items-center space-x-1 text-xs font-semibold shadow-md animate-pulse";
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
        btn.innerHTML = `<i data-lucide="volume-x" class="w-3.5 h-3.5 text-rose-400"></i><span>Lỗi</span>`;
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
    currentPreviewBtn.className = "px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-teal-600 text-slate-300 hover:text-white border border-slate-700/80 transition flex items-center space-x-1 text-xs font-semibold shadow-sm";
    currentPreviewBtn = null;
    lucide.createIcons();
  }
  currentPreviewVoiceId = null;
}

function setSpeedPreset(val) {
  const slider = document.getElementById("speed-slider");
  if (slider) {
    slider.value = val;
    const disp = document.getElementById("speed-val");
    if (disp) disp.innerText = Number(val).toFixed(2) + "x";
    updateStats();
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

async function cleanText() {
  const textarea = document.getElementById("tts-input");
  let text = textarea.value;
  if (!text.trim()) return;

  try {
    const res = await fetch("/api/utils/clean-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text })
    });
    const data = await res.json();
    if (data.success) {
      textarea.value = data.cleaned_text;
      updateStats();
      showToast("Đã làm sạch văn bản và nối dòng thông minh!", "success");
      return;
    }
  } catch (e) {
    // Fallback local clean
  }

  text = text.replace(/[\r\n]+/g, "\n");
  text = text.replace(/^[•\-\*]\s+/gm, "");
  text = text.replace(/[ \t]+/g, " ");
  textarea.value = text.trim();
  updateStats();
  showToast("Đã làm sạch văn bản!", "success");
}

async function handleFileImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const ext = file.name.split(".").pop().toLowerCase();

  if (ext === "docx" || ext === "pdf" || ext === "doc") {
    showToast(`Đang trích xuất văn bản từ tệp ${file.name}...`, "info");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/utils/extract-text", { method: "POST", body: fd });
      const data = await res.json();
      if (res.ok && data.success) {
        document.getElementById("tts-input").value = data.text;
        updateStats();
        showToast(`Đã nạp ${data.chars} ký tự từ file ${file.name}!`, "success");
      } else {
        showToast("Lỗi đọc file: " + (data.detail || "Không đọc được"), "error");
      }
    } catch (err) {
      showToast("Lỗi trích xuất: " + err.message, "error");
    }
  } else {
    const reader = new FileReader();
    reader.onload = (event) => {
      document.getElementById("tts-input").value = event.target.result;
      updateStats();
      showToast(`Đã nạp file ${file.name}!`, "success");
    };
    reader.readAsText(file, "UTF-8");
  }
  e.target.value = "";
}

// Download Handlers (Hỗ trợ 100% Native WebView & Trình duyệt)
let currentGeneratedAudio = null;
let currentGeneratedSrt = null;

async function triggerFileDownload(url, filename) {
  try {
    const res = await fetch(url + (url.includes("?") ? "&" : "?") + "download=true");
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = blobUrl;
    a.download = filename || url.split("/").pop().split("?")[0];
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      window.URL.revokeObjectURL(blobUrl);
      a.remove();
    }, 1000);
  } catch (e) {
    window.location.href = url + (url.includes("?") ? "&" : "?") + "download=true";
  }
}

async function downloadCurrentMp3() {
  if (!currentGeneratedAudio) return;
  triggerFileDownload(`/api/audio/${currentGeneratedAudio}`, currentGeneratedAudio);
  
  try {
    await fetch(`/api/audio/save-to-downloads/${currentGeneratedAudio}`, { method: "POST" });
    showActivationToast(`✅ Đã lưu file ${currentGeneratedAudio} vào thư mục Downloads của bạn!`);
  } catch (e) {}
}

async function downloadCurrentSrt() {
  if (!currentGeneratedSrt) return;
  triggerFileDownload(`/api/audio/${currentGeneratedSrt}`, currentGeneratedSrt);
  showActivationToast(`✅ Đã tải file phụ đề ${currentGeneratedSrt}!`);
}

async function downloadAudioItem(filename) {
  triggerFileDownload(`/api/audio/${filename}`, filename);
  try {
    await fetch(`/api/audio/save-to-downloads/${filename}`, { method: "POST" });
    showActivationToast(`✅ Đã lưu ${filename} vào thư mục Downloads!`);
  } catch (e) {}
}

async function openDownloadsFolder() {
  try {
    await fetch("/api/open-downloads-folder");
  } catch (e) {}
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
      currentGeneratedAudio = data.filename;
      currentGeneratedSrt = data.metadata ? data.metadata.srt_filename : null;

      const resultBox = document.getElementById("result-box");
      const player = document.getElementById("audio-player");
      const downloadSrt = document.getElementById("download-srt-btn");
      const resultSize = document.getElementById("result-size");

      player.src = data.audio_url;
      player.play();

      if (data.srt_url) {
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
          <button onclick="downloadAudioItem('${item.filename}')" class="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition" title="Tải Audio / Lưu Downloads">
            <i data-lucide="download" class="w-4 h-4"></i>
          </button>
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

function downloadDictTemplate() {
  window.open("/api/dictionary/template.csv", "_blank");
}

function exportDictCSV() {
  window.open("/api/dictionary/export.csv", "_blank");
}

async function importDictCSV(e) {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch("/api/dictionary/import", { method: "POST", body: fd });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Đã nhập ${data.imported_count} từ từ điển! (Bỏ qua ${data.skipped_count} dòng)`, "success");
      fetchDictionary();
    } else {
      showToast("Lỗi nhập CSV: " + (data.detail || "Không nhập được"), "error");
    }
  } catch (err) {
    showToast("Lỗi tải tệp: " + err.message, "error");
  }
  e.target.value = "";
}

// License Verification & Real-time Auto-Sync
let licensePollInterval = null;

async function checkLicenseStatus(showAlert = false, isAuto = false) {
  const dot = document.getElementById("lic-dot");
  const text = document.getElementById("lic-text");

  try {
    const res = await fetch("/api/license/status");
    const data = await res.json();
    const wasInactive = currentLicense ? !currentLicense.is_active : true;
    currentLicense = data;

    // Update Modal / Settings Tab
    const mHwid = document.getElementById("modal-hwid");
    const mCust = document.getElementById("modal-customer-name");
    const mExp = document.getElementById("modal-expires-at");
    const mDays = document.getElementById("modal-days-left");
    const badge = document.getElementById("modal-status-badge");

    if (mHwid) mHwid.innerText = data.hwid || "Không xác định";
    if (mCust) mCust.innerText = data.customer_name || "Chưa kích hoạt";
    if (mExp) mExp.innerText = data.expires_at || "Chưa kích hoạt";
    if (mDays) mDays.innerText = data.is_active ? `${data.days_left} ngày` : "0 ngày";

    // Header badges
    const hCust = document.getElementById("header-customer-name");
    const hExp = document.getElementById("header-expires-at");
    const hDays = document.getElementById("header-days-left");
    if (hCust) hCust.innerText = data.customer_name || "Chưa kích hoạt";
    if (hExp) hExp.innerText = data.expires_at || "Chưa kích hoạt";
    if (hDays) {
      if (data.is_active) {
        hDays.innerText = `${data.days_left} ngày`;
        hDays.className = "text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 font-bold border border-emerald-500/30";
      } else {
        hDays.innerText = "0 ngày";
        hDays.className = "text-[10px] px-1.5 py-0.2 rounded bg-red-500/15 text-red-300 font-bold border border-red-500/30";
      }
    }

    if (data.is_active) {
      if (badge) {
        badge.className = "font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
        badge.innerText = "Đã kích hoạt (VIP)";
      }

      if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-400";
      if (text) {
        text.className = "text-emerald-300 font-semibold";
        text.innerText = `${data.customer_name} (${data.days_left} ngày)`;
      }

      // Realtime auto-unlock trigger
      if (wasInactive && isAuto) {
        closeLicenseModal();
        showActivationToast(`🎉 Chúc mừng ${data.customer_name}! Bản quyền của bạn đã được kích hoạt thành công (Hạn: ${data.expires_at})`);
      } else if (showAlert) {
        alert(`Bản quyền của bạn hợp lệ!\nTên: ${data.customer_name}\nThời hạn: ${data.expires_at} (Còn ${data.days_left} ngày)`);
      }

      resetPolling(120000); // 2 phút kiểm tra 1 lần khi đã kích hoạt
    } else {
      if (badge) {
        badge.className = "font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30";
        badge.innerText = "Chưa kích hoạt / Hết hạn";
      }

      if (dot) dot.className = "w-2 h-2 rounded-full bg-red-400 animate-ping";
      if (text) {
        text.className = "text-red-400 font-semibold";
        text.innerText = "Chưa kích hoạt";
      }

      if (showAlert) {
        alert(`Mã máy ${data.hwid} chưa được kích hoạt hoặc đã hết hạn!\nVui lòng sao chép mã máy và gửi Admin Xteam.`);
      } else if (!isAuto) {
        openLicenseModal();
      }

      resetPolling(3000); // Đang chờ kích hoạt: tự động kiểm tra mỗi 3 giây
    }
  } catch (err) {
    console.error("Lỗi kiểm tra bản quyền:", err);
  }
}

function resetPolling(intervalMs) {
  if (licensePollInterval) clearInterval(licensePollInterval);
  licensePollInterval = setInterval(() => {
    checkLicenseStatus(false, true);
  }, intervalMs);
}

function showActivationToast(msg) {
  showToast(msg, "success");
}

function showToast(msg, type = "info") {
  let toastContainer = document.getElementById("studio-toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "studio-toast-container";
    toastContainer.className = "fixed bottom-5 right-5 z-[9999] flex flex-col space-y-2 pointer-events-none max-w-sm w-full";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.className = "pointer-events-auto flex items-center space-x-3 px-4 py-3 rounded-xl shadow-2xl border text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0";
  
  let bgBorder = "bg-slate-900/95 border-slate-700 text-slate-100";
  let iconHtml = '<i data-lucide="info" class="w-5 h-5 text-teal-400 shrink-0"></i>';
  
  if (type === "success") {
    bgBorder = "bg-slate-900/95 border-teal-500/60 text-white shadow-teal-950/40";
    iconHtml = '<i data-lucide="check-circle-2" class="w-5 h-5 text-teal-400 shrink-0"></i>';
  } else if (type === "error") {
    bgBorder = "bg-slate-900/95 border-rose-500/60 text-white shadow-rose-950/40";
    iconHtml = '<i data-lucide="alert-circle" class="w-5 h-5 text-rose-400 shrink-0"></i>';
  } else if (type === "warning") {
    bgBorder = "bg-slate-900/95 border-amber-500/60 text-white shadow-amber-950/40";
    iconHtml = '<i data-lucide="alert-triangle" class="w-5 h-5 text-amber-400 shrink-0"></i>';
  }
  
  toast.className += ` ${bgBorder}`;
  toast.innerHTML = `
    ${iconHtml}
    <div class="flex-1 text-xs leading-relaxed font-sans">${msg}</div>
  `;
  
  toastContainer.appendChild(toast);
  if (window.lucide) lucide.createIcons();
  
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });
  
  setTimeout(() => {
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 350);
  }, 4500);
}

function openLicenseModal() {
  openSettingsModal('license');
}

function closeLicenseModal() {
  const sm = document.getElementById("settings-modal");
  if (sm && !sm.classList.contains("hidden")) {
    const licPanel = document.getElementById("spanel-license");
    if (licPanel && !licPanel.classList.contains("hidden")) {
      closeSettingsModal();
    }
  }
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




// ===================== SRT TIMED SPEECH =====================
let currentSrtAudio = null;

function updateSrtVoiceLabel() {
  const v = voices.find(x => x.id === selectedVoiceId);
  const el = document.getElementById("srt-voice-name");
  if (el) el.innerText = v ? `${v.name} (${v.region})` : selectedVoiceId;
}

const _origSwitchTab = switchTab;
switchTab = function (tabId) {
  _origSwitchTab(tabId);
  if (tabId === "srt" || tabId === "batch") {
    populateVoiceDropdowns();
  }
};

function handleSrtFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  document.getElementById("srt-file-label").innerText = file.name;
  const reader = new FileReader();
  reader.onload = (ev) => { document.getElementById("srt-input").value = ev.target.result; };
  reader.readAsText(file, "utf-8");
}

async function generateFromSrt() {
  const srtText = document.getElementById("srt-input").value.trim();
  if (!srtText) { alert("Vui lòng dán nội dung hoặc chọn file SRT!"); return; }

  stopCurrentPreview();
  const btn = document.getElementById("btn-srt");
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Đang đọc từng câu theo SRT... (có thể mất vài phút)</span>`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/tts/srt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        srt_text: srtText,
        voice_id: selectedVoiceId,
        speed: parseFloat(document.getElementById("speed-slider").value),
        fit: document.getElementById("srt-fit").checked
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      alert("Không thể tạo giọng theo SRT: " + (data.detail || "Lỗi không xác định"));
      return;
    }
    currentSrtAudio = data.filename;
    const info = document.getElementById("srt-result-info");
    let msg = `✓ ${data.cues} câu • dài ${data.duration}s • ${data.size_kb} KB`;
    if (data.late_cues && data.late_cues.length) {
      msg += ` • ⚠ Câu bị trễ so với mốc: ${data.late_cues.slice(0, 15).join(", ")}${data.late_cues.length > 15 ? "..." : ""} (khung thời gian quá ngắn)`;
    }
    info.innerText = msg;
    const player = document.getElementById("srt-player");
    player.src = data.audio_url;
    player.play();
    document.getElementById("srt-result").classList.remove("hidden");
    loadHistory();
    lucide.createIcons();
  } catch (err) {
    alert("Lỗi kết nối máy chủ TTS: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
    lucide.createIcons();
  }
}

async function downloadSrtAudio() {
  if (!currentSrtAudio) return;
  triggerFileDownload(`/api/audio/${currentSrtAudio}`, currentSrtAudio);
  try {
    await fetch(`/api/audio/save-to-downloads/${currentSrtAudio}`, { method: "POST" });
    showActivationToast(`✅ Đã lưu ${currentSrtAudio} vào thư mục Downloads!`);
  } catch (e) {}
}

// ===================== BATCH GENERATION =====================
let batchFiles = [];

function parseBatchParts(raw) {
  const text = raw.replace(/\r\n/g, "\n").trim();
  const re = /^\s*\[P(\d+)\]\s*/gim;
  const marks = [...text.matchAll(re)];
  if (marks.length) {
    return marks.map((m, i) => {
      const start = m.index + m[0].length;
      const end = i + 1 < marks.length ? marks[i + 1].index : text.length;
      return { label: `P${m[1]}`, text: text.slice(start, end).trim() };
    }).filter(p => p.text);
  }
  return text.split(/\n\s*\n/).map((t, i) => ({ label: `P${i + 1}`, text: t.trim() })).filter(p => p.text);
}

async function processBatchTTS() {
  const raw = document.getElementById("batch-input").value;
  const parts = parseBatchParts(raw);
  if (!parts.length) { alert("Vui lòng nhập nội dung. Dùng [P1], [P2]... ở đầu mỗi phần."); return; }

  stopCurrentPreview();
  const box = document.getElementById("batch-results");
  box.innerHTML = "";
  batchFiles = [];
  const speed = parseFloat(document.getElementById("speed-slider").value);

  const rows = parts.map(p => {
    const div = document.createElement("div");
    div.className = "p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between gap-3 text-xs";
    div.innerHTML = `<div class="flex-1 min-w-0"><span class="font-bold text-brand-400">${p.label}</span> <span class="text-slate-300 truncate">${p.text.slice(0, 80).replace(/</g, "&lt;")}</span></div><div class="batch-status text-slate-500">Đang chờ...</div>`;
    box.appendChild(div);
    return div;
  });

  for (let i = 0; i < parts.length; i++) {
    const st = rows[i].querySelector(".batch-status");
    st.innerHTML = `<span class="text-yellow-400">Đang tạo...</span>`;
    try {
      const res = await fetch("/api/tts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: parts[i].text, voice_id: selectedVoiceId, speed, include_subtitles: false })
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || "Lỗi");
      batchFiles.push(data.filename);
      st.innerHTML = `
        <div class="flex items-center space-x-1.5">
          <button onclick="new Audio('${data.audio_url}').play()" class="px-2 py-1 bg-brand-600 hover:bg-brand-500 text-white rounded text-[11px] font-semibold">Nghe</button>
          <button onclick="downloadAudioItem('${data.filename}')" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-semibold">Tải</button>
        </div>`;
    } catch (err) {
      st.innerHTML = `<span class="text-red-400">Lỗi: ${String(err.message).slice(0, 60)}</span>`;
    }
  }

  if (batchFiles.length) {
    const z = document.createElement("button");
    z.className = "w-full mt-2 py-2.5 bg-slate-800 hover:bg-brand-600 text-slate-200 hover:text-white text-xs font-bold rounded-xl transition flex items-center justify-center space-x-1.5";
    z.innerHTML = `<span>📦 Tải tất cả (${batchFiles.length} file) dạng ZIP</span>`;
    z.onclick = downloadBatchZip;
    box.appendChild(z);
  }
  loadHistory();
}

async function downloadBatchZip() {
  try {
    const res = await fetch("/api/audio/zip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filenames: batchFiles })
    });
    const data = await res.json();
    if (data.success) {
      triggerFileDownload(data.url, data.filename);
      showActivationToast(`✅ Đã lưu ${data.filename} vào thư mục Downloads!`);
    }
  } catch (e) { alert("Không tạo được file ZIP: " + e.message); }
}


// ===================== ENGINE SWITCH (Edge / VieNeu / Supertonic) =====================
function updateEngineButtons() {
  const on = "py-1.5 rounded-lg text-xs font-bold bg-teal-600 text-white transition shadow-sm";
  const off = "py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition";
  const bEdge = document.getElementById("engine-edge");
  const bVieneu = document.getElementById("engine-vieneu");
  const bSuper = document.getElementById("engine-supertonic");
  if (bEdge) bEdge.className = currentEngine === "edge" ? on : off;
  if (bVieneu) bVieneu.className = currentEngine === "vieneu" ? on : off;
  if (bSuper) bSuper.className = currentEngine === "supertonic" ? on : off;
}

function updateVieneuBanner() {
  const b = document.getElementById("vieneu-banner");
  if (!b) return;
  if (currentEngine === "edge") {
    b.classList.add("hidden");
    return;
  }
  b.classList.remove("hidden");
  if (currentEngine === "supertonic") {
    b.className = "mb-3 p-2.5 rounded-xl text-xs border bg-teal-950/40 border-teal-700/60 text-teal-300 flex items-center justify-between shadow-sm";
    b.innerHTML = `<span>🌐 <b>Supertonic 3</b>: Đang hoạt động (10 giọng quốc tế, 31 ngôn ngữ, 44 kHz).</span> <button onclick="openSettingsModal('models')" class="underline text-xs ml-2 text-teal-200 hover:text-white font-medium">Đổi mô hình</button>`;
    return;
  }
  const st = vieneuInfo.state;
  if (st === "ready") {
    b.className = "mb-3 p-2.5 rounded-xl text-xs border bg-teal-950/40 border-teal-700/60 text-teal-300 flex items-center justify-between shadow-sm";
    b.innerHTML = `<span>✅ <b>VieNeu-TTS</b>: Đã sẵn sàng chạy offline. Hỗ trợ nhân bản giọng.</span> <button onclick="openSettingsModal('models')" class="underline text-xs ml-2 text-teal-200 hover:text-white font-medium">Đổi mô hình</button>`;
  } else if (st === "loading") {
    b.className = "mb-3 p-2.5 rounded-xl text-xs border bg-amber-950/30 border-amber-700/60 text-amber-300 shadow-sm";
    b.innerHTML = "⏳ " + (vieneuInfo.message || "Đang nạp mô hình...") + " Lần đầu cần Internet để tải dữ liệu mô hình.";
  } else if (st === "error") {
    b.className = "mb-3 p-2.5 rounded-xl text-xs border bg-red-950/30 border-red-800/60 text-red-300 flex items-center justify-between shadow-sm";
    b.innerHTML = `<span>⚠ ${vieneuInfo.message || "Lỗi nạp mô hình"}</span> <div><button onclick="loadVieneu()" class="underline ml-1">Thử lại</button><button onclick="openSettingsModal('models')" class="underline ml-2">Chọn mô hình khác</button></div>`;
  } else {
    b.className = "mb-3 p-2.5 rounded-xl text-xs border bg-slate-950/60 border-slate-700 text-slate-300 flex items-center justify-between shadow-sm";
    b.innerHTML = `<span>VieNeu-TTS chưa được bật.</span> <div><button onclick="loadVieneu()" class="ml-1 px-2.5 py-0.5 rounded bg-teal-600 hover:bg-teal-500 text-white font-semibold">Bật VieNeu-TTS</button><button onclick="openSettingsModal('models')" class="underline text-xs ml-2 text-slate-400 hover:text-white">Cài đặt</button></div>`;
  }
}

async function loadVieneu() {
  try {
    const r = await fetch("/api/vieneu/load", { method: "POST" });
    vieneuInfo = await r.json();
  } catch (e) {}
  updateVieneuBanner();
  if (vieneuPoll) clearInterval(vieneuPoll);
  vieneuPoll = setInterval(async () => {
    try {
      vieneuInfo = await (await fetch("/api/vieneu/status")).json();
      updateVieneuBanner();
      if (vieneuInfo.state === "ready" || vieneuInfo.state === "error") {
        clearInterval(vieneuPoll);
        vieneuPoll = null;
        if (vieneuInfo.state === "ready") {
          await fetchVoices();
          const first = voices.find(v => v.engine === "vieneu");
          if (first && currentEngine === "vieneu") selectVoice(first.id);
        }
      }
    } catch (e) {}
  }, 2000);
}

function setEngine(engine) {
  stopCurrentPreview();
  currentEngine = engine;
  try { localStorage.setItem("xteam_engine", engine); } catch (e) {}
  updateEngineButtons();
  if (engine === "supertonic") {
    document.querySelectorAll(".voice-filter-btn").forEach(b => {
      if (b.getAttribute("data-region") === "all") {
        b.className = "voice-filter-btn px-2.5 py-1 text-xs rounded-lg font-medium bg-brand-600 text-white";
      } else {
        b.className = "voice-filter-btn px-2.5 py-1 text-xs rounded-lg font-medium bg-slate-800 text-slate-300 hover:bg-slate-700";
      }
    });
  }
  if (engine === "supertonic") {
    selectedVoiceId = "st:M2"; // Mặc định giọng Watson ( M2 ) cho Supertonic 3
  } else {
    const cur = voices.find(v => v.id === selectedVoiceId);
    if (!cur || (cur.engine || "edge") !== engine) {
      const first = voices.find(v => (v.engine || "edge") === engine);
      if (first) selectedVoiceId = first.id;
    }
  }
  const currentRegion = (engine === "supertonic") ? "all" : (document.querySelector(".voice-filter-btn.bg-brand-600")?.getAttribute("data-region") || "all");
  renderVoices(currentRegion);
  updateVieneuBanner();
  if (engine === "vieneu" && vieneuInfo.state === "idle") loadVieneu();
  else if (engine === "vieneu" && vieneuInfo.state === "loading" && !vieneuPoll) loadVieneu();
}

// ===================== VOICE CLONING =====================
function handleCloneFileSelect(e) {
  cloneFile = e.target.files[0] || null;
  document.getElementById("clone-file-label").innerText = cloneFile ? cloneFile.name : "Bấm để chọn file ghi âm mẫu từ máy tính";
}

async function submitVoiceClone() {
  const name = document.getElementById("clone-name").value.trim();
  if (!name) return alert("Vui lòng đặt tên cho giọng nhân bản!");
  if (!cloneFile) return alert("Vui lòng chọn file ghi âm mẫu (5-8 giây)!");
  if (!document.getElementById("clone-consent").checked) return alert("Bạn cần tích xác nhận quyền sử dụng giọng trước khi nhân bản.");

  const btn = event.currentTarget;
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Đang nhân bản giọng... (lần đầu cần tải mô hình, có thể vài phút)</span>`;
  lucide.createIcons();

  try {
    const fd = new FormData();
    fd.append("voice_name", name);
    fd.append("consent", "true");
    fd.append("sample_file", cloneFile);
    const res = await fetch("/api/tts/clone", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok || !data.success) {
      alert("Không thể nhân bản giọng: " + (data.detail || "Lỗi không xác định"));
      return;
    }
    vieneuInfo.state = "ready";
    await fetchVoices();
    currentEngine = "vieneu";
    updateEngineButtons();
    selectedVoiceId = data.voice.id;
    renderVoices("all");
    updateVieneuBanner();
    document.getElementById("clone-name").value = "";
    document.getElementById("clone-consent").checked = false;
    cloneFile = null;
    document.getElementById("clone-file-label").innerText = "Bấm để chọn file ghi âm mẫu từ máy tính";
    showActivationToast(`✅ Đã tạo giọng "${data.voice.name}". Giọng đã được chọn ở tab TTS Studio.`);
    switchTab("tts");
  } catch (err) {
    alert("Lỗi kết nối: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
    lucide.createIcons();
  }
}

// ==================== CONVERSATION / MULTI-SPEAKER ====================
let conversationRows = [
  { id: 1, speaker: "Người dẫn", voice_id: "north_male_news_1", speed: 1.0, text: "Chào mừng quý thính giả đến với số podcast đặc biệt hôm nay." },
  { id: 2, speaker: "Khách mời", voice_id: "north_female_story_1", speed: 1.0, text: "Xin chào anh và xin chào tất cả các bạn đang lắng nghe chương trình." }
];

function escapeHtml(text) {
  if (!text) return "";
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderConversationRows() {
  const container = document.getElementById("conversation-list");
  if (!container) return;
  container.innerHTML = "";

  conversationRows.forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3 relative hover:border-slate-700 transition";

    let voiceOptions = "";
    voices.forEach(v => {
      const selected = (v.id === row.voice_id) ? "selected" : "";
      voiceOptions += `<option value="${v.id}" ${selected}>${v.name} (${v.region || ""} - ${v.gender || ""})</option>`;
    });

    div.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-2.5">
        <div class="flex items-center space-x-2">
          <span class="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 font-bold text-xs flex items-center justify-center border border-brand-500/30">
            ${idx + 1}
          </span>
          <input type="text" value="${escapeHtml(row.speaker)}" placeholder="Tên nhân vật"
            onchange="updateConvRow(${idx}, 'speaker', this.value)"
            class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white font-semibold w-32 focus:border-brand-500 focus:outline-none">
        </div>

        <div class="flex items-center space-x-2">
          <select onchange="updateConvRow(${idx}, 'voice_id', this.value)"
            class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white focus:border-brand-500 focus:outline-none custom-scrollbar">
            ${voiceOptions}
          </select>
          <select onchange="updateConvRow(${idx}, 'speed', parseFloat(this.value))"
            class="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:border-brand-500 focus:outline-none">
            <option value="0.75" ${row.speed === 0.75 ? "selected" : ""}>0.75x</option>
            <option value="0.9" ${row.speed === 0.9 ? "selected" : ""}>0.9x</option>
            <option value="1.0" ${row.speed === 1.0 ? "selected" : ""}>1.0x</option>
            <option value="1.1" ${row.speed === 1.1 ? "selected" : ""}>1.1x</option>
            <option value="1.25" ${row.speed === 1.25 ? "selected" : ""}>1.25x</option>
          </select>
          <button onclick="previewConvRow(${idx})" title="Nghe thử câu này"
            class="p-1.5 bg-slate-800 hover:bg-slate-700 text-brand-400 rounded-lg transition">
            <i data-lucide="play" class="w-3.5 h-3.5"></i>
          </button>
          <button onclick="removeConvRow(${idx})" title="Xóa lượt thoại"
            class="p-1.5 bg-slate-800 hover:bg-red-950 hover:text-red-400 text-slate-400 rounded-lg transition">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </div>

      <textarea rows="2" placeholder="Nhập lời thoại của nhân vật..."
        oninput="updateConvRow(${idx}, 'text', this.value)"
        class="w-full bg-slate-900/60 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-brand-500 focus:outline-none resize-y">${escapeHtml(row.text)}</textarea>
    `;
    container.appendChild(div);
  });
  if (window.lucide) lucide.createIcons();
}

function addConvRow() {
  const defaultVoices = ["north_female_news_1", "north_male_news_1", "south_female_gentle_1", "central_male_warm_1"];
  const nextVoice = defaultVoices[conversationRows.length % defaultVoices.length] || "north_male_news_1";

  conversationRows.push({
    id: Date.now(),
    speaker: `Nhân vật ${conversationRows.length + 1}`,
    voice_id: nextVoice,
    speed: 1.0,
    text: ""
  });
  renderConversationRows();
}

function removeConvRow(idx) {
  if (conversationRows.length <= 1) {
    showToast("Cần ít nhất một câu thoại trong kịch bản.", "info");
    return;
  }
  conversationRows.splice(idx, 1);
  renderConversationRows();
}

function clearConvRows() {
  conversationRows = [
    { id: Date.now(), speaker: "Nhân vật 1", voice_id: "north_male_news_1", speed: 1.0, text: "" }
  ];
  renderConversationRows();
}

function updateConvRow(idx, field, val) {
  if (conversationRows[idx]) {
    conversationRows[idx][field] = val;
  }
}

async function previewConvRow(idx) {
  const row = conversationRows[idx];
  if (!row || !row.text.trim()) {
    showToast("Vui lòng nhập lời thoại để nghe thử.", "info");
    return;
  }
  showToast(`Đang tạo âm thanh nghe thử cho ${row.speaker}...`, "info");
  try {
    const res = await fetch("/api/tts/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: row.text,
        voice_id: row.voice_id,
        speed: row.speed || 1.0,
        format: "mp3"
      })
    });
    const data = await res.json();
    if (res.ok && data.audio_url) {
      const audio = new Audio(data.audio_url);
      audio.play();
    } else {
      showToast("Lỗi nghe thử: " + (data.detail || "Không tạo được"), "error");
    }
  } catch (err) {
    showToast("Lỗi kết nối: " + err.message, "error");
  }
}

async function generateConversation() {
  const valid = conversationRows.filter(r => r.text && r.text.trim());
  if (valid.length === 0) {
    showToast("Vui lòng nhập ít nhất một câu thoại có nội dung.", "error");
    return;
  }

  const pauseSec = parseFloat(document.getElementById("conv-pause-between")?.value || "0.5");
  const btn = document.getElementById("btn-generate-conv");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Đang ghép hội thoại...</span>`;
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch("/api/tts/conversation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dialogues: valid,
        pause_between: pauseSec,
        format: "wav"
      })
    });
    const data = await res.json();
    if (!res.ok) {
      showToast("Lỗi tạo hội thoại: " + (data.detail || "Không xác định"), "error");
      return;
    }

    showToast(`Tạo hội thoại thành công! Thời lượng: ${data.duration}s`, "success");
    const resultBox = document.getElementById("conv-result-box");
    resultBox.classList.remove("hidden");

    const player = document.getElementById("conv-audio-player");
    player.src = data.audio_url;
    player.play().catch(() => {});

    document.getElementById("conv-duration-badge").innerText = `${data.duration}s`;
    document.getElementById("conv-turns-badge").innerText = `${data.turns} lượt`;
    document.getElementById("conv-size-badge").innerText = `${data.size_kb} KB`;

    document.getElementById("conv-download-btn").onclick = () => {
      triggerFileDownload(data.audio_url, data.filename);
    };
    document.getElementById("conv-save-btn").onclick = () => {
      saveAudioToDownloads(data.filename);
    };

    fetchHistory();
  } catch (err) {
    showToast("Lỗi kết nối máy chủ: " + err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i><span>Ghép & Tạo File Hội Thoại</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

// ==================== SETTINGS MODAL & MODEL MANAGEMENT ====================
function openSettingsModal(tabName = "models") {
  document.getElementById("settings-modal").classList.remove("hidden");
  switchSettingsTab(tabName);
  fetchSettingsModels();
  fetchLanSettings();
}

function closeSettingsModal() {
  document.getElementById("settings-modal").classList.add("hidden");
}

function switchSettingsTab(tabName) {
  document.querySelectorAll(".spanel").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".stab-btn").forEach(el => {
    el.classList.remove("bg-teal-700", "text-white", "shadow-sm");
    el.classList.add("text-slate-400");
  });

  const targetPanel = document.getElementById(`spanel-${tabName}`);
  const targetBtn = document.getElementById(`stab-btn-${tabName}`);
  if (targetPanel && targetBtn) {
    targetPanel.classList.remove("hidden");
    targetBtn.classList.remove("text-slate-400");
    targetBtn.classList.add("bg-teal-700", "text-white", "shadow-sm");
  }

  if (tabName === "logs") {
    fetchLogs();
  } else if (tabName === "license") {
    checkLicenseStatus(false);
  }
}

async function fetchSettingsModels() {
  const container = document.getElementById("settings-models-container");
  if (!container) return;

  try {
    const res = await fetch("/api/settings/models");
    const data = await res.json();
    if (!res.ok || !data.success) return;

    container.innerHTML = "";

    data.models.forEach(m => {
      const card = document.createElement("div");
      const isActive = m.is_active;

      card.className = `p-4 rounded-2xl border transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
        isActive
          ? "border-teal-500/70 bg-teal-950/20 shadow-md shadow-teal-900/10"
          : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
      }`;

      let tagsHtml = "";
      (m.tags || []).forEach(t => {
        let tagClass = "bg-slate-800 text-slate-300";
        if (t === "Khuyến nghị" || t === "Nhanh nhất") tagClass = "bg-teal-500/20 text-teal-300 border border-teal-500/30";
        if (t === "Thử nghiệm") tagClass = "bg-amber-500/20 text-amber-300 border border-amber-500/30";
        tagsHtml += `<span class="px-2 py-0.5 rounded text-[11px] font-semibold ${tagClass}">${t}</span>`;
      });

      let iconName = "cpu";
      if (m.id.includes("gpu")) iconName = "zap";
      if (m.id.includes("supertonic")) iconName = "languages";
      if (m.id.includes("nano")) iconName = "feather";

      let actionBtn = "";
      if (isActive) {
        actionBtn = `
          <button disabled class="px-4 py-2 bg-teal-700 text-white rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-sm opacity-95">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>✓ Đang dùng</span>
          </button>
        `;
      } else if (m.action_type === "disabled") {
        actionBtn = `
          <button disabled class="px-4 py-2 bg-slate-800/60 text-slate-500 border border-slate-800 rounded-xl text-xs font-medium cursor-not-allowed">
            Không khả dụng
          </button>
        `;
      } else if (m.action_type === "download_apply") {
        actionBtn = `
          <button onclick="applyModel('${m.id}', this)" class="px-4 py-2 bg-teal-800 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1 shadow-sm">
            <i data-lucide="download" class="w-3.5 h-3.5"></i>
            <span>Tải về & Áp dụng</span>
          </button>
        `;
      } else {
        actionBtn = `
          <button onclick="applyModel('${m.id}', this)" class="px-4 py-2 border border-slate-600 hover:border-teal-500 hover:bg-teal-950/40 text-slate-200 hover:text-white rounded-xl text-xs font-bold transition shadow-sm">
            Áp dụng
          </button>
        `;
      }

      card.innerHTML = `
        <div class="flex items-start space-x-3.5">
          <div class="w-9 h-9 rounded-xl ${isActive ? "bg-teal-600 text-white" : "bg-slate-800 text-teal-400"} flex items-center justify-center shrink-0 mt-0.5">
            <i data-lucide="${iconName}" class="w-4 h-4"></i>
          </div>
          <div class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-bold text-white text-sm">${m.name}</span>
              ${tagsHtml}
            </div>
            <div class="text-[11px] ${isActive ? "text-teal-300" : "text-slate-400"} flex items-center space-x-1">
              <span>${m.downloaded ? "✓ " : ""}${m.status_text}</span>
            </div>
            <div class="text-[11px] text-slate-500">${m.notes}</div>
          </div>
        </div>
        <div class="shrink-0 self-end sm:self-center mt-2 sm:mt-0">
          ${actionBtn}
        </div>
      `;

      container.appendChild(card);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Lỗi tải models:", err);
  }
}

async function applyModel(modelId, btnElement) {
  if (btnElement) {
    btnElement.disabled = true;
    btnElement.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Đang nạp mô hình...</span>`;
    if (window.lucide) lucide.createIcons();
  }
  showToast("Đang kích hoạt mô hình AI...", "info");
  try {
    const res = await fetch("/api/settings/models/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      if (modelId === "supertonic_3") {
        setEngine("supertonic");
        selectedVoiceId = "st:M2"; // Mặc định giọng Watson ( M2 )
        renderVoices("all");
      } else {
        setEngine("vieneu");
      }
      showToast("Đã chuyển đổi và áp dụng mô hình AI thành công!", "success");
      await fetchSettingsModels();
      await fetchVoices();
    } else {
      showToast("Không chuyển được mô hình: " + (data.detail || "Lỗi"), "error");
      if (btnElement) {
        btnElement.disabled = false;
        btnElement.innerText = "Áp dụng";
      }
    }
  } catch (err) {
    showToast("Lỗi kết nối: " + err.message, "error");
    if (btnElement) {
      btnElement.disabled = false;
      btnElement.innerText = "Áp dụng";
    }
  }
}

async function fetchLanSettings() {
  try {
    const res = await fetch("/api/settings/lan");
    const data = await res.json();
    if (res.ok && data.success) {
      const toggle = document.getElementById("lan-toggle");
      if (toggle) toggle.checked = !!data.lan_enabled;
      const ipDisp = document.getElementById("lan-ip-display");
      if (ipDisp) ipDisp.value = data.lan_url;
      const keyDisp = document.getElementById("lan-key-display");
      if (keyDisp) keyDisp.value = data.api_key;
    }
  } catch (err) {
    console.error("Lỗi tải cài đặt LAN:", err);
  }
}

async function toggleLanAccess(enabled) {
  try {
    const res = await fetch("/api/settings/lan/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: enabled })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(enabled ? "Đã bật chia sẻ API qua mạng LAN!" : "Đã tắt chia sẻ mạng LAN.", "success");
    }
  } catch (err) {
    showToast("Lỗi cập nhật LAN: " + err.message, "error");
  }
}

async function regenerateLanKey() {
  if (!confirm("Tạo khóa API mới sẽ làm các máy khác đang dùng khóa cũ bị từ chối kết nối. Bạn có chắc không?")) return;
  try {
    const res = await fetch("/api/settings/lan/regen-key", { method: "POST" });
    const data = await res.json();
    if (res.ok && data.success) {
      document.getElementById("lan-key-display").value = data.api_key;
      showToast("Đã cấp khóa API mới thành công!", "success");
    }
  } catch (err) {
    showToast("Lỗi cấp khóa mới: " + err.message, "error");
  }
}

function copyLanUrl() {
  const val = document.getElementById("lan-ip-display")?.value;
  if (val) {
    navigator.clipboard.writeText(val);
    showToast("Đã sao chép địa chỉ LAN: " + val, "success");
  }
}

function copyLanKey() {
  const val = document.getElementById("lan-key-display")?.value;
  if (val) {
    navigator.clipboard.writeText(val);
    showToast("Đã sao chép khóa API!", "success");
  }
}

// ==================== SYSTEM LOGS ====================
let currentLogsText = "";

function openLogModal() {
  const m = document.getElementById("log-modal");
  if (m) m.classList.remove("hidden");
  fetchLogs();
}

function closeLogModal() {
  const m = document.getElementById("log-modal");
  if (m) m.classList.add("hidden");
}

async function fetchLogs() {
  try {
    const res = await fetch("/api/logs");
    const data = await res.json();
    if (!res.ok || !data.success) return;

    currentLogsText = data.text || "";
    const termModal = document.getElementById("modal-log-terminal");
    const termSettings = document.getElementById("settings-log-terminal");
    const countBadge = document.getElementById("log-count-badge");

    if (countBadge) {
      countBadge.innerText = `${data.total || (data.logs ? data.logs.length : 0)} dòng log`;
    }

    let coloredHtml = "";
    (data.logs || []).forEach(l => {
      let lvlColor = "text-teal-400";
      if (l.level === "ERROR") lvlColor = "text-rose-400 font-bold";
      else if (l.level === "WARNING") lvlColor = "text-amber-400 font-bold";
      else if (l.level === "SUCCESS") lvlColor = "text-emerald-400 font-semibold";

      coloredHtml += `<div class="py-0.5"><span class="text-slate-500">[${l.time}]</span> <span class="${lvlColor}">[${l.level}]</span> <span class="text-slate-200">${l.message}</span></div>`;
    });

    if (!data.logs || data.logs.length === 0) {
      coloredHtml = `<div class="text-slate-500 italic py-2">Chưa có bản ghi log nào.</div>`;
    }

    if (termModal) {
      termModal.innerHTML = coloredHtml;
      termModal.scrollTop = termModal.scrollHeight;
    }
    if (termSettings) {
      termSettings.innerHTML = coloredHtml;
      termSettings.scrollTop = termSettings.scrollHeight;
    }
  } catch (err) {
    console.error("Lỗi tải log:", err);
  }
}

async function copyLogs() {
  if (!currentLogsText) {
    await fetchLogs();
  }
  if (!currentLogsText) {
    showToast("Chưa có nhật ký log để sao chép.", "info");
    return;
  }
  try {
    await navigator.clipboard.writeText(currentLogsText);
    showToast("Đã sao chép toàn bộ nhật ký log vào bộ nhớ tạm!", "success");
  } catch (err) {
    const ta = document.createElement("textarea");
    ta.value = currentLogsText;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    showToast("Đã sao chép nhật ký log!", "success");
  }
}

async function clearLogs() {
  if (!confirm("Bạn có chắc muốn xóa sạch toàn bộ nhật ký log không?")) return;
  try {
    const res = await fetch("/api/logs/clear", { method: "POST" });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Đã xóa nhật ký log hệ thống thành công!", "success");
      await fetchLogs();
    }
  } catch (err) {
    showToast("Lỗi xóa log: " + err.message, "error");
  }
}
