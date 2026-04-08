const DEFAULT_CONFIG = {
  handle: 'realDonaldTrump',
  intervalMinutes: 15,
  enabled: false,
  webhookUrl: '',
  maxPages: 3,
  excludeReplies: true,
};

const ALARM_NAME = 'truthsocial-collector';
const STORAGE_KEYS = {
  config: 'config',
  state: 'state',
};

async function getStored(keys) {
  return await chrome.storage.local.get(keys);
}

async function setStored(data) {
  return await chrome.storage.local.set(data);
}

async function getConfig() {
  const stored = await getStored([STORAGE_KEYS.config]);
  return { ...DEFAULT_CONFIG, ...(stored[STORAGE_KEYS.config] || {}) };
}

async function setConfig(patch) {
  const current = await getConfig();
  const next = { ...current, ...patch };
  await setStored({ [STORAGE_KEYS.config]: next });
  await syncAlarm(next);
  return next;
}

async function syncAlarm(config) {
  await chrome.alarms.clear(ALARM_NAME);
  if (config.enabled) {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: Math.max(1, Number(config.intervalMinutes) || 15) });
  }
}

async function setState(patch) {
  const stored = await getStored([STORAGE_KEYS.state]);
  const next = { ...(stored[STORAGE_KEYS.state] || {}), ...patch };
  await setStored({ [STORAGE_KEYS.state]: next });
  return next;
}

async function getTruthTab() {
  const tabs = await chrome.tabs.query({ url: 'https://truthsocial.com/*' });
  return tabs.find((tab) => tab.id && tab.status === 'complete') || tabs[0] || null;
}

async function collectFromTab(tabId, config) {
  const response = await chrome.tabs.sendMessage(tabId, {
    type: 'TRUTH_COLLECT_POSTS',
    config,
  });
  if (!response || !response.ok) {
    throw new Error(response?.error || 'collector failed');
  }
  return response.payload;
}

function compareIdsDesc(a, b) {
  const ai = BigInt(a.id);
  const bi = BigInt(b.id);
  if (ai === bi) return 0;
  return ai > bi ? -1 : 1;
}

function dedupeNewPosts(posts, lastSeenId) {
  const sorted = [...posts].sort(compareIdsDesc);
  if (!lastSeenId) return sorted;
  const last = BigInt(lastSeenId);
  return sorted.filter((post) => BigInt(post.id) > last);
}

async function uploadWebhook(webhookUrl, payload) {
  if (!webhookUrl) return null;
  const resp = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(`webhook upload failed: ${resp.status}`);
  }
  return resp.text();
}

async function runCollector(trigger = 'manual') {
  const config = await getConfig();
  if (!config.enabled) {
    await setState({ lastRunAt: new Date().toISOString(), lastStatus: 'disabled', lastError: '' });
    return { ok: false, skipped: true, reason: 'disabled' };
  }

  const tab = await getTruthTab();
  if (!tab?.id) {
    const status = await setState({
      lastRunAt: new Date().toISOString(),
      lastStatus: 'no_truth_tab',
      lastError: 'No Truth Social tab is open.',
    });
    return { ok: false, skipped: true, state: status };
  }

  try {
    const payload = await collectFromTab(tab.id, config);
    const posts = Array.isArray(payload.posts) ? payload.posts : [];
    const state = await getStored([STORAGE_KEYS.state]);
    const lastSeenId = state[STORAGE_KEYS.state]?.lastSeenId || '';
    const newPosts = dedupeNewPosts(posts, lastSeenId);
    const newestId = posts.length ? String(posts[0].id) : lastSeenId;

    const uploadPayload = {
      trigger,
      collectedAt: new Date().toISOString(),
      handle: config.handle,
      account: payload.account,
      newPosts,
      allPosts: posts,
    };

    if (newPosts.length && config.webhookUrl) {
      await uploadWebhook(config.webhookUrl, uploadPayload);
    }

    await setState({
      lastRunAt: new Date().toISOString(),
      lastStatus: 'ok',
      lastError: '',
      lastSeenId: newestId,
      lastCount: posts.length,
      lastNewCount: newPosts.length,
    });

    return {
      ok: true,
      count: posts.length,
      newCount: newPosts.length,
      newestId,
      account: payload.account,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await setState({
      lastRunAt: new Date().toISOString(),
      lastStatus: 'error',
      lastError: message,
    });
    return { ok: false, error: message };
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  const current = await getConfig();
  await setStored({ [STORAGE_KEYS.config]: current });
  await syncAlarm(current);
});

chrome.runtime.onStartup.addListener(async () => {
  const current = await getConfig();
  await syncAlarm(current);
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  await runCollector('alarm');
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'RUN_COLLECTOR_NOW') {
    runCollector('manual').then(sendResponse).catch((error) => {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    });
    return true;
  }

  if (message?.type === 'GET_STATE') {
    getStored([STORAGE_KEYS.config, STORAGE_KEYS.state]).then((data) => {
      sendResponse({
        ok: true,
        config: { ...DEFAULT_CONFIG, ...(data[STORAGE_KEYS.config] || {}) },
        state: data[STORAGE_KEYS.state] || {},
      });
    });
    return true;
  }

  if (message?.type === 'SAVE_CONFIG') {
    setConfig(message.config || {}).then((config) => {
      sendResponse({ ok: true, config });
    }).catch((error) => {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    });
    return true;
  }
});
