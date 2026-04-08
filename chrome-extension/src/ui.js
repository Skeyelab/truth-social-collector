/**
 * Banner helpers shared by popup.js and options.js.
 *
 * The module expects a `<div id="banner" class="status-banner" hidden>` element
 * to be present in the host document.
 */

const bannerEl = document.getElementById('banner');

export function showBanner(text, type) {
  bannerEl.textContent = text;
  bannerEl.className = `status-banner ${type}`;
  bannerEl.hidden = false;
}

export function hideBanner() {
  bannerEl.hidden = true;
}

export function renderState(state, config = {}) {
  const s = state.lastStatus || '';
  if (s === 'error') {
    showBanner(`⚠ Error: ${state.lastError || 'unknown error'}`, 'error');
  } else if (s === 'ok') {
    const count = config.uploadAllItems ? state.lastUploadedCount : state.lastNewCount;
    const label = config.uploadAllItems ? 'post(s) uploaded' : 'new post(s) uploaded';
    const msg = count
      ? `✓ ${count} ${label}`
      : config.uploadAllItems
        ? '✓ Collected — no posts uploaded'
        : '✓ Collected — no new posts';
    showBanner(msg, 'ok');
  } else if (s === 'no_truth_tab') {
    showBanner('⚠ No Truth Social tab is open.', 'warning');
  } else {
    hideBanner();
  }
}
