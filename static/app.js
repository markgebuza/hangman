// Hangman browser client.
//
// This file contains NO game rules. Every game decision (is a letter
// correct, is the game won or lost, what the word is) is made by the server.
// The client only sends requests with fetch() and renders the JSON it gets
// back. The hidden word is never stored here while a game is in progress.

"use strict";

const ALPHABET = "abcdefghijklmnopqrstuvwxyz";
const STORAGE_KEY = "hangman.game_id";

const els = {
  form: document.getElementById("new-game-form"),
  difficulty: document.getElementById("difficulty"),
  newGame: document.getElementById("new-game"),
  pattern: document.getElementById("pattern"),
  remaining: document.getElementById("remaining"),
  guessed: document.getElementById("guessed"),
  incorrect: document.getElementById("incorrect"),
  message: document.getElementById("message"),
  keyboard: document.getElementById("keyboard"),
  parts: Array.from(document.querySelectorAll("#gallows .part")),
};

// Only what the UI needs between requests. `state` is the last server
// response, used to know which keys to disable and whether play is over.
let gameId = null;
let state = null;
let busy = false;

// ------------------------------------------------------------------ HTTP

async function api(method, url, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  }
  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    // Non-JSON response (e.g. a proxy error page) – handled below.
  }
  if (!response.ok) {
    const msg = (data && data.error) || `Request failed (HTTP ${response.status}).`;
    throw new ApiError(msg, response.status);
  }
  return data;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// ------------------------------------------------------------------ actions

async function startNewGame() {
  if (busy) return;
  setBusy(true);
  showMessage("");
  try {
    const data = await api("POST", "/api/games", { difficulty: els.difficulty.value });
    gameId = data.game_id;
    saveGameId(gameId);
    render(data);
  } catch (err) {
    showMessage(err.message, "error");
  } finally {
    setBusy(false);
  }
}

async function guessLetter(letter) {
  if (busy || !gameId || !state || state.status !== "playing") return;
  setBusy(true);
  try {
    const data = await api("POST", `/api/games/${encodeURIComponent(gameId)}/guess`, { letter });
    render(data);
  } catch (err) {
    if (err.status === 404) {
      // The server forgot the game (e.g. it restarted). Nothing to recover.
      gameId = null;
      state = null;
      saveGameId(null);
      updateKeyboard();
      showMessage("This game no longer exists on the server (it may have restarted). Start a new game.", "error");
    } else {
      showMessage(err.message, "error");
    }
  } finally {
    setBusy(false);
  }
}

async function resumeOrStart() {
  const saved = loadGameId();
  if (saved) {
    try {
      const data = await api("GET", `/api/games/${encodeURIComponent(saved)}`);
      gameId = data.game_id;
      if (data.difficulty) els.difficulty.value = data.difficulty;
      render(data);
      return;
    } catch (err) {
      saveGameId(null); // stale id: fall through to a fresh game
    }
  }
  await startNewGame();
}

// ------------------------------------------------------------------ rendering

function render(data) {
  state = data;
  els.pattern.textContent = data.pattern;
  els.remaining.textContent = String(data.remaining_guesses);
  els.guessed.textContent = data.guessed_letters.length ? data.guessed_letters.join(" ") : "–";
  els.incorrect.textContent = data.incorrect_letters.length ? data.incorrect_letters.join(" ") : "–";

  const wrong = data.incorrect_letters.length;
  els.parts.forEach((part, i) => part.classList.toggle("shown", i < wrong));

  if (data.status === "won") {
    showMessage(`You won! The word was "${data.word}".`, "won");
  } else if (data.status === "lost") {
    showMessage(`You lost. The word was "${data.word}".`, "lost");
  } else {
    showMessage("");
  }
  updateKeyboard();
}

function updateKeyboard() {
  const guessed = new Set(state ? state.guessed_letters : []);
  const incorrect = new Set(state ? state.incorrect_letters : []);
  const playing = Boolean(state && state.status === "playing");
  for (const key of els.keyboard.children) {
    const letter = key.dataset.letter;
    key.disabled = busy || !playing || guessed.has(letter);
    key.classList.toggle("incorrect", incorrect.has(letter));
    key.classList.toggle("correct", guessed.has(letter) && !incorrect.has(letter));
  }
}

function showMessage(text, kind) {
  els.message.textContent = text;
  els.message.className = "message" + (kind ? " " + kind : "");
}

function setBusy(value) {
  busy = value;
  els.newGame.disabled = value;
  updateKeyboard();
}

function buildKeyboard() {
  for (const letter of ALPHABET) {
    const key = document.createElement("button");
    key.type = "button";
    key.className = "key";
    key.textContent = letter;
    key.dataset.letter = letter;
    key.setAttribute("aria-label", `Guess ${letter.toUpperCase()}`);
    key.addEventListener("click", () => guessLetter(letter));
    els.keyboard.appendChild(key);
  }
}

// ------------------------------------------------------------------ storage

function saveGameId(id) {
  try {
    if (id) sessionStorage.setItem(STORAGE_KEY, id);
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch (err) { /* storage unavailable – ignore */ }
}

function loadGameId() {
  try { return sessionStorage.getItem(STORAGE_KEY); } catch (err) { return null; }
}

// ------------------------------------------------------------------ events

function onKeyDown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const tag = event.target && event.target.tagName;
  if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;
  const letter = event.key.toLowerCase();
  if (letter.length !== 1 || !ALPHABET.includes(letter)) return;
  // Ignore physical keys once the game is over or before it has started,
  // and keys for letters that are already guessed.
  if (!state || state.status !== "playing" || state.guessed_letters.includes(letter)) return;
  event.preventDefault();
  guessLetter(letter);
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault(); // no page reload
  startNewGame();
});
document.addEventListener("keydown", onKeyDown);

buildKeyboard();
resumeOrStart();
