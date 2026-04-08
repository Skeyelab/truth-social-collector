/**
 * Compare two post objects by id descending (newest first).
 * Uses BigInt so string IDs with more than 53 significant bits are handled correctly.
 */
export function compareIdsDesc(a, b) {
  const ai = BigInt(a.id);
  const bi = BigInt(b.id);
  if (ai === bi) return 0;
  return ai > bi ? -1 : 1;
}

/**
 * Sort posts newest-first and keep only those whose id is strictly greater
 * than lastSeenId. When lastSeenId is falsy every post is considered new.
 *
 * @param {Array<{id: string}>} posts
 * @param {string} lastSeenId
 * @returns {Array<{id: string}>}
 */
export function dedupeNewPosts(posts, lastSeenId) {
  const sorted = [...posts].sort(compareIdsDesc);
  if (!lastSeenId) return sorted;
  const last = BigInt(lastSeenId);
  return sorted.filter((post) => BigInt(post.id) > last);
}

/**
 * Build the JSON payload that is POSTed to the webhook.
 *
 * @param {object} opts
 * @param {string} opts.trigger  - 'alarm' | 'manual'
 * @param {string} opts.handle   - configured account handle
 * @param {object} opts.account  - raw account object returned by the API
 * @param {Array}  opts.newPosts - deduplicated new posts
 * @param {Array}  opts.allPosts - all posts fetched this run
 * @returns {object}
 */
export function buildUploadPayload({ trigger, handle, account, newPosts, allPosts }) {
  return {
    trigger,
    collectedAt: new Date().toISOString(),
    handle,
    account,
    newPosts,
    allPosts,
  };
}

export function isRetryableStatus(status) {
  return [408, 429, 500, 502, 503, 504].includes(Number(status));
}

export function formatHttpStatusError(status, label = 'request') {
  const code = Number(status);
  if (code === 429) return `${label} was rate limited by Truth Social (HTTP 429)`;
  if (code === 403) return `${label} was blocked by Truth Social/Cloudflare (HTTP 403)`;
  if (code === 404) return `${label} was not found (HTTP 404)`;
  return `${label} failed with HTTP ${code}`;
}

export async function retryAsync(operation, {
  maxAttempts = 3,
  baseDelayMs = 250,
  backoffFactor = 2,
  shouldRetry = () => true,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  let attempt = 0;
  let lastError;

  while (attempt < maxAttempts) {
    try {
      return await operation({ attempt: attempt + 1 });
    } catch (error) {
      lastError = error;
      attempt += 1;
      if (attempt >= maxAttempts || !shouldRetry(error)) {
        throw error;
      }
      const delay = Math.round(baseDelayMs * (backoffFactor ** (attempt - 1)));
      await sleep(delay);
    }
  }

  throw lastError;
}
