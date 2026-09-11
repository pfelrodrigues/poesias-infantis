import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, mkdtemp, cp, rm, rename, realpath } from 'node:fs/promises';
import { resolve, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VERSION = /^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$/;
const HASH = /^[a-f0-9]{64}$/;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const route = (id, piece, lang) => `${lang === 'en' ? '/en' : ''}/books/${id}/${lang === 'en' ? 'read' : 'ler'}/${piece}/`;

function safePath(path) {
  if (typeof path !== 'string' || !path || path.startsWith('/') || path.includes('\\') || path.includes('\0') || path.split('/').some(p => !p || p === '.' || p === '..') || /[:?#]/.test(path)) {
    throw new Error(`Invalid package path: ${path}`);
  }
  return path;
}

async function confinedFile(root, path) {
  const base = await realpath(root);
  const full = await realpath(resolve(base, safePath(path)));
  if (!full.startsWith(base + sep)) throw new Error(`Package path escapes root: ${path}`);
  return full;
}

function requireResource(book, path) {
  safePath(path);
  if (!Object.hasOwn(book.files, path)) throw new Error(`Undeclared resource: ${path}`);
  return `${book.assetBase}${path}`;
}

function resolveFragment(html, book, lang) {
  // These fragments are emitted by Pandoc, not arbitrary user-authored HTML.
  // Attribute-only changes keep the original prose and verse bytes untouched.
  if (/<\s*(?:script|style|iframe|object|embed|svg|math|form|input|button|textarea|select|link|meta|base)\b/i.test(html)) throw new Error('Active or unsupported chapter markup');
  return html.replace(/<[A-Za-z][A-Za-z0-9:-]*(?:\s+(?:[^"'<>]|"[^"]*"|'[^']*')*)?\s*\/?>/g, tag => {
    if (/\s(?:on[a-z]+|style|srcdoc)\s*=/i.test(tag)) throw new Error('Active chapter attribute');
    return tag
    .replace(/\bsrc="([^"]+)"/g, (_, src) => `src="${requireResource(book, src)}"`)
    .replace(/\bsrcset="([^"]+)"/g, (_, value) => `srcset="${value.split(',').map(part => {
      const [path, width, ...rest] = part.trim().split(/\s+/);
      if (rest.length || (width && !/^\d+w$/.test(width))) throw new Error('Invalid resource srcset');
      return `${requireResource(book, path)}${width ? ` ${width}` : ''}`;
    }).join(', ')}"`)
    .replace(/\bhref="([^"]+)"/g, (_, href) => {
      if (href.startsWith('book:')) {
        const [id, anchor] = href.slice(5).split('#');
        if (!book.pieces.some(piece => piece.id === id)) throw new Error(`Unknown chapter: ${id}`);
        return `href="${route(book.id, id, lang)}${anchor ? `#${anchor}` : ''}"`;
      }
      if (/^(https?:|mailto:|#)/.test(href)) return `href="${href}"`;
      return `href="${requireResource(book, href)}"`;
    });
  });
}

async function loadBook(root, entry) {
  if (!ID.test(entry.id) || !VERSION.test(entry.version) || !HASH.test(entry.sha256)) throw new Error('Invalid book lock entry');
  const manifestPath = await confinedFile(root, `${safePath(entry.directory)}/book.json`);
  const directory = dirname(manifestPath);
  const manifestBytes = await readFile(manifestPath);
  if (digest(manifestBytes) !== entry.sha256) throw new Error(`Manifest checksum mismatch: ${entry.id}`);
  const book = JSON.parse(manifestBytes);
  if (book.schema !== 1 || book.id !== entry.id || book.version !== entry.version || !book.title || !book.author || !/^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$/.test(book.language) || !Array.isArray(book.pieces) || !book.pieces.length || !book.files || typeof book.files !== 'object') {
    throw new Error(`Invalid book manifest: ${entry.id}`);
  }
  const files = new Map();
  for (const [path, hash] of Object.entries(book.files)) {
    safePath(path);
    if (!/^(?:chapters\/[a-z0-9.-]+\.html|images\/[a-z0-9.-]+\.(?:webp|png|jpe?g)|[a-z0-9.-]+\.(?:epub|pdf|json))$/.test(path)) throw new Error(`Unsupported or executable package file: ${path}`);
    if (!HASH.test(hash)) throw new Error(`Invalid file checksum: ${path}`);
    const full = await confinedFile(directory, path);
    const bytes = await readFile(full);
    if (digest(bytes) !== hash) throw new Error(`File checksum mismatch: ${entry.id}/${path}`);
    files.set(path, { full, bytes });
  }
  book.assetBase = `/books/assets/${book.id}/${book.version}/`;
  requireResource(book, book.epub);
  if (book.pdf) requireResource(book, book.pdf);
  for (const picture of [book.cover, book.comparison?.original, book.comparison?.restored].filter(Boolean)) {
    requireResource(book, picture.src);
    if (!(picture.width > 0 && picture.height > 0)) throw new Error('Image dimensions required');
  }
  const ids = new Set();
  for (const piece of book.pieces) {
    if (!ID.test(piece.id) || ids.has(piece.id) || !piece.title || !Array.isArray(piece.sections)) throw new Error(`Invalid/duplicate chapter: ${piece.id}`);
    ids.add(piece.id);
    requireResource(book, piece.html);
    for (const section of piece.sections) {
      if (!section.id || !section.title) throw new Error(`Invalid section: ${piece.id}`);
    }
  }
  for (const piece of book.pieces) {
    const original = files.get(piece.html).bytes.toString('utf8');
    const englishPath = piece.translations?.en?.html;
    if (englishPath && piece.original) throw new Error(`Original chapter cannot be translated: ${piece.id}`);
    if (englishPath) requireResource(book, englishPath);
    piece.htmlContent = resolveFragment(original, book, 'pt');
    piece.translations = { ...piece.translations, en: {
      ...piece.translations?.en,
      htmlContent: resolveFragment(englishPath ? files.get(englishPath).bytes.toString('utf8') : original, book, 'en'),
    } };
  }
  return { book, files };
}

async function writeJson(root, path, value) {
  const destination = resolve(root, path);
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, `${JSON.stringify(value, null, 2)}\n`);
}

export async function importBooks({ root = resolve(dirname(fileURLToPath(import.meta.url)), '..') } = {}) {
  const lock = JSON.parse(await readFile(resolve(root, 'data/books.lock.json'), 'utf8'));
  if (lock.schema !== 1 || !Array.isArray(lock.books)) throw new Error('Unsupported books lockfile');
  const seen = new Set();
  const editions = [];
  for (const entry of lock.books) {
    if (seen.has(entry.id)) throw new Error(`Duplicate book: ${entry.id}`);
    seen.add(entry.id);
    editions.push({ ...await loadBook(root, entry), presentation: entry.presentation });
  }
  // Validate all packages first; a bad update must not erase the last good import.
  const stage = await mkdtemp(resolve(root, '.generated-'));
  try {
    for (const { book, files, presentation } of editions) {
      await writeJson(stage, `data/books/${book.id}.json`, book);
      for (const lang of ['pt', 'en']) {
        if (presentation) {
          const page = presentation[lang];
          if (!page?.metadata?.description || typeof page.body !== 'string') throw new Error(`Missing presentation: ${book.id}/${lang}`);
          const metadata = { ...page.metadata, title: book.title, type: 'books', layout: 'book', bookID: book.id, translationKey: `book-${book.id}`, url: `${lang === 'en' ? '/en' : ''}/books/${book.id}/` };
          const destination = resolve(stage, `content/books/${book.id}/_index.${lang}.md`);
          await mkdir(dirname(destination), { recursive: true });
          await writeFile(destination, `${JSON.stringify(metadata, null, 2)}\n\n${page.body}`);
        }
        await writeJson(stage, `content/books/${book.id}/reader/_index.${lang}.md`, {
          title: book.title, build: { render: 'never', list: 'never' },
        });
      }
      for (const piece of book.pieces) {
        for (const lang of ['pt', 'en']) {
          const title = lang === 'en' && !piece.original ? piece.translations?.en?.title || piece.title : piece.title;
          await writeJson(stage, `content/books/${book.id}/reader/${piece.id}.${lang}.md`, {
            title, type: 'books', layout: 'reader', bookID: book.id, pieceID: piece.id,
            translationKey: `reader-${book.id}-${piece.id}`, url: route(book.id, piece.id, lang),
            description: piece.original
              ? (lang === 'en' ? `${title}, from ${book.title} by ${book.author}. Original text in ${book.language === 'pt' ? 'Portuguese' : book.language}.` : `${title}, de ${book.title}, de ${book.author}. Texto da edição original.`)
              : (lang === 'en' ? `Editorial notes for ${book.title}, by ${book.author}.` : `Notas editoriais de ${book.title}, de ${book.author}.`),
            contentLanguage: lang === 'en' && !piece.original && piece.translations?.en?.html ? 'en' : book.language,
            original: piece.original, weight: book.pieces.indexOf(piece) + 1,
          });
        }
      }
      for (const [path, { full }] of files) {
        if (path.startsWith('chapters/')) continue;
        const destination = resolve(stage, `static${book.assetBase}${path}`);
        await mkdir(dirname(destination), { recursive: true });
        await cp(full, destination);
      }
    }
    await rm(resolve(root, '.generated'), { recursive: true, force: true });
    await rename(stage, resolve(root, '.generated'));
  } finally {
    await rm(stage, { recursive: true, force: true });
  }
  return editions.map(({ book }) => ({ id: book.id, version: book.version, pieces: book.pieces.length }));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    for (const book of await importBooks()) console.log(`Imported ${book.id} ${book.version}: ${book.pieces} pieces, PT/EN`);
  } catch (error) {
    console.error(`Books import failed: ${error.message}`);
    process.exitCode = 1;
  }
}
