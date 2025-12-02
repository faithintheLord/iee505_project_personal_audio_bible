const apiBase = '/api';
const token = localStorage.getItem('token');
if (!token) window.location.href = '/static/login.html';

const authFail = () => {
  localStorage.removeItem('token');
  window.location.href = '/static/login.html';
};

const headers = () => ({ 'Authorization': `Bearer ${token}` });

const bibleSelect = document.getElementById('bible-select');
const bookSelect = document.getElementById('book-select');
const chapterSelect = document.getElementById('chapter-select');
const versionSelect = document.getElementById('version-select');
const recordingsTable = document.querySelector('#recordings-table tbody');
const analyticsSummary = document.getElementById('analytics-summary');
const analyticsTable = document.querySelector('#analytics-table tbody');
const boxCanvas = document.getElementById('wpm-boxplot');
const histCanvas = document.getElementById('wpm-hist');
const recordMsg = document.getElementById('record-msg');
const timerSpan = document.getElementById('timer');
let mediaRecorder, chunks = [], startTime, timerId, lastDuration = 0;
const bookMeta = {};
const chapterMeta = {};

async function apiGet(path) {
  const res = await fetch(path, { headers: headers() });
  if (res.status === 401) return authFail();
  if (!res.ok) throw new Error('Request failed');
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(path, { method: 'DELETE', headers: headers() });
  if (res.status === 401) return authFail();
  if (!res.ok) throw new Error('Delete failed');
}

async function apiPut(path, data) {
  const res = await fetch(path, {
    method: 'PUT',
    headers: { ...headers(), 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (res.status === 401) return authFail();
  if (!res.ok) throw new Error('Update failed');
}

function fillOptions(select, items, mapFn) {
  select.innerHTML = '';
  items.forEach(item => {
    const opt = document.createElement('option');
    const { value, label } = mapFn(item);
    opt.value = value;
    opt.textContent = label;
    select.appendChild(opt);
  });
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZoneName: 'short',
  }).formatToParts(date);
  const lookup = {};
  parts.forEach(p => { if (p.type !== 'literal') lookup[p.type] = p.value; });
  const tz = lookup.timeZoneName || '';
  return `${lookup.month}-${lookup.day}-${lookup.year} ${lookup.hour}:${lookup.minute} ${lookup.dayPeriod || ''} ${tz}`.replace('  ', ' ').trim();
}

async function loadBibles() {
  const bibles = await apiGet(`${apiBase}/bibles`);
  if (!bibles) return;
  fillOptions(bibleSelect, bibles, b => ({ value: b.bible_id, label: `${b.name} (${b.language})` }));
  if (bibleSelect.value) {
    await loadBooks();
    await loadRecordings();
    await loadAnalytics();
  }
}

async function loadVersions() {
  const versions = await apiGet(`${apiBase}/versions`);
  if (!versions) return;
  fillOptions(versionSelect, versions, v => ({ value: v, label: v }));
}

async function loadBooks() {
  const bibleId = bibleSelect.value;
  const books = await apiGet(`${apiBase}/bibles/${bibleId}/books`);
  if (!books) return;
  books.forEach(b => {
    bookMeta[b.Books.book_id] = { name: b.CanonBooks.canon_book_name };
  });
  fillOptions(bookSelect, books, b => ({ value: b.Books.book_id, label: b.CanonBooks.canon_book_name }));
  if (bookSelect.value) await loadChapters();
}

async function loadChapters() {
  const bookId = bookSelect.value;
  const chapters = await apiGet(`${apiBase}/books/${bookId}/chapters`);
  if (!chapters) return;
  chapters.forEach(c => {
    chapterMeta[c.Chapters.chapter_id] = { verse_count: c.CanonChapters.verse_count };
  });
  fillOptions(chapterSelect, chapters, c => ({ value: c.Chapters.chapter_id, label: c.CanonChapters.canon_book_chapter }));
  // reset verse inputs to start of chapter
  document.getElementById('verse-start').value = 1;
  document.getElementById('verse-end').value = 1;
  updateVerseLimits();
  await fillTranscriptionFromSelection();
}

async function loadRecordings() {
  const bibleId = bibleSelect.value;
  const rows = await apiGet(`${apiBase}/bibles/${bibleId}/recordings`);
  if (!rows) return;
  recordingsTable.innerHTML = '';
  rows.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.book_name}</td>
      <td>${row.chapter_number}</td>
      <td>${row.verse_start}-${row.verse_end}</td>
      <td>${formatDateTime(row.date_recorded)}</td>
      <td>${row.accessed_count}</td>
      <td>${row.duration_seconds ?? ''}</td>
      <td>${row.computed_wpm ? row.computed_wpm.toFixed(2) : ''}</td>
      <td>
        <button data-id="${row.recording_id}" class="play">Play</button>
        <button data-id="${row.recording_id}" class="delete">Delete</button>
      </td>`;
    recordingsTable.appendChild(tr);
  });
}

function fmtNum(val, digits = 2) {
  if (val === null || val === undefined) return '';
  if (typeof val === 'number') return val.toFixed(digits);
  return val;
}

function renderBoxPlot(stats) {
  if (!boxCanvas || !stats || !stats.count) {
    if (boxCanvas) boxCanvas.getContext('2d').clearRect(0, 0, boxCanvas.width, boxCanvas.height);
    return;
  }
  const ctx = boxCanvas.getContext('2d');
  const { min, q1, median, q3, max } = stats;
  const w = boxCanvas.width, h = boxCanvas.height;
  ctx.clearRect(0, 0, w, h);
  const pad = 20;
  const scale = (val) => pad + ((val - min) / (max - min || 1)) * (w - pad * 2);
  const midY = h / 2;
  ctx.strokeStyle = '#000'; ctx.fillStyle = '#ccc'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(scale(min), midY); ctx.lineTo(scale(max), midY); ctx.stroke();
  const boxLeft = scale(q1), boxRight = scale(q3), boxTop = midY - 15, boxBot = midY + 15;
  ctx.fillRect(boxLeft, boxTop, boxRight - boxLeft, boxBot - boxTop);
  ctx.strokeRect(boxLeft, boxTop, boxRight - boxLeft, boxBot - boxTop);
  ctx.beginPath(); const medX = scale(median); ctx.moveTo(medX, boxTop); ctx.lineTo(medX, boxBot); ctx.stroke();
}

function renderHistogram(hist) {
  if (!histCanvas || !hist || !hist.length) {
    if (histCanvas) histCanvas.getContext('2d').clearRect(0, 0, histCanvas.width, histCanvas.height);
    return;
  }
  const ctx = histCanvas.getContext('2d');
  const w = histCanvas.width, h = histCanvas.height;
  ctx.clearRect(0, 0, w, h);
  const maxCount = Math.max(...hist.map(b => b.count));
  const barW = w / hist.length;
  ctx.fillStyle = '#444';
  hist.forEach((b, i) => {
    const barH = maxCount ? (b.count / maxCount) * (h - 20) : 0;
    ctx.fillRect(i * barW + 2, h - barH, barW - 4, barH);
  });
}

async function loadAnalytics() {
  const bibleId = bibleSelect.value;
  if (!bibleId) return;
  const data = await apiGet(`${apiBase}/bibles/${bibleId}/analytics`);
  if (!data) return;
  const stats = data.wpm_stats || {};
  analyticsSummary.textContent = `Count: ${stats.count || 0} | Min: ${fmtNum(stats.min)} | Max: ${fmtNum(stats.max)} | Mean: ${fmtNum(stats.mean)} | Median: ${fmtNum(stats.median)} | Std: ${fmtNum(stats.std)}`;
  analyticsTable.innerHTML = '';
  const rows = [
    ['Min', fmtNum(stats.min)],
    ['Max', fmtNum(stats.max)],
    ['Mean', fmtNum(stats.mean)],
    ['Median', fmtNum(stats.median)],
    ['Std Dev', fmtNum(stats.std)],
  ];
  rows.forEach(([label, val]) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${label}</td><td>${val}</td>`;
    analyticsTable.appendChild(tr);
  });
  renderBoxPlot(stats);
  renderHistogram(stats.histogram || []);
}

async function fillTranscriptionFromSelection() {
  const bookId = bookSelect.value;
  const chapterId = chapterSelect.value;
  const verseStart = parseInt(document.getElementById('verse-start').value, 10);
  const verseEnd = parseInt(document.getElementById('verse-end').value, 10);
  const version = versionSelect.value;
  if (!bookId || !chapterId || !version || Number.isNaN(verseStart) || Number.isNaN(verseEnd)) return;
  const bookName = bookMeta[bookId]?.name;
  const chapterNumber = parseInt(chapterSelect.options[chapterSelect.selectedIndex]?.textContent || '0', 10);
  if (!bookName || !chapterNumber) return;
  try {
    const res = await apiGet(
      `${apiBase}/verses?book=${encodeURIComponent(bookName)}&chapter=${chapterNumber}&start=${verseStart}&end=${verseEnd}&version=${encodeURIComponent(version)}`
    );
    if (res && res.text) {
      document.getElementById('transcription').value = res.text;
    }
  } catch (e) {
    // ignore fetch errors for now
  }
}

function updateVerseLimits() {
  const chapterId = chapterSelect.value;
  const max = chapterMeta[chapterId]?.verse_count;
  if (!max) return;
  const startInput = document.getElementById('verse-start');
  const endInput = document.getElementById('verse-end');
  startInput.max = max;
  endInput.max = max;
  if (parseInt(startInput.value, 10) > max) startInput.value = max;
  if (parseInt(endInput.value, 10) > max) endInput.value = max;
}

async function fetchAudio(id) {
  const res = await fetch(`${apiBase}/recordings/${id}/audio`, { headers: headers() });
  if (res.status === 401) return authFail();
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  document.getElementById('player').src = url;
  document.getElementById('player').play();
}

recordingsTable.onclick = async (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  const id = e.target.getAttribute('data-id');
  if (e.target.classList.contains('play')) {
    await fetchAudio(id);
    await loadRecordings();
  } else if (e.target.classList.contains('delete')) {
    await apiDelete(`${apiBase}/recordings/${id}`);
    await loadRecordings();
  }
};

bibleSelect.onchange = async () => { await loadBooks(); await loadRecordings(); await loadAnalytics(); await fillTranscriptionFromSelection(); };
bookSelect.onchange = async () => { await loadChapters(); await fillTranscriptionFromSelection(); };
chapterSelect.onchange = async () => { updateVerseLimits(); await fillTranscriptionFromSelection(); };
document.getElementById('verse-start').oninput = fillTranscriptionFromSelection;
document.getElementById('verse-end').oninput = fillTranscriptionFromSelection;
versionSelect.onchange = fillTranscriptionFromSelection;

document.getElementById('logout-btn').onclick = () => {
  localStorage.removeItem('token');
  window.location.href = '/static/login.html';
};

// Recording helpers
function updateTimer() {
  if (!startTime) return;
  const seconds = Math.round((Date.now() - startTime) / 1000);
  timerSpan.textContent = `${seconds}s`;
}

async function startRecording() {
  if (timerId) clearInterval(timerId);
  lastDuration = 0;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.onstop = () => {
    stream.getTracks().forEach(t => t.stop());
  };
  mediaRecorder.start();
  startTime = Date.now();
  document.getElementById('start-rec').disabled = true;
  document.getElementById('stop-rec').disabled = false;
  document.getElementById('upload-rec').disabled = true;
  recordMsg.textContent = 'Recording...';
  timerSpan.textContent = '0s';
  timerId = setInterval(updateTimer, 500);
}

function stopRecording() {
  if (!mediaRecorder) return;
  lastDuration = Math.round((Date.now() - startTime) / 1000);
  mediaRecorder.stop();
  mediaRecorder = null;
  if (timerId) clearInterval(timerId);
  timerId = null;
  startTime = null;
  timerSpan.textContent = `${lastDuration}s`;
  document.getElementById('start-rec').disabled = false;
  document.getElementById('stop-rec').disabled = true;
  document.getElementById('upload-rec').disabled = false;
  recordMsg.textContent = 'Recording stopped. Ready to upload.';
}

async function uploadRecording() {
  const blob = new Blob(chunks, { type: 'audio/webm' });
  const form = new FormData();
  form.append('bible_id', bibleSelect.value);
  form.append('chapter_id', chapterSelect.value);
  form.append('verse_index_start', document.getElementById('verse-start').value);
  form.append('verse_index_end', document.getElementById('verse-end').value);
  const duration = lastDuration || (startTime ? Math.round((Date.now() - startTime) / 1000) : 0);
  form.append('duration_seconds', duration || '');
  form.append('transcription_text', document.getElementById('transcription').value);
  form.append('file', blob, 'recording.webm');

  const res = await fetch(`${apiBase}/recordings`, {
    method: 'POST',
    headers: headers(),
    body: form
  });
  if (res.status === 401) return authFail();
  if (!res.ok) {
    recordMsg.textContent = 'Upload failed';
    return;
  }
  recordMsg.textContent = 'Upload successful';
  document.getElementById('upload-rec').disabled = true;
  await loadRecordings();
  await loadAnalytics();
}

document.getElementById('start-rec').onclick = startRecording;
document.getElementById('stop-rec').onclick = stopRecording;
document.getElementById('upload-rec').onclick = uploadRecording;

document.getElementById('download-btn').onclick = async () => {
  const res = await fetch(`${apiBase}/bibles/${bibleSelect.value}/download`, { headers: headers() });
  if (res.status === 401) return authFail();
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'bible.zip';
  a.click();
};

(async function init() {
  await loadVersions();
  await loadBibles();
})();
