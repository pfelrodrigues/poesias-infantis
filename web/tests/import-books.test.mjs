import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { importBooks } from '../scripts/import-books.mjs';

const digest = value => createHash('sha256').update(value).digest('hex');

async function fixture(t, change = () => {}) {
  const root = await mkdtemp(join(tmpdir(), 'books-import-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const files = {
    'chapters/primeiro.html': '<div class="line-block">Ó verso original!<br />\nOutra linha.</div><img src="images/capa.webp" width="20" height="30" alt="Capa"><a href="book:segundo#nota">seguir</a>',
    'chapters/segundo.html': '<h2 id="nota">Nota</h2><p>Texto original.</p>',
    'images/capa.webp': 'test-image',
    'amostra.epub': 'test-epub',
  };
  const book = {
    schema: 1, id: 'amostra', version: '1.0.0', source_commit: '1'.repeat(40),
    title: 'Amostra', author: 'Autor', year: 1904, language: 'pt',
    cover: { src: 'images/capa.webp', width: 20, height: 30, alt: 'Capa' },
    epub: 'amostra.epub',
    pieces: [
      { id: 'primeiro', title: 'Primeiro', html: 'chapters/primeiro.html', original: true, sections: [] },
      { id: 'segundo', title: 'Segundo', html: 'chapters/segundo.html', original: true, sections: [{ id: 'nota', title: 'Nota' }] },
    ], files: Object.fromEntries(Object.entries(files).map(([p, data]) => [p, digest(data)])),
  };
  change(book, files);
  const directory = 'vendor/books/amostra/1.0.0';
  for (const [path, data] of Object.entries(files)) {
    await mkdir(join(root, directory, path, '..'), { recursive: true });
    await writeFile(join(root, directory, path), data);
  }
  const manifest = JSON.stringify(book);
  await writeFile(join(root, directory, 'book.json'), manifest);
  await mkdir(join(root, 'data'));
  await writeFile(join(root, 'data/books.lock.json'), JSON.stringify({ schema: 1, books: [{ id: book.id, version: book.version, directory, sha256: digest(manifest) }] }));
  return { root, directory };
}

test('imports paired reader pages, shared resources and unchanged original words', async t => {
  const { root } = await fixture(t);
  await importBooks({ root });
  const pt = JSON.parse(await readFile(join(root, '.generated/content/books/amostra/reader/primeiro.pt.md'), 'utf8'));
  const en = JSON.parse(await readFile(join(root, '.generated/content/books/amostra/reader/primeiro.en.md'), 'utf8'));
  assert.equal(pt.url, '/books/amostra/ler/primeiro/');
  assert.equal(en.url, '/en/books/amostra/read/primeiro/');
  assert.equal(pt.translationKey, en.translationKey);
  assert.equal(en.contentLanguage, 'pt');
  const book = JSON.parse(await readFile(join(root, '.generated/data/books/amostra.json'), 'utf8'));
  assert.match(book.pieces[0].htmlContent, /Ó verso original!<br \/>\nOutra linha\./);
  assert.match(book.pieces[0].htmlContent, /src="\/books\/assets\/amostra\/1.0.0\/images\/capa.webp"/);
  assert.match(book.pieces[0].translations.en.htmlContent, /href="\/en\/books\/amostra\/read\/segundo\/#nota"/);
  assert.equal(await readFile(join(root, '.generated/static/books/assets/amostra/1.0.0/amostra.epub'), 'utf8'), 'test-epub');
});

test('corrupted artifact aborts import and preserves the previous generated site', async t => {
  const { root, directory } = await fixture(t);
  await importBooks({ root });
  await writeFile(join(root, '.generated/sentinel'), 'previous build');
  await writeFile(join(root, directory, 'amostra.epub'), 'corrupted');
  await assert.rejects(importBooks({ root }), /checksum/i);
  assert.equal(await readFile(join(root, '.generated/sentinel'), 'utf8'), 'previous build');
});

test('manifest changes require an explicit lockfile update', async t => {
  const { root, directory } = await fixture(t);
  await writeFile(join(root, directory, 'book.json'), '{}');
  await assert.rejects(importBooks({ root }), /checksum/i);
});

test('rejects package paths that escape the distribution', async t => {
  const { root } = await fixture(t, book => { book.files['../outside'] = '0'.repeat(64); });
  await assert.rejects(importBooks({ root }), /path|caminho/i);
});

test('rejects undeclared image resources even when chapter checksum is valid', async t => {
  const { root } = await fixture(t, (book, files) => {
    files['chapters/primeiro.html'] = '<img src="images/missing.webp" alt="missing">';
    book.files['chapters/primeiro.html'] = digest(files['chapters/primeiro.html']);
  });
  await assert.rejects(importBooks({ root }), /resource|recurso/i);
});

test('imports another book using metadata without changing site code', async t => {
  const { root } = await fixture(t, book => { book.id = 'prosa'; book.title = 'Livro em prosa'; });
  await importBooks({ root });
  const book = JSON.parse(await readFile(join(root, '.generated/data/books/prosa.json'), 'utf8'));
  assert.equal(book.title, 'Livro em prosa');
  const en = JSON.parse(await readFile(join(root, '.generated/content/books/prosa/reader/primeiro.en.md'), 'utf8'));
  assert.equal(en.url, '/en/books/prosa/read/primeiro/');
});

test('preserves literal attribute-like prose while resolving actual image tags', async t => {
  const literal = '<p>O texto cita href="book:primeiro" e src="images/capa.webp".</p>';
  const { root } = await fixture(t, (book, files) => {
    files['chapters/primeiro.html'] = `${literal}<img src="images/capa.webp" alt="Capa">`;
    book.files['chapters/primeiro.html'] = digest(files['chapters/primeiro.html']);
  });
  await importBooks({ root });
  const book = JSON.parse(await readFile(join(root, '.generated/data/books/amostra.json'), 'utf8'));
  assert(book.pieces[0].htmlContent.startsWith(literal));
  assert.match(book.pieces[0].htmlContent, /<img src="\/books\/assets\//);
});

test('rejects executable files even with valid hashes', async t => {
  const { root } = await fixture(t, (book, files) => {
    files['scripts/book.js'] = 'alert(1)';
    files['chapters/primeiro.html'] = '<script src="scripts/book.js"></script>';
    for (const path of ['scripts/book.js', 'chapters/primeiro.html']) book.files[path] = digest(files[path]);
  });
  await assert.rejects(importBooks({ root }), /executable|active|unsupported/i);
});

test('rejects active markup inside a checksummed chapter', async t => {
  const { root } = await fixture(t, (book, files) => {
    files['chapters/primeiro.html'] = '<iframe src="chapters/segundo.html"></iframe>';
    book.files['chapters/primeiro.html'] = digest(files['chapters/primeiro.html']);
  });
  await assert.rejects(importBooks({ root }), /active|unsupported/i);
});
