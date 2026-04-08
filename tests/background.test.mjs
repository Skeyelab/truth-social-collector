import assert from 'node:assert/strict';
import { afterEach, beforeEach, test, vi } from 'vitest';

function createChromeMock({ storedConfig = {}, storedState = {} } = {}) {
  const listeners = {
    installed: null,
    startup: null,
    alarm: null,
    message: null,
  };
  const calls = [];
  const storage = {
    config: storedConfig,
    state: storedState,
  };

  globalThis.chrome = {
    storage: {
      local: {
        async get(keys) {
          const out = {};
          for (const key of keys) {
            out[key] = storage[key];
          }
          return out;
        },
        async set(data) {
          if (Object.prototype.hasOwnProperty.call(data, 'config')) {
            storage.config = data.config;
          }
          if (Object.prototype.hasOwnProperty.call(data, 'state')) {
            storage.state = data.state;
          }
          calls.push(['storage.set', data]);
        },
      },
    },
    alarms: {
      async clear(name) {
        calls.push(['alarms.clear', name]);
      },
      create(name, opts) {
        calls.push(['alarms.create', name, opts]);
      },
      onAlarm: {
        addListener(fn) {
          listeners.alarm = fn;
        },
      },
    },
    action: {
      setIcon(payload) {
        calls.push(['action.setIcon', payload]);
      },
    },
    tabs: {
      query: async () => [],
      sendMessage: async () => null,
    },
    runtime: {
      onInstalled: {
        addListener(fn) {
          listeners.installed = fn;
        },
      },
      onStartup: {
        addListener(fn) {
          listeners.startup = fn;
        },
      },
      onMessage: {
        addListener(fn) {
          listeners.message = fn;
        },
      },
    },
  };

  return { listeners, calls, storage };
}

let chromeMock;

async function loadBackground() {
  await import('../chrome-extension/src/background.js');
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  delete globalThis.chrome;
});

test('saving config creates a repeating alarm using the configured interval', async () => {
  chromeMock = createChromeMock();
  await loadBackground();

  const response = await new Promise((resolve) => {
    chromeMock.listeners.message(
      { type: 'SAVE_CONFIG', config: { enabled: true, intervalMinutes: 7, webhookUrl: '' } },
      null,
      resolve,
    );
  });

  assert.equal(response.ok, true);
  assert.deepEqual(
    chromeMock.calls.filter(([name]) => name === 'alarms.create'),
    [['alarms.create', 'truthsocial-collector', { periodInMinutes: 7 }]],
  );
  const iconCall = chromeMock.calls.find(([name]) => name === 'action.setIcon');
  assert.ok(iconCall, 'expected setIcon to be called');
  const payload = iconCall[1];
  assert.equal(payload.imageData[16].width, 16);
  assert.equal(payload.imageData[16].height, 16);
  assert.deepEqual(Array.from(payload.imageData[16].data.slice(0, 4)), [0, 87, 184, 255]);
});

test('startup restores the saved interval alarm when enabled', async () => {
  chromeMock = createChromeMock({
    storedConfig: {
      handle: 'realDonaldTrump',
      intervalMinutes: 12,
      enabled: true,
      webhookUrl: '',
      uploadAllItems: false,
      maxPages: 3,
      excludeReplies: true,
    },
  });
  await loadBackground();

  await chromeMock.listeners.startup();

  assert.deepEqual(
    chromeMock.calls.filter(([name]) => name === 'alarms.create'),
    [['alarms.create', 'truthsocial-collector', { periodInMinutes: 12 }]],
  );
});

test('saving disabled config clears the alarm instead of creating one', async () => {
  chromeMock = createChromeMock();
  await loadBackground();

  const response = await new Promise((resolve) => {
    chromeMock.listeners.message(
      { type: 'SAVE_CONFIG', config: { enabled: false, intervalMinutes: 7, webhookUrl: '' } },
      null,
      resolve,
    );
  });

  assert.equal(response.ok, true);
  assert.deepEqual(
    chromeMock.calls.filter(([name]) => name === 'alarms.create'),
    [],
  );
  assert.deepEqual(
    chromeMock.calls.filter(([name]) => name === 'alarms.clear'),
    [['alarms.clear', 'truthsocial-collector']],
  );
});
