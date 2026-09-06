import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const destination = resolve(root, process.argv[2] || 'public');
const origin = 'https://pfelrodrigues.com.br';
const errors = [];
const unescape = value => value.replaceAll('&amp;', '&').replaceAll('&#39;', "'").replaceAll('&quot;', '"');
const attributes = tag => Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m => [m[1], unescape(m[2] ?? m[3] ?? m[4])]));

async function walk(path) {
  const entries = await readdir(path, { withFileTypes: true });
  return (await Promise.all(entries.map(e => e.isDirectory() ? walk(resolve(path, e.name)) : resolve(path, e.name)))).flat();
}

const htmlFiles = (await walk(destination)).filter(path => path.endsWith('.html'));
const pages = new Map();
for (const path of htmlFiles) {
  const html = await readFile(path, 'utf8');
  const url = path.slice(destination.length).replace(/index\.html$/, '');
  pages.set(url, { html, path, ids: new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1])) });
}

async function verifyTarget(value, from, resource = false) {
  if (!value || /^(mailto:|tel:)/.test(value)) return;
  let url;
  try { url = new URL(value, `${origin}${from}`); } catch { throw new Error(`Invalid URL ${value}`); }
  if (url.origin !== origin) {
    assert(!resource, `External resource ${value}`);
    return;
  }
  if (url.pathname.startsWith('/_vercel/insights/') || ['/', '/en/'].includes(url.pathname)) return;
  const pathname = decodeURIComponent(url.pathname);
  const target = resolve(destination, `.${pathname}`);
  assert(target.startsWith(destination + '/') || target === destination, 'Path escaped public directory');
  const info = await stat(target).catch(() => null);
  assert(info, `Missing local target ${value}`);
  if (info.isDirectory()) assert(await stat(resolve(target, 'index.html')).catch(() => null), `Missing index ${value}`);
  if (url.hash && pages.has(pathname)) {
    assert(pages.get(pathname).ids.has(decodeURIComponent(url.hash.slice(1))), `Missing anchor ${value}`);
  }
}

for (const [url, { html }] of pages) {
  try {
    if (/<meta\b[^>]*http-equiv="refresh"/i.test(html)) {
      const refresh = [...html.matchAll(/<meta\b[^>]*>/g)].map(m => attributes(m[0])).find(a => a['http-equiv']?.toLowerCase() === 'refresh');
      const target = refresh?.content?.match(/url=(.+)$/i)?.[1];
      assert(target, 'Redirect target required');
      await verifyTarget(target, url);
      continue;
    }
    assert.equal((html.match(/<h1\b/g) || []).length, 1, 'Exactly one H1 required');
    assert(!/\s(?:style|on\w+)\s*=/i.test(html), 'Inline style/event handler violates CSP');
    const language = html.match(/<html\b[^>]*lang="([^"]+)"/)?.[1];
    assert.equal(language, url.startsWith('/en/') ? 'en' : 'pt-BR', 'Wrong interface language');
    const tags = [...html.matchAll(/<(?:a|link|img|script)\b[^>]*>/g)].map(m => ({ tag: m[0], attrs: attributes(m[0]) }));
    for (const { tag, attrs } of tags) {
      if (attrs.src && !attrs.src.startsWith('/_vercel/') && !attrs.src.startsWith('/books/')) throw new Error(`Resource outside library namespace: ${attrs.src}`);
      if (attrs.src) await verifyTarget(attrs.src, url, true);
      if (attrs.srcset) for (const part of attrs.srcset.split(',')) await verifyTarget(part.trim().split(/\s+/)[0], url, true);
      if (attrs.href) await verifyTarget(attrs.href, url, tag.startsWith('<link') && attrs.rel === 'stylesheet');
      if (tag.startsWith('<img')) assert(+attrs.width > 0 && +attrs.height > 0 && Object.hasOwn(attrs, 'alt'), 'Image dimensions/alt required');
      if (tag.startsWith('<script')) assert(attrs.src, 'Inline script violates CSP');
    }
    if (url.includes('/books/')) {
      const canonical = tags.find(t => t.attrs.rel === 'canonical')?.attrs.href;
      assert.equal(canonical, `${origin}${url}`, 'Wrong canonical');
      const ptUrl = url.replace(/^\/en\//, '/').replace('/read/', '/ler/');
      const enUrl = `/en${ptUrl}`.replace('/ler/', '/read/');
      for (const [lang, expected] of [['pt-BR', ptUrl], ['en', enUrl], ['x-default', ptUrl]]) {
        assert.equal(tags.find(t => t.attrs.hreflang === lang)?.attrs.href, `${origin}${expected}`, `Wrong hreflang ${lang}`);
      }
      assert(html.includes('<meta name="description" content="'), 'Missing description');
      assert(!html.includes('property="og:type" content="profile"'), 'Book OG is a personal profile');
    }
  } catch (error) { errors.push(`${url}: ${error.message}`); }
}

const lock = JSON.parse(await readFile(resolve(root, 'data/books.lock.json'), 'utf8'));
for (const entry of lock.books) {
  const book = JSON.parse(await readFile(resolve(root, '.generated/data/books', `${entry.id}.json`), 'utf8'));
  for (const piece of book.pieces) {
    for (const lang of ['pt', 'en']) {
      const url = `${lang === 'en' ? '/en' : ''}/books/${book.id}/${lang === 'en' ? 'read' : 'ler'}/${piece.id}/`;
      const page = pages.get(url);
      if (!page) errors.push(`${url}: Missing chapter page`);
      else if (piece.original && !page.html.includes(`id="reading-content" lang="${book.language}"`)) errors.push(`${url}: Original reading content must declare its source language`);
    }
  }
}

assert(pages.has('/books/') && pages.has('/en/books/'), 'Missing home/catalog language pair');
const fonts = (await walk(resolve(destination, 'books/ui/fonts'))).filter(path => path.endsWith('.woff2'));
assert.equal(fonts.length, 3, 'Original self-hosted font set changed');
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log(`Verified ${pages.size} HTML pages: routes, local resources, anchors, PT/EN, metadata, CSP markup and 3 local fonts.`);
}
