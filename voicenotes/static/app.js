import { startRecording } from "/recorder.js";

const MAX_RECORD_SECONDS = 25;
const STATUS_BASE = "mt-4 min-h-6 text-sm";
const STATUS_OK = "text-emerald-700 dark:text-emerald-400";
const STATUS_ERROR = "text-red-600 dark:text-red-400";

const noteForm = document.querySelector("#note-form");
const titleInput = document.querySelector("#title");
const bodyInput = document.querySelector("#body");
const folderSelect = document.querySelector("#folder");
const folderForm = document.querySelector("#folder-form");
const folderPathInput = document.querySelector("#folder-path");
const folderNameInput = document.querySelector("#folder-name");
const folderList = document.querySelector("#folder-list");
const statusLine = document.querySelector("#status");
const recordButton = document.querySelector("#record");
const recordLabel = document.querySelector("#record-label");
const recordTimer = document.querySelector("#record-timer");

let session = null;
let stopTimer = null;
let tickTimer = null;
let recordStartedAt = 0;

function showStatus(text, isError = false) {
  statusLine.textContent = text;
  statusLine.className = `${STATUS_BASE} ${isError ? STATUS_ERROR : STATUS_OK}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json" },
  });
  if (response.status === 204) {
    return null;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Check the form values.");
  }
  return data;
}

async function transcribe(wav) {
  const response = await fetch("/api/transcriptions", {
    method: "POST",
    headers: { "Content-Type": "audio/wav" },
    body: wav,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : `Transcription failed (${response.status}).`);
  }
  return data.text;
}

function folderItem(folder) {
  const item = document.createElement("li");
  item.className = "flex items-start justify-between gap-3 rounded-lg border border-stone-200 p-3 dark:border-stone-800";

  const text = document.createElement("div");
  text.className = "min-w-0";

  const name = document.createElement("p");
  name.className = "truncate font-medium";
  name.textContent = folder.name;

  const path = document.createElement("p");
  path.className = "break-all text-xs text-stone-500 dark:text-stone-400";
  path.textContent = folder.path;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "btn-quiet shrink-0";
  remove.textContent = "Remove";
  remove.title = "Remove from the list. Files stay on disk.";
  remove.addEventListener("click", () => removeFolder(folder));

  text.append(name, path);
  item.append(text, remove);
  return item;
}

function renderFolders(folders) {
  folderSelect.replaceChildren(...folders.map((folder) => new Option(folder.name, folder.id)));
  if (folders.length === 0) {
    const empty = document.createElement("li");
    empty.className = "rounded-lg bg-stone-100 p-3 text-sm text-stone-500 dark:bg-stone-800 dark:text-stone-400";
    empty.textContent = "No folders yet. Add one below.";
    folderList.replaceChildren(empty);
    return;
  }
  folderList.replaceChildren(...folders.map(folderItem));
}

async function loadFolders() {
  const { items } = await api("/api/folders");
  renderFolders(items);
}

async function removeFolder(folder) {
  if (!confirm(`Remove "${folder.name}" from the list? Files stay on disk.`)) {
    return;
  }
  try {
    await api(`/api/folders/${folder.id}`, { method: "DELETE" });
    await loadFolders();
    showStatus("Folder removed from the list.");
  } catch (error) {
    showStatus(error.message, true);
  }
}

function setRecording(recording) {
  recordButton.classList.toggle("recording", recording);
  recordButton.setAttribute("aria-pressed", String(recording));
  recordLabel.textContent = recording ? "Stop" : "Record";
  recordTimer.setAttribute("aria-hidden", String(!recording));
  if (!recording) {
    recordTimer.textContent = "";
  }
}

function updateTimer() {
  const seconds = Math.floor((Date.now() - recordStartedAt) / 1000);
  recordTimer.textContent = `${seconds} / ${MAX_RECORD_SECONDS} s`;
}

// Adds the transcript to the note, after any text already there.
function appendTranscript(text) {
  bodyInput.value = [bodyInput.value.trimEnd(), text].filter(Boolean).join(" ");
}

async function beginRecording() {
  recordButton.disabled = true;
  try {
    session = await startRecording();
  } catch (error) {
    showStatus(`Microphone unavailable: ${error.message}`, true);
    recordButton.disabled = false;
    return;
  }
  recordButton.disabled = false;
  recordStartedAt = Date.now();
  setRecording(true);
  updateTimer();
  tickTimer = setInterval(updateTimer, 500);
  stopTimer = setTimeout(finishRecording, MAX_RECORD_SECONDS * 1000);
  showStatus(`Recording. Click Stop, or it stops after ${MAX_RECORD_SECONDS} seconds.`);
}

async function finishRecording() {
  if (!session) {
    return;
  }
  const active = session;
  session = null;
  clearTimeout(stopTimer);
  clearInterval(tickTimer);
  setRecording(false);
  recordButton.disabled = true;
  showStatus("Transcribing...");
  try {
    const wav = await active.stop();
    const text = await transcribe(wav);
    if (text) {
      appendTranscript(text);
      showStatus("Transcribed. Review the text, then save.");
    } else {
      showStatus("No speech found in the clip.", true);
    }
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    recordButton.disabled = false;
  }
}

recordButton.addEventListener("click", () => {
  if (session) {
    finishRecording();
  } else {
    beginRecording();
  }
});

noteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!folderSelect.value) {
    showStatus("Add a folder first.", true);
    return;
  }
  try {
    const result = await api("/api/notes", {
      method: "POST",
      body: JSON.stringify({
        folder_id: folderSelect.value,
        title: titleInput.value,
        body: bodyInput.value,
      }),
    });
    titleInput.value = "";
    bodyInput.value = "";
    showStatus(`Saved ${result.file}`);
  } catch (error) {
    showStatus(error.message, true);
  }
});

folderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/folders", {
      method: "POST",
      body: JSON.stringify({
        path: folderPathInput.value,
        name: folderNameInput.value || null,
      }),
    });
    folderForm.reset();
    await loadFolders();
    showStatus("Folder added.");
  } catch (error) {
    showStatus(error.message, true);
  }
});

loadFolders().catch((error) => showStatus(error.message, true));
