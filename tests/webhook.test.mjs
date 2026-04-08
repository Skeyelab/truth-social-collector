import assert from 'node:assert/strict';
import { test } from 'vitest';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const utilsPath = pathToFileURL(
  path.resolve(__dirname, '../chrome-extension/src/utils.js'),
).href;

const { compareIdsDesc, dedupeNewPosts, buildUploadPayload } = await import(utilsPath);

// ---------------------------------------------------------------------------
// compareIdsDesc
// ---------------------------------------------------------------------------

test('compareIdsDesc returns 0 for equal ids', () => {
  assert.equal(compareIdsDesc({ id: '100' }, { id: '100' }), 0);
});

test('compareIdsDesc puts the larger id first', () => {
  assert.equal(compareIdsDesc({ id: '200' }, { id: '100' }), -1);
  assert.equal(compareIdsDesc({ id: '100' }, { id: '200' }), 1);
});

test('compareIdsDesc handles very large snowflake ids without precision loss', () => {
  const a = { id: '114313983475888128' };
  const b = { id: '114313983475888127' };
  assert.equal(compareIdsDesc(a, b), -1);
});

// ---------------------------------------------------------------------------
// dedupeNewPosts
// ---------------------------------------------------------------------------

test('dedupeNewPosts returns all posts sorted newest-first when lastSeenId is empty', () => {
  const posts = [
    { id: '100' },
    { id: '300' },
    { id: '200' },
  ];
  const result = dedupeNewPosts(posts, '');
  assert.deepEqual(
    result.map((p) => p.id),
    ['300', '200', '100'],
  );
});

test('dedupeNewPosts filters out posts with id <= lastSeenId', () => {
  const posts = [{ id: '100' }, { id: '200' }, { id: '300' }];
  const result = dedupeNewPosts(posts, '200');
  assert.deepEqual(result.map((p) => p.id), ['300']);
});

test('dedupeNewPosts returns empty array when no posts are newer', () => {
  const posts = [{ id: '100' }, { id: '200' }];
  const result = dedupeNewPosts(posts, '300');
  assert.deepEqual(result, []);
});

test('dedupeNewPosts treats a falsy lastSeenId as "no previous posts"', () => {
  const posts = [{ id: '50' }, { id: '60' }];
  assert.equal(dedupeNewPosts(posts, null).length, 2);
  assert.equal(dedupeNewPosts(posts, undefined).length, 2);
  assert.equal(dedupeNewPosts(posts, '').length, 2);
});

test('dedupeNewPosts does not mutate the original array', () => {
  const posts = [{ id: '300' }, { id: '100' }, { id: '200' }];
  const copy = [...posts];
  dedupeNewPosts(posts, '150');
  assert.deepEqual(posts, copy);
});

// ---------------------------------------------------------------------------
// buildUploadPayload
// ---------------------------------------------------------------------------

test('buildUploadPayload includes all required fields', () => {
  const account = { id: '1', username: 'realDonaldTrump' };
  const newPosts = [{ id: '300', content_text: 'hello' }];
  const allPosts = [{ id: '200', content_text: 'world' }, ...newPosts];

  const payload = buildUploadPayload({
    trigger: 'manual',
    handle: 'realDonaldTrump',
    account,
    newPosts,
    allPosts,
  });

  assert.equal(payload.trigger, 'manual');
  assert.equal(payload.handle, 'realDonaldTrump');
  assert.ok(typeof payload.collectedAt === 'string', 'collectedAt should be a string');
  assert.ok(!isNaN(Date.parse(payload.collectedAt)), 'collectedAt should be a valid ISO date');
  assert.deepEqual(payload.account, account);
  assert.deepEqual(payload.newPosts, newPosts);
  assert.deepEqual(payload.allPosts, allPosts);
});

test('buildUploadPayload collectedAt is a recent ISO timestamp', () => {
  const before = Date.now();
  const payload = buildUploadPayload({
    trigger: 'alarm',
    handle: 'testHandle',
    account: {},
    newPosts: [],
    allPosts: [],
  });
  const after = Date.now();
  const ts = Date.parse(payload.collectedAt);
  assert.ok(ts >= before && ts <= after, 'collectedAt should be within the test window');
});
