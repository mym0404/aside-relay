import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

function findPython() {
  if (process.env.ASIDE_TEST_PYTHON) return process.env.ASIDE_TEST_PYTHON;
  // venv layout is platform-specific: POSIX .venv/bin/python, Windows .venv\Scripts\python.exe
  const candidates = process.platform === 'win32'
    ? ['.venv/Scripts/python.exe', '.venv/Scripts/python', 'python']
    : ['.venv/bin/python', 'python3'];
  for (const c of candidates) {
    if (c === 'python' || c === 'python3' || existsSync(c)) return c;
  }
  return 'python3';
}

const python = findPython();
const result = spawnSync(python, ['-m', 'unittest', 'discover', '-s', 'tests/backend', '-p', 'test_*.py', '-v'], { stdio: 'inherit' });
if (result.error) { console.error(result.error.message); process.exit(1); }
process.exit(result.status ?? 1);
