import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { test } from 'vitest';
import { buildExtension, toBuiltManifest, buildTargets } from '../scripts/build-extension.mjs';

test('build targets include the extension entry points', () => {
  assert.deepEqual(buildTargets, [
    'src/background.js',
    'src/content.js',
    'src/options.js',
    'src/popup.js',
  ]);
});

test('toBuiltManifest rewrites extension assets into the dist bundle', () => {
  const manifest = {
    manifest_version: 3,
    name: 'Truth Social Collector',
    version: '0.1.0',
    background: { service_worker: 'src/background.js' },
    action: { default_popup: 'src/popup.html' },
    options_page: 'src/options.html',
    content_scripts: [
      {
        matches: ['https://truthsocial.com/*'],
        js: ['src/content.js'],
        run_at: 'document_idle',
      },
    ],
  };

  const built = toBuiltManifest(manifest);

  assert.equal(built.background.service_worker, 'background.js');
  assert.equal(built.action.default_popup, 'popup.html');
  assert.equal(built.options_page, 'options.html');
  assert.deepEqual(built.content_scripts[0].js, ['content.js']);
});

test('buildExtension writes the HTML, CSS, and manifest assets into dist', async () => {
  const outDir = await buildExtension({
    bundleScripts: async () => {},
  });
  assert.ok(existsSync(`${outDir}/manifest.json`));
  assert.ok(existsSync(`${outDir}/popup.html`));
  assert.ok(existsSync(`${outDir}/options.html`));
  assert.ok(existsSync(`${outDir}/styles.css`));
});

