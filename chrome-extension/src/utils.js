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
