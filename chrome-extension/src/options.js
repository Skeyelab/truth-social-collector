import { showBanner, hideBanner, renderState } from './ui.js';

const handleEl = document.getElementById('handle');
const intervalEl = document.getElementById('intervalMinutes');
const webhookEl = document.getElementById('webhookUrl');
const uploadAllItemsEl = document.getElementById('uploadAllItems');
const enabledEl = document.getElementById('enabled');
const statusEl = document.getElementById('status');

async function loadState() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
  const config = response.config || {};
  const state = response.state || {};
  handleEl.value = config.handle || 'realDonaldTrump';
  intervalEl.value = config.intervalMinutes || 15;
  webhookEl.value = config.webhookUrl || '';
  uploadAllItemsEl.checked = Boolean(config.uploadAllItems);
  enabledEl.checked = Boolean(config.enabled);
  renderState(state, config);
  statusEl.textContent = JSON.stringify({ config, state }, null, 2);
}

async function save() {
  hideBanner();
  const response = await chrome.runtime.sendMessage({
    type: 'SAVE_CONFIG',
    config: {
      handle: handleEl.value.trim() || 'realDonaldTrump',
      intervalMinutes: Number(intervalEl.value) || 15,
      webhookUrl: webhookEl.value.trim(),
      uploadAllItems: uploadAllItemsEl.checked,
      enabled: enabledEl.checked,
    },
  });
  if (!response.ok) {
    showBanner(`⚠ Save failed: ${response.error || 'unknown error'}`, 'error');
  } else {
    showBanner('✓ Settings saved', 'ok');
  }
  statusEl.textContent = JSON.stringify(response, null, 2);
}

async function runNow() {
  hideBanner();
  const response = await chrome.runtime.sendMessage({ type: 'RUN_COLLECTOR_NOW' });
  if (!response.ok) {
    showBanner(`⚠ ${response.error || 'collector failed'}`, 'error');
  } else {
    const msg = uploadAllItemsEl.checked
      ? (response.uploadedCount
        ? `✓ ${response.uploadedCount} post(s) uploaded`
        : '✓ Collected — no posts uploaded')
      : (response.newCount
        ? `✓ ${response.newCount} new post(s) uploaded`
        : '✓ Collected — no new posts');
    showBanner(msg, 'ok');
  }
  statusEl.textContent = JSON.stringify(response, null, 2);
}

document.getElementById('save').addEventListener('click', () => save().catch((err) => {
  statusEl.textContent = String(err);
}));
document.getElementById('runNow').addEventListener('click', () => runNow().catch((err) => {
  statusEl.textContent = String(err);
}));

loadState().catch((err) => {
  statusEl.textContent = String(err);
});
