// ==UserScript==
// @name         Unit Rollup JSON Extractor
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Extracts JSON from <script data-unit-rollup="..."> found on /resources page for a unit and displays it in a copyable, pretty-printed panel
// @author       Dan
// @match        https://studio.code.org/*
// @grant        GM_setClipboard
// @run-at       context-menu
// ==/UserScript==

(function () {
  'use strict';

  // ── Find the target element ──────────────────────────────────────────────
  const el = document.querySelector('script[data-unit-rollup]');
  if (!el) return; // Nothing to do on this page

  const raw = el.getAttribute('data-unit-rollup');
  let pretty = raw;
  let parseError = false;

  try {
    pretty = JSON.stringify(JSON.parse(raw), null, 2);
  } catch (e) {
    parseError = true;
    pretty = `// ⚠️ Could not parse as JSON — showing raw value:\n\n${raw}`;
  }

  // ── Inject styles ────────────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #urj-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.55);
      z-index: 2147483646;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: system-ui, sans-serif;
    }
    #urj-panel {
      background: #1e1e2e;
      color: #cdd6f4;
      border-radius: 12px;
      box-shadow: 0 24px 64px rgba(0,0,0,.6);
      width: min(860px, 92vw);
      max-height: 82vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #urj-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 18px;
      background: #181825;
      border-bottom: 1px solid #313244;
      flex-shrink: 0;
    }
    #urj-title {
      flex: 1;
      font-size: 14px;
      font-weight: 600;
      color: #cba6f7;
      letter-spacing: .02em;
    }
    #urj-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #a6e3a1;
      color: #1e1e2e;
      font-weight: 700;
    }
    #urj-badge.error {
      background: #f38ba8;
    }
    #urj-copy-btn {
      cursor: pointer;
      background: #cba6f7;
      color: #1e1e2e;
      border: none;
      border-radius: 7px;
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 700;
      transition: background .15s, transform .1s;
    }
    #urj-copy-btn:hover { background: #b4befe; }
    #urj-copy-btn:active { transform: scale(.96); }
    #urj-copy-btn.copied { background: #a6e3a1; }
    #urj-close-btn {
      cursor: pointer;
      background: transparent;
      border: none;
      color: #6c7086;
      font-size: 20px;
      line-height: 1;
      padding: 2px 4px;
      border-radius: 5px;
      transition: color .15s;
    }
    #urj-close-btn:hover { color: #f38ba8; }
    #urj-body {
      overflow: auto;
      flex: 1;
    }
    #urj-textarea {
      display: block;
      width: 100%;
      height: 100%;
      min-height: 340px;
      box-sizing: border-box;
      padding: 16px 18px;
      background: transparent;
      border: none;
      outline: none;
      resize: none;
      font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
      font-size: 13px;
      line-height: 1.65;
      color: #cdd6f4;
      white-space: pre;
      tab-size: 2;
    }
    #urj-footer {
      padding: 8px 18px;
      background: #181825;
      border-top: 1px solid #313244;
      font-size: 11px;
      color: #6c7086;
      flex-shrink: 0;
    }
  `;
  document.head.appendChild(style);

  // ── Build UI ─────────────────────────────────────────────────────────────
  const overlay = document.createElement('div');
  overlay.id = 'urj-overlay';

  overlay.innerHTML = `
    <div id="urj-panel">
      <div id="urj-header">
        <span id="urj-title">data-unit-rollup JSON</span>
        <span id="urj-badge" class="${parseError ? 'error' : ''}">${parseError ? 'PARSE ERROR' : 'VALID JSON'}</span>
        <button id="urj-copy-btn">Copy</button>
        <button id="urj-close-btn" title="Close">✕</button>
      </div>
      <div id="urj-body">
        <textarea id="urj-textarea" spellcheck="false">${pretty.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</textarea>
      </div>
      <div id="urj-footer">
        Press <kbd>Esc</kbd> to close · Click anywhere outside the panel to dismiss
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Decode HTML entities that got into the textarea value via innerHTML
  const textarea = document.getElementById('urj-textarea');
  textarea.value = pretty;

  // ── Copy button ──────────────────────────────────────────────────────────
  const copyBtn = document.getElementById('urj-copy-btn');
  copyBtn.addEventListener('click', () => {
    // Try GM_setClipboard first (no permissions dialog), fall back to clipboard API
    if (typeof GM_setClipboard === 'function') {
      GM_setClipboard(pretty, 'text');
      flashCopied();
    } else {
      navigator.clipboard.writeText(pretty).then(flashCopied).catch(() => {
        textarea.select();
        document.execCommand('copy');
        flashCopied();
      });
    }
  });

  function flashCopied() {
    copyBtn.textContent = '✓ Copied!';
    copyBtn.classList.add('copied');
    setTimeout(() => {
      copyBtn.textContent = 'Copy';
      copyBtn.classList.remove('copied');
    }, 1800);
  }

  // ── Close handlers ───────────────────────────────────────────────────────
  function closePanel() {
    overlay.remove();
    style.remove();
  }

  document.getElementById('urj-close-btn').addEventListener('click', closePanel);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closePanel();
  });

  document.addEventListener('keydown', function onKey(e) {
    if (e.key === 'Escape') {
      closePanel();
      document.removeEventListener('keydown', onKey);
    }
  });

})();