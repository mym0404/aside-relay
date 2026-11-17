import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const temporary = await mkdtemp(path.join(os.tmpdir(), 'aside-test-mutations-'));
const mutations = [
  { name: 'unsafe website link', file: 'web/src/browser.ts', test: 'browser-errors',
    before: 'if (url.protocol === "https:" || url.protocol === "http:")', after: 'if (true)' },
  { name: 'negative response counter', file: 'web/src/responses.ts', test: 'responses',
    before: '!Number.isSafeInteger(result) || result < 0', after: '!Number.isSafeInteger(result)' },
  { name: 'private error log exposure', file: 'web/src/errors.ts', test: 'browser-errors',
    before: 'return GENERIC_ERROR_MESSAGE;', after: 'return message ?? GENERIC_ERROR_MESSAGE;' },
  { name: 'draft action on a preview card', file: 'web/src/drafts.ts', test: 'drafts',
    before: "action: language.endsWith('-draft') ? 'Post' : undefined", after: "action: 'Post'" },
];

function run(test) {
  return spawnSync(process.execPath, ['--test', `tests/unit/${test}.test.mjs`], {
    cwd: temporary, encoding: 'utf8', timeout: 15_000,
  });
}

try {
  await cp(path.join(root, 'web/src'), path.join(temporary, 'web/src'), { recursive: true });
  await cp(path.join(root, 'tests/unit'), path.join(temporary, 'tests/unit'), { recursive: true });
  await cp(path.join(root, 'web/sw.js'), path.join(temporary, 'web/sw.js'));
  await writeFile(path.join(temporary, 'package.json'), '{"type":"module"}');
  // Junctions need no privileges on Windows; symlinks there require
  // Developer Mode or admin. Junction targets must be absolute (ours is).
  await symlink(path.join(root, 'node_modules'), path.join(temporary, 'node_modules'),
                process.platform === 'win32' ? 'junction' : 'dir');
  for (const mutation of mutations) {
    const filename = path.join(temporary, mutation.file);
    const original = await readFile(filename, 'utf8');
    assert.equal(original.split(mutation.before).length, 2, `Mutation target changed: ${mutation.name}`);
    const baseline = run(mutation.test);
    assert.equal(baseline.status, 0, `Baseline failed: ${baseline.stdout}${baseline.stderr}`);
    await writeFile(filename, original.replace(mutation.before, mutation.after));
    const result = run(mutation.test);
    assert.equal(result.error, undefined, `Mutation runner failed: ${mutation.name}`);
    assert.notEqual(result.status, 0, `Tests missed seeded defect: ${mutation.name}`);
    assert.match(result.stdout, /AssertionError/, 'A test assertion, rather than an import error, must detect the defect.');
    console.log(`Detected seeded defect: ${mutation.name}`);
    await writeFile(filename, original);
  }
} finally {
  await rm(temporary, { recursive: true, force: true });
}
