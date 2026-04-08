import { showBanner, hideBanner, renderState } from './ui.js';

const handleEl = document.getElementById('handle');
const intervalEl = document.getElementById('intervalMinutes');
const webhookEl = document.getElementById('webhookUrl');
const enabledEl = document.getElementById('enabled');
const statusEl = document.getElementById('status');

async function loadState() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
  const config = response.config || {};
  const state = response.state || {};
  handleEl.value = config.handle || 'realDonaldTrump';
  intervalEl.value = config.intervalMinutes || 15;
  webhookEl.value = config.webhookUrl || '';
  enabledEl.checked = Boolean(config.enabled);
  renderState(state);
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
    const msg = response.newCount
      ? `✓ ${response.newCount} new post(s) uploaded`
      : '✓ Collected — no new posts';
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
