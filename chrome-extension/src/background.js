import { buildUploadPayload, dedupeNewPosts, selectUploadPosts, shouldUploadWebhook } from './utils.js';

const DEFAULT_CONFIG = {
  handle: 'realDonaldTrump',
  intervalMinutes: 15,
  enabled: false,
  webhookUrl: '',
  uploadAllItems: false,
  maxPages: 3,
  excludeReplies: true,
};

const ALARM_NAME = 'truthsocial-collector';
const STORAGE_KEYS = {
  config: 'config',
  state: 'state',
};

const ICON_SIZE = 16;
const ICON_BG_ENABLED = [0, 87, 184, 255];
const ICON_BG_DISABLED = [148, 163, 184, 255];
const ICON_GLYPH = [255, 255, 255, 255];
const ICON_GLYPH_TRANSPARENT = [255, 255, 255, 0];

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
  await syncVisualState(next);
  return next;
}

async function syncAlarm(config) {
  await chrome.alarms.clear(ALARM_NAME);
  if (config.enabled) {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: Math.max(1, Number(config.intervalMinutes) || 15) });
  }
}

function buildIconImageData(enabled) {
  const bg = enabled ? ICON_BG_ENABLED : ICON_BG_DISABLED;
  const data = new Uint8ClampedArray(ICON_SIZE * ICON_SIZE * 4);
  for (let y = 0; y < ICON_SIZE; y += 1) {
    for (let x = 0; x < ICON_SIZE; x += 1) {
      const idx = (y * ICON_SIZE + x) * 4;
      data.set(bg, idx);
    }
  }

  // Simple white vertical mark so the icon isn't just a flat square.
  for (let y = 3; y < 13; y += 1) {
    const left = (y * ICON_SIZE + 6) * 4;
    const right = (y * ICON_SIZE + 9) * 4;
    data.set(ICON_GLYPH, left);
    data.set(ICON_GLYPH_TRANSPARENT, left + 4);
    data.set(ICON_GLYPH_TRANSPARENT, left + 8);
    data.set(ICON_GLYPH, right);
  }

  return { [ICON_SIZE]: { width: ICON_SIZE, height: ICON_SIZE, data } };
}

async function syncActionIcon(config) {
  if (!chrome.action?.setIcon) return;
  await chrome.action.setIcon({ imageData: buildIconImageData(Boolean(config.enabled)) });
}

async function syncVisualState(config) {
  await syncActionIcon(config);
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
    await setState({
      lastRunAt: new Date().toISOString(),
      lastStatus: 'disabled',
      lastError: '',
    });
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
    const uploadedPosts = selectUploadPosts({
      uploadAllItems: Boolean(config.uploadAllItems),
      newPosts,
      allPosts: posts,
    });
    const uploadCount = uploadedPosts.length;

    const uploadPayload = buildUploadPayload({
      trigger,
      handle: config.handle,
      account: payload.account,
      newPosts,
      allPosts: posts,
      uploadedPosts,
      uploadAllItems: Boolean(config.uploadAllItems),
    });

    if (shouldUploadWebhook({
      webhookUrl: config.webhookUrl,
      uploadedPosts,
    })) {
      await uploadWebhook(config.webhookUrl, uploadPayload);
    }

    await setState({
      lastRunAt: new Date().toISOString(),
      lastSuccessAt: new Date().toISOString(),
      lastStatus: 'ok',
      lastError: '',
      lastSeenId: newestId,
      lastCount: posts.length,
      lastNewCount: newPosts.length,
      lastUploadedCount: uploadCount,
    });

    return {
      ok: true,
      count: posts.length,
      newCount: newPosts.length,
      uploadedCount: uploadCount,
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
  await syncVisualState(current);
});

chrome.runtime.onStartup.addListener(async () => {
  const current = await getConfig();
  await syncAlarm(current);
  await syncVisualState(current);
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
