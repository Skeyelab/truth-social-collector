import { mkdir, readFile, readdir, rm, cp, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const extensionRoot = path.join(projectRoot, 'chrome-extension');
const outputRoot = path.join(projectRoot, 'dist', 'truth-social-collector');

export const buildTargets = [
  'src/background.js',
  'src/content.js',
  'src/options.js',
  'src/popup.js',
];

function rewriteAssetPath(sourcePath) {
  return path.basename(sourcePath);
}

function rewriteManifestPath(value) {
  if (typeof value !== 'string') return value;
  return value.startsWith('src/') ? path.basename(value) : value;
}

export function toBuiltManifest(manifest) {
  const next = JSON.parse(JSON.stringify(manifest));
  if (next.background?.service_worker) {
    next.background.service_worker = rewriteManifestPath(next.background.service_worker);
  }
  if (next.action?.default_popup) {
    next.action.default_popup = rewriteManifestPath(next.action.default_popup);
  }
  if (next.options_page) {
    next.options_page = rewriteManifestPath(next.options_page);
  }
  if (Array.isArray(next.content_scripts)) {
    next.content_scripts = next.content_scripts.map((script) => ({
      ...script,
      js: Array.isArray(script.js) ? script.js.map(rewriteManifestPath) : script.js,
    }));
  }
  return next;
}

async function loadEsbuild() {
  const mod = await import('esbuild');
  return mod.default || mod;
}

async function bundleScripts() {
  const esbuild = await loadEsbuild();
  await esbuild.build({
    absWorkingDir: extensionRoot,
    entryPoints: buildTargets,
    outdir: outputRoot,
    bundle: true,
    format: 'iife',
    platform: 'browser',
    target: ['chrome120'],
    sourcemap: false,
    minify: false,
    logLevel: 'info',
  });
}

async function copyStaticFiles() {
  const rootEntries = await readdir(extensionRoot, { withFileTypes: true });
  for (const entry of rootEntries) {
    if (entry.isFile() && entry.name === 'manifest.json') {
      const manifest = JSON.parse(await readFile(path.join(extensionRoot, entry.name), 'utf8'));
      await writeFile(path.join(outputRoot, 'manifest.json'), JSON.stringify(toBuiltManifest(manifest), null, 2) + '\n');
      continue;
    }
    if (entry.isFile() && /\.(html|css)$/i.test(entry.name)) {
      await cp(path.join(extensionRoot, entry.name), path.join(outputRoot, entry.name));
    }
  }

  const srcDir = path.join(extensionRoot, 'src');
  const srcEntries = await readdir(srcDir, { withFileTypes: true });
  for (const entry of srcEntries) {
    if (!entry.isFile()) continue;
    if (!/\.(html|css)$/i.test(entry.name)) continue;
    await cp(path.join(srcDir, entry.name), path.join(outputRoot, entry.name));
  }
}

export async function buildExtension({ bundleScripts: bundleScriptsImpl = bundleScripts, copyStaticFiles: copyStaticFilesImpl = copyStaticFiles } = {}) {
  await rm(outputRoot, { recursive: true, force: true });
  await mkdir(outputRoot, { recursive: true });
  await bundleScriptsImpl();
  await copyStaticFilesImpl();
  return outputRoot;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  buildExtension().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
