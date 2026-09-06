(() => {
  "use strict";

  const storage = {
    get(key) {
      try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Reading works without storage. */ }
    }
  };
  const settingsKey = "books:reader:v1";
  const saved = storage.get(settingsKey);
  const settings = {
    theme: ["system", "light", "dark", "paper"].includes(saved?.theme) ? saved.theme : "system",
    font: ["mono", "serif"].includes(saved?.font) ? saved.font : "mono",
    size: Number.isInteger(saved?.size) && saved.size >= -1 && saved.size <= 3 ? saved.size : 0
  };
  const content = document.getElementById("reading-content");
  const fontChoice = document.getElementById("font-choice");
  const themeChoice = document.getElementById("theme-choice");
  const sizeButtons = document.querySelectorAll("[data-size-change]");

  function applySettings() {
    if (settings.theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = settings.theme;
    if (content) {
      content.dataset.font = settings.font;
      content.dataset.size = String(settings.size);
    }
    if (fontChoice) fontChoice.value = settings.font;
    if (themeChoice) themeChoice.value = settings.theme;
    sizeButtons.forEach(button => {
      button.disabled = Number(button.dataset.sizeChange) < 0 ? settings.size <= -1 : settings.size >= 3;
    });
  }

  applySettings();
  document.querySelectorAll("[data-reader-control]").forEach(control => { control.hidden = false; });
  fontChoice?.addEventListener("change", () => {
    if (!["mono", "serif"].includes(fontChoice.value)) return;
    settings.font = fontChoice.value;
    applySettings();
    storage.set(settingsKey, settings);
  });
  themeChoice?.addEventListener("change", () => {
    if (!["system", "light", "dark", "paper"].includes(themeChoice.value)) return;
    settings.theme = themeChoice.value;
    applySettings();
    storage.set(settingsKey, settings);
  });
  sizeButtons.forEach(button => button.addEventListener("click", () => {
    settings.size = Math.max(-1, Math.min(3, settings.size + Number(button.dataset.sizeChange)));
    applySettings();
    storage.set(settingsKey, settings);
  }));

  function validHash(value) {
    return typeof value === "string" && /^#[^\s\u0000-\u001f]{1,200}$/.test(value);
  }
  function updateLanguageLinks() {
    document.querySelectorAll("[data-language-link]").forEach(link => {
      const target = new URL(link.href, location.origin);
      if (target.origin !== location.origin) return;
      target.hash = location.hash;
      link.href = target.pathname + target.search + target.hash;
    });
  }
  updateLanguageLinks();
  window.addEventListener("hashchange", updateLanguageLinks);

  document.querySelectorAll("[data-resume-book]").forEach(link => {
    const last = storage.get("books:position:v1:" + link.dataset.resumeBook);
    const pieces = link.dataset.pieceIds.split(",");
    if (!last || typeof last.piece !== "string" || !pieces.includes(last.piece)) return;
    const target = new URL(link.dataset.readerRoot + encodeURIComponent(last.piece) + "/", location.origin);
    if (target.origin !== location.origin) return;
    if (validHash(last.hash)) target.hash = last.hash;
    link.href = target.pathname + target.hash;
    link.hidden = false;
  });

  const { bookId, pieceId } = document.body.dataset;
  if (!content || !bookId || !pieceId) return;
  const positionKey = "books:position:v1:" + bookId;
  // Stable enhancement-only anchors also let long prose resume within a piece.
  const blocks = Array.from(content.querySelectorAll("h2, h3, p, .line-block"));
  blocks.forEach((block, index) => {
    if (!block.id) block.id = "reading-p-" + (index + 1);
  });
  function savePosition(hash = location.hash) {
    storage.set(positionKey, { piece: pieceId, hash: validHash(hash) ? hash : "" });
  }
  function saveVisiblePosition() {
    let visible = null;
    for (const block of blocks) {
      if (block.getBoundingClientRect().top <= window.innerHeight * 0.35) visible = block;
      else break;
    }
    savePosition(visible ? "#" + visible.id : location.hash);
  }
  if (location.hash.startsWith("#reading-p-")) {
    document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }
  savePosition();
  let scrollTimer;
  window.addEventListener("scroll", () => {
    window.clearTimeout(scrollTimer);
    scrollTimer = window.setTimeout(saveVisiblePosition, 180);
  }, { passive: true });
  window.addEventListener("hashchange", () => savePosition());
  window.addEventListener("pagehide", saveVisiblePosition);
})();
