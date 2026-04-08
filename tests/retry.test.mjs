import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const utilsPath = pathToFileURL(
  path.resolve(__dirname, '../chrome-extension/src/utils.js'),
).href;

const {
  isRetryableStatus,
  retryAsync,
  formatHttpStatusError,
} = await import(utilsPath);

test('isRetryableStatus returns true for rate limit and transient server errors', () => {
  assert.equal(isRetryableStatus(429), true);
  assert.equal(isRetryableStatus(500), true);
  assert.equal(isRetryableStatus(502), true);
  assert.equal(isRetryableStatus(503), true);
  assert.equal(isRetryableStatus(504), true);
});

test('isRetryableStatus returns false for client errors that should not be retried', () => {
  assert.equal(isRetryableStatus(400), false);
  assert.equal(isRetryableStatus(403), false);
  assert.equal(isRetryableStatus(404), false);
});

test('formatHttpStatusError surfaces rate limit and block messages', () => {
  assert.match(formatHttpStatusError(429), /rate limited/i);
  assert.match(formatHttpStatusError(403), /blocked/i);
  assert.match(formatHttpStatusError(500), /http 500/i);
});

test('retryAsync retries until the operation succeeds', async () => {
  const events = [];
  let attempts = 0;
  const result = await retryAsync(async () => {
    attempts += 1;
    events.push(`attempt-${attempts}`);
    if (attempts < 3) {
      throw new Error('boom');
    }
    return 'ok';
  }, {
    maxAttempts: 3,
    baseDelayMs: 1,
    sleep: async (ms) => events.push(`sleep-${ms}`),
  });

  assert.equal(result, 'ok');
  assert.deepEqual(events, ['attempt-1', 'sleep-1', 'attempt-2', 'sleep-2', 'attempt-3']);
});

test('retryAsync stops retrying when the error is not retryable', async () => {
  let attempts = 0;
  await assert.rejects(
    () => retryAsync(async () => {
      attempts += 1;
      const err = new Error('forbidden');
      err.status = 403;
      throw err;
    }, {
      maxAttempts: 5,
      baseDelayMs: 1,
      shouldRetry: (error) => isRetryableStatus(error.status),
      sleep: async () => {},
    }),
    /forbidden/,
  );

  assert.equal(attempts, 1);
});
