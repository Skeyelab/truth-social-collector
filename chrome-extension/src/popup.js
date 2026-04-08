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
  statusEl.textContent = JSON.stringify({ config, state }, null, 2);
}

async function save() {
  const response = await chrome.runtime.sendMessage({
    type: 'SAVE_CONFIG',
    config: {
      handle: handleEl.value.trim() || 'realDonaldTrump',
      intervalMinutes: Number(intervalEl.value) || 15,
      webhookUrl: webhookEl.value.trim(),
      enabled: enabledEl.checked,
    },
  });
  statusEl.textContent = JSON.stringify(response, null, 2);
}

async function runNow() {
  const response = await chrome.runtime.sendMessage({ type: 'RUN_COLLECTOR_NOW' });
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
