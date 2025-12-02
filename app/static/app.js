const apiBase = '/api';
const token = localStorage.getItem('token');
if (!token) window.location.href = '/static/login.html';

const headers = () => ({ 'Authorization': `Bearer ${token}` });

const bibleSelect = document.getElementById('bible-select');
const bookSelect = document.getElementById('book-select');
const chapterSelect = document.getElementById('chapter-select');
const recordingsTable = document.querySelector('#recordings-table tbody');
const recordMsg = document.getElementById('record-msg');
const timerSpan = document.getElementById('timer');
let mediaRecorder, chunks = [], startTime;

async function apiGet(path) {
  const res = await fetch(path, { headers: headers() });
  if (!res.ok) throw new Error('Request failed');
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(path, { method: 'DELETE', headers: headers() });
  if (!res.ok) throw new Error('Delete failed');
}

async function apiPut(path, data) {
  const res = await fetch(path, {
    method: 'PUT',
    headers: { ...headers(), 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
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

async function loadBibles() {
  const bibles = await apiGet(`${apiBase}/bibles`);
  fillOptions(bibleSelect, bibles, b => ({ value: b.bible_id, label: `${b.name} (${b.language})` }));
  if (bibleSelect.value) {
    await loadBooks();
    await loadRecordings();
  }
}

async function loadBooks() {
  const bibleId = bibleSelect.value;
  const books = await apiGet(`${apiBase}/bibles/${bibleId}/books`);
  fillOptions(bookSelect, books, b => ({ value: b.Books.book_id, label: b.CanonBooks.canon_book_name }));
  if (bookSelect.value) await loadChapters();
}

async function loadChapters() {
  const bookId = bookSelect.value;
  const chapters = await apiGet(`${apiBase}/books/${bookId}/chapters`);
  fillOptions(chapterSelect, chapters, c => ({ value: c.Chapters.chapter_id, label: c.CanonChapters.canon_book_chapter }));
}

async function loadRecordings() {
  const bibleId = bibleSelect.value;
  const rows = await apiGet(`${apiBase}/bibles/${bibleId}/recordings`);
  recordingsTable.innerHTML = '';
  rows.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.book_name}</td>
      <td>${row.chapter_number}</td>
      <td>${row.verse_start}-${row.verse_end}</td>
      <td>${row.date_recorded}</td>
      <td>${row.accessed_count}</td>
      <td>${row.duration_seconds || ''}</td>
      <td>${row.computed_wpm ? row.computed_wpm.toFixed(2) : ''}</td>
      <td>
        <button data-id="${row.recording_id}" class="play">Play</button>
        <button data-id="${row.recording_id}" class="delete">Delete</button>
      </td>`;
    recordingsTable.appendChild(tr);
  });
}

async function fetchAudio(id) {
  const res = await fetch(`${apiBase}/recordings/${id}/audio`, { headers: headers() });
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

bibleSelect.onchange = async () => { await loadBooks(); await loadRecordings(); };
bookSelect.onchange = loadChapters;

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
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.start();
  startTime = Date.now();
  document.getElementById('start-rec').disabled = true;
  document.getElementById('stop-rec').disabled = false;
  recordMsg.textContent = 'Recording...';
  setInterval(updateTimer, 500);
}

function stopRecording() {
  if (!mediaRecorder) return;
  mediaRecorder.stop();
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
  const duration = startTime ? Math.round((Date.now() - startTime) / 1000) : undefined;
  form.append('duration_seconds', duration || '');
  form.append('transcription_text', document.getElementById('transcription').value);
  form.append('file', blob, 'recording.webm');

  const res = await fetch(`${apiBase}/recordings`, {
    method: 'POST',
    headers: headers(),
    body: form
  });
  if (!res.ok) {
    recordMsg.textContent = 'Upload failed';
    return;
  }
  recordMsg.textContent = 'Upload successful';
  document.getElementById('upload-rec').disabled = true;
  await loadRecordings();
}

document.getElementById('start-rec').onclick = startRecording;
document.getElementById('stop-rec').onclick = stopRecording;
document.getElementById('upload-rec').onclick = uploadRecording;

document.getElementById('download-btn').onclick = async () => {
  const res = await fetch(`${apiBase}/bibles/${bibleSelect.value}/download`, { headers: headers() });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'bible.zip';
  a.click();
};

loadBibles();
