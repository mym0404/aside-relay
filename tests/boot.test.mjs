// Production UI smoke test. Run `npm run build` before this file.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { JSDOM } from 'jsdom';

const root = path.resolve(import.meta.dirname, '..');
const dist = path.join(root, 'web/dist');
const UI_TIMEOUT_MS = 5_000;
const PRODUCT_NAME = 'aside-relay';
const indexPath = path.join(dist, 'index.html');
if (!fs.existsSync(indexPath)) throw new Error('web/dist is missing. Run npm run build first.');

const html = fs.readFileSync(indexPath, 'utf8');
const entrySource = html.match(/<script[^>]+type="module"[^>]+src="([^"]+)"/i)?.[1];
if (!entrySource) throw new Error('The production HTML has no module entry.');
const entryPath = path.join(dist, entrySource.replace(/^\//, ''));
if (!fs.existsSync(entryPath)) throw new Error(`The production entry is missing: ${entryPath}`);

const now = Date.now() / 1_000;
const sessions = [
  createSession('ALPHASESSION001', 'Alpha conversation', now),
  createSession('BETASESSION0001', 'Beta conversation', now - 60),
];
const messages = new Map([
  ['ALPHASESSION001', [createMessage(0, 'user', [{ type: 'text', text: 'Alpha prompt' }])]],
  ['BETASESSION0001', [
    createMessage(0, 'user', [{ type: 'text', text: 'Inspect this' }]),
    createMessage(1, 'assistant', [
      { type: 'thinking', text: 'Plan\nCheck the page' },
      { type: 'toolCall', name: 'repl', args: { code: '1 + 1' } },
    ]),
    { ...createMessage(2, 'toolResult', [{ type: 'text', text: '2' }]), toolName: 'repl' },
  ]],
]);
const running = new Set();
const runRequests = new Map();
const socketRequests = [];
const runtimeErrors = [];
let failures = 0;

const dom = new JSDOM(html, { url: 'http://localhost/settings', pretendToBeVisual: true });
const { window } = dom;
window.localStorage.setItem('lastSession', 'BETASESSION0001');
installBrowserGlobals(window);
installFetch(window);
const socket = installWebSocket(window);

process.on('unhandledRejection', captureError);
process.on('uncaughtExceptionMonitor', captureError);
window.addEventListener('error', event => captureError(event.error || event.message));
window.addEventListener('unhandledrejection', event => captureError(event.reason));

console.log('production React boot');
await Promise.race([
  import(pathToFileURL(entryPath).href),
  new Promise((_, reject) => setTimeout(() => reject(new Error('Timed out importing the production bundle.')), UI_TIMEOUT_MS)),
]);
await waitFor(() => document.querySelector('[aria-current="page"]')?.textContent.includes('Beta'));
await waitFor(() => document.querySelector('[aria-label="Your message"]'));
check('no boot errors', runtimeErrors.length === 0);
check('product title is aside-relay', document.title === PRODUCT_NAME);
check('Home Screen title is aside-relay', document.querySelector('meta[name="apple-mobile-web-app-title"]')?.content === PRODUCT_NAME);
check('drawer brand is aside-relay', document.querySelector('aside[aria-label="Conversations"]')?.textContent.includes(PRODUCT_NAME));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'web/manifest.webmanifest'), 'utf8'));
check('installation manifest uses aside-relay', manifest.name === PRODUCT_NAME && manifest.short_name === PRODUCT_NAME);
check('conversation list rendered', document.querySelectorAll('aside[aria-label="Conversations"]').length === 1);
check('settings refresh restores the last conversation in the background', location.pathname === '/settings' && document.querySelector('[aria-current="page"]')?.textContent.includes('Beta'));
check('restored messages rendered', document.querySelector('[aria-label="Your message"]')?.textContent.includes('Inspect this'));
click(document.querySelector('[role="dialog"][data-app-dialog] button[aria-label="Close"]'));
await waitFor(() => location.pathname === '/c/BETASESSION0001');

console.log('activity state and mobile drawer');
const activity = document.querySelector('details');
check('activity is rendered collapsed', activity && !activity.open);
activity.open = true;
await waitFor(() => activity.querySelector('details'));
const innerStep = activity.querySelector('details');
innerStep.open = true;
socket.emit({ op: 'hello', running: [] });
await tick();
check('activity stays open across a state render', activity.open && innerStep.open);

click(document.querySelector('button[aria-label="Open conversations"]'));
await waitFor(() => document.querySelector('dialog[aria-label="Conversation menu"]'));
const drawer = document.querySelector('dialog[aria-label="Conversation menu"]');
check('mobile menu opens a modal drawer', drawer.open === true);
typeIn(drawer.querySelector('input[aria-label="Search conversations"]'), 'Alpha');
await waitFor(() => drawer.textContent.includes('Alpha conversation') && !drawer.textContent.includes('Beta conversation'));
check('search filters from the API', drawer.textContent.includes('Alpha conversation'));
click([...drawer.querySelectorAll('button')].find(button => button.textContent.includes('Alpha conversation')));
await waitFor(() => location.pathname === '/c/ALPHASESSION001');
check('opening a result routes to its conversation', location.pathname === '/c/ALPHASESSION001');
await waitFor(() => !document.querySelector('dialog[aria-label="Conversation menu"]'));
check('drawer closes after selection', !document.querySelector('dialog[aria-label="Conversation menu"]'));

console.log('dead link and stale run correlation');
history.pushState({}, '', '/c/MISSINGSESSION1');
window.dispatchEvent(new window.PopStateEvent('popstate'));
await waitFor(() => location.pathname === '/');
check('dead conversation is replaced with the new-chat route', location.pathname === '/');

const draft = document.querySelector('textarea[aria-label="Message"]');
typeIn(draft, 'Do not resurrect this run');
click(document.querySelector('button[aria-label="Send message"]'));
await waitFor(() => lastSocketRequest('run'));
const staleRun = lastSocketRequest('run');
check('draft clears as soon as the run is sent', draft.value === '');
click(document.querySelector('button[aria-label="New chat"]'));
socket.emit({ op: 'run.started', requestId: staleRun.requestId, sessionId: 'STALESESSION01', runId: 'stale-run' });
await tick(30);
check('late run.started cannot reselect a canceled chat', location.pathname === '/' && !localStorage.getItem('lastSession'));

console.log('disconnect delivery recovery and first-message recovery');
typeIn(draft, 'Accepted after disconnect');
click(document.querySelector('button[aria-label="Send message"]'));
await waitFor(() => socketRequests.filter(request => request.op === 'run').length === 2);
const recoveredRun = lastSocketRequest('run');
messages.set('NEWSESSION0001', [createMessage(0, 'user', [{ type: 'text', text: 'Accepted after disconnect' }])]);
running.add('NEWSESSION0001');
runRequests.set(recoveredRun.requestId, { status: 'started', sessionId: 'NEWSESSION0001', runId: 'recovered-run' });
socket.disconnect();
await waitFor(() => location.pathname === '/c/NEWSESSION0001');
await waitFor(() => document.querySelector('[aria-label="Your message"]')?.textContent.includes('Accepted after disconnect'));
check('request registry recovers a lost run.started event', location.pathname === '/c/NEWSESSION0001');
check('canonical fetch recovers the first message', document.querySelector('[aria-label="Your message"]')?.textContent.includes('Accepted after disconnect'));
check('draft stays clear after recovered acceptance', draft.value === '');

click(document.querySelector('button[aria-label="New chat"]'));
socket.emit({ op: 'run.done', sessionId: 'NEWSESSION0001', runId: 'recovered-run' });
await tick(30);
check('old run completion does not reopen its conversation', location.pathname === '/');
check('explicit new chat choice is persisted', localStorage.getItem('lastSessionMode') === 'new');
check('no runtime errors after core flows', runtimeErrors.length === 0);

console.log(failures ? `\n${failures} FAILED` : '\nall passed');
dom.window.close();
process.exit(failures ? 1 : 0);

function createSession(id, title, mtime) {
  return { id, title, status: 'idle', unread: false, isPinned: false, updatedAt: new Date(mtime * 1_000).toISOString(), mtime, preview: `${title} preview`, lastPrompt: title, bytes: 100, hasLog: true };
}

function createMessage(seq, role, blocks) {
  return { seq, role, blocks, ts: 1_791_590_400_000 };
}

function check(name, condition) {
  console.log(`  ${condition ? '✓' : '✗'} ${name}`);
  if (!condition) failures += 1;
}

function captureError(error) {
  runtimeErrors.push(String(error?.stack || error?.message || error));
}

function tick(milliseconds = 0) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function waitFor(condition, timeout = UI_TIMEOUT_MS) {
  const deadline = Date.now() + timeout;
  while (!condition()) {
    if (Date.now() >= deadline) throw new Error(`UI condition timed out at ${location.pathname}: ${condition.toString()}`);
    await tick(10);
  }
}

function click(element) {
  if (!element) throw new Error('Could not find the element to click.');
  element.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));
}

function typeIn(element, value) {
  if (!element) throw new Error('Could not find the input.');
  const prototype = element instanceof window.HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value);
  element.dispatchEvent(new window.Event('input', { bubbles: true }));
}

function lastSocketRequest(operation) {
  return socketRequests.findLast(request => request.op === operation);
}

function installFetch(targetWindow) {
  globalThis.fetch = targetWindow.fetch = async (input, init = {}) => {
    const url = new URL(String(input), location.href);
    const method = init.method || 'GET';
    // The bundle resolves lazy chunks against import.meta.url. Under the test's
    // file:// entry on Windows that pathname is /C:/assets/x.js — strip the
    // drive-letter prefix so it matches the same way it does on macOS.
    const pathname = url.pathname.replace(/^\/[A-Za-z]:/, '');
    if (method === 'GET' && pathname.startsWith('/assets/')) {
      const assetPath = path.join(dist, 'assets', path.basename(pathname));
      if (fs.existsSync(assetPath)) return new Response(fs.readFileSync(assetPath));
    }
    if (url.pathname === '/api/web-token') return response({ token: 'test-token', via: 'loopback' });
    if (url.pathname === '/api/models') return response({
      items: [{ id: 'test-model', name: 'Test model', provider: 'test', thinkingLevels: ['high'], supportsFastMode: false }],
      current: { provider: 'test', modelId: 'test-model', thinkingLevel: 'high', fastMode: false },
    });
    if ((url.pathname === '/api/sessions' || url.pathname === '/api/native/sessions') && method === 'GET') {
      const query = (url.searchParams.get('q') || '').toLowerCase();
      const items = sessions.filter(item => !query || item.title.toLowerCase().includes(query) || item.preview.toLowerCase().includes(query));
      return response({ items, nextCursor: null, total: sessions.length, matched: items.length });
    }
    const messageMatch = url.pathname.match(/^\/api\/sessions\/([^/]+)\/messages$/);
    if (messageMatch && method === 'GET') {
      const sessionId = decodeURIComponent(messageMatch[1]);
      const items = messages.get(sessionId) || [];
      return response({ sessionId, messages: items, nextSeq: items.length ? items.at(-1).seq + 1 : 0, offset: items.length * 100, running: running.has(sessionId) });
    }
    const statusMatch = url.pathname.match(/^\/api\/sessions\/([^/]+)\/status$/);
    if (statusMatch) return response({ sessionId: statusMatch[1], running: running.has(statusMatch[1]) });
    const requestMatch = url.pathname.match(/^\/api\/run-requests\/([^/]+)$/);
    if (requestMatch) return response(runRequests.get(decodeURIComponent(requestMatch[1])) || { detail: 'unknown request' }, runRequests.has(decodeURIComponent(requestMatch[1])) ? 200 : 404);
    if (url.pathname.endsWith('/abort')) return response({ aborted: true });
    throw new Error(`Unexpected fetch: ${method} ${url.pathname}${url.search}`);
  };
}

function response(body, status = 200) {
  const text = JSON.stringify(body);
  return { ok: status >= 200 && status < 300, status, headers: new Headers({ 'Content-Type': 'application/json' }), json: async () => JSON.parse(text), text: async () => text, blob: async () => new Blob([text], { type: 'application/json' }) };
}

function installWebSocket(targetWindow) {
  class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSED = 3;
    static instance;

    readyState = MockWebSocket.CONNECTING;
    onopen;
    onmessage;
    onerror;
    onclose;

    constructor() {
      MockWebSocket.instance = this;
      queueMicrotask(() => {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.({});
        this.emit({ op: 'hello', running: [] });
      });
    }

    send(raw) { socketRequests.push(JSON.parse(raw)); }
    emit(payload) { this.onmessage?.({ data: JSON.stringify(payload) }); }
    close() { this.readyState = MockWebSocket.CLOSED; }
    disconnect() { this.readyState = MockWebSocket.CLOSED; this.onclose?.({}); }
  }

  globalThis.WebSocket = targetWindow.WebSocket = MockWebSocket;
  return {
    emit(payload) { MockWebSocket.instance?.emit(payload); },
    disconnect() { MockWebSocket.instance?.disconnect(); },
  };
}

function installBrowserGlobals(targetWindow) {
  const itemHeight = 96;
  const names = ['document', 'navigator', 'location', 'history', 'localStorage', 'Node', 'Element', 'HTMLElement', 'HTMLInputElement', 'HTMLTextAreaElement', 'HTMLDialogElement', 'SVGElement', 'Event', 'ErrorEvent', 'CustomEvent', 'MouseEvent', 'PopStateEvent', 'MutationObserver', 'Image', 'File', 'Blob', 'Headers', 'getComputedStyle'];
  Object.defineProperty(globalThis, 'window', { configurable: true, writable: true, value: targetWindow });
  names.forEach(name => {
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value: targetWindow[name] });
  });
  globalThis.requestAnimationFrame = targetWindow.requestAnimationFrame.bind(targetWindow);
  globalThis.cancelAnimationFrame = targetWindow.cancelAnimationFrame.bind(targetWindow);
  globalThis.matchMedia = targetWindow.matchMedia = query => ({ matches: query.includes('pointer: fine'), media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; } });
  targetWindow.visualViewport = { height: 844, offsetTop: 0, addEventListener() {}, removeEventListener() {} };
  targetWindow.document.fonts = Object.assign(new targetWindow.EventTarget(), { load: async () => [], ready: Promise.resolve() });
  targetWindow.HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
    const height = this.hasAttribute('data-item-index') ? itemHeight : 744;
    return { x: 0, y: 0, top: 0, left: 0, bottom: height, right: 374, width: 374, height, toJSON() {} };
  };
  ['offsetHeight', 'clientHeight'].forEach(name => Object.defineProperty(targetWindow.HTMLElement.prototype, name, { configurable: true, get() { return this.getBoundingClientRect().height; } }));
  Object.defineProperty(targetWindow.HTMLElement.prototype, 'offsetParent', { configurable: true, get() { return this.parentElement; } });
  Object.defineProperty(targetWindow.HTMLElement.prototype, 'scrollHeight', { configurable: true, get() {
    const list = this.querySelector('[data-testid="virtuoso-item-list"]');
    return Math.max(this.clientHeight, list ? (parseFloat(list.style.paddingTop) || 0) + (parseFloat(list.style.paddingBottom) || 0) + list.children.length * itemHeight : this.clientHeight);
  } });
  globalThis.ResizeObserver = targetWindow.ResizeObserver = class {
    targets = new Set();
    constructor(callback) { this.callback = callback; }
    observe(target) {
      this.targets.add(target);
      queueMicrotask(() => {
        if (!this.targets.has(target)) return;
        const contentRect = target.getBoundingClientRect();
        this.callback([{ target, contentRect, borderBoxSize: [{ blockSize: contentRect.height, inlineSize: contentRect.width }] }]);
      });
    }
    unobserve(target) { this.targets.delete(target); }
    disconnect() { this.targets.clear(); }
  };
  globalThis.IntersectionObserver = targetWindow.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} };
  targetWindow.HTMLDialogElement.prototype.showModal = function showModal() { this.setAttribute('open', ''); };
  targetWindow.HTMLDialogElement.prototype.close = function close() { this.removeAttribute('open'); };
  targetWindow.HTMLElement.prototype.scrollTo = function scrollTo(options) { if (typeof options === 'object' && typeof options.top === 'number') { this.scrollTop = options.top; this.dispatchEvent(new targetWindow.Event('scroll')); } };
  targetWindow.HTMLElement.prototype.focus = function focus() {};
}
