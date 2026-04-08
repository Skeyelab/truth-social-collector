const MAX_DEFAULT_PAGES = 3;

function stripHtml(html) {
  const doc = new DOMParser().parseFromString(html || '', 'text/html');
  return (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
}

async function lookupAccount(handle) {
  const resp = await fetch(`/api/v1/accounts/lookup?acct=${encodeURIComponent(handle)}`, {
    credentials: 'include',
    headers: { accept: 'application/json, text/plain, */*' },
  });
  if (!resp.ok) {
    throw new Error(`lookup failed: ${resp.status}`);
  }
  return resp.json();
}

async function fetchStatuses(accountId, excludeReplies = true, maxPages = 3) {
  const all = [];
  let maxId = null;

  for (let pageIndex = 0; pageIndex < Math.max(1, Number(maxPages) || MAX_DEFAULT_PAGES); pageIndex++) {
    const url = new URL(`/api/v1/accounts/${accountId}/statuses`, location.origin);
    if (excludeReplies) url.searchParams.set('exclude_replies', 'true');
    if (maxId) url.searchParams.set('max_id', maxId);

    const resp = await fetch(url, {
      credentials: 'include',
      headers: { accept: 'application/json, text/plain, */*' },
    });
    if (!resp.ok) {
      throw new Error(`statuses fetch failed: ${resp.status}`);
    }

    const page = await resp.json();
    if (!Array.isArray(page) || page.length === 0) break;

    const normalized = page.map((post) => ({
      id: String(post.id),
      created_at: post.created_at,
      url: post.url || post.uri || `https://truthsocial.com/@${post.account?.acct || 'unknown'}/posts/${post.id}`,
      account: {
        id: post.account?.id ? String(post.account.id) : '',
        username: post.account?.username || post.account?.acct || '',
        display_name: post.account?.display_name || '',
        url: post.account?.url || '',
      },
      content_html: post.content || '',
      content_text: stripHtml(post.content || ''),
      raw: post,
    }));

    all.push(...normalized);
    maxId = normalized[normalized.length - 1].id;

    if (page.length < 20) break;
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }

  return all;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== 'TRUTH_COLLECT_POSTS') return;

  (async () => {
    const handle = message.config?.handle || 'realDonaldTrump';
    const account = await lookupAccount(handle);
    const posts = await fetchStatuses(account.id, message.config?.excludeReplies !== false, message.config?.maxPages || MAX_DEFAULT_PAGES);
    sendResponse({ ok: true, payload: { account, posts } });
  })().catch((error) => {
    sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
  });

  return true;
});
