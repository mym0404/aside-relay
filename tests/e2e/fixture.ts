import { test as base, expect, type Page, type Route, type WebSocketRoute } from '@playwright/test';

export const SESSION_A = 'sessionalpha01';
export const SESSION_B = 'sessionbravo02';
export const SIDECHAT = 'sessionside03';
export const NEW_SESSION = 'sessionnewchat06';

type ApiCall = { method: string; path: string; body?: unknown };
type Session = { id: string; title: string; status: string; unread: boolean; isPinned: boolean; pinned?: boolean; archived?: boolean; updatedAt: string; mtime: number; preview: string; lastPrompt: string; bytes: number; hasLog: boolean; projectId?: string | null; statusLabel?: string; suspensionKind?: string };
type Message = { seq: number; role: 'user' | 'assistant' | 'toolResult'; blocks: unknown[]; ts: number; responseId?: string; model?: string; provider?: string };
type Followup = { id: string; prompt: string; attachments: unknown[]; status: 'queued' | 'sending' | 'error'; isEditing?: boolean; error?: string };
type Gate = { promise: Promise<void>; release: () => void };
type HeldRequest = { method: string; path: string | RegExp; gate: Gate; failureStatus?: number };

export const BROWSER_TAB_ID = 'tab-docs-001';
export const BROWSER_TAB_TITLE = 'Streaming documentation';
export const BROWSER_TAB_URL = 'https://example.com/docs/streaming';

const PREVIEW_IMAGE = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240"><rect width="100%" height="100%" fill="#111"/><text x="24" y="48" fill="white">${BROWSER_TAB_TITLE}</text></svg>`;

function gate(): Gate {
  let release: () => void = () => {};
  const promise = new Promise<void>(resolve => { release = resolve; });
  return { promise, release };
}

function json(route: Route, value: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });
}

function session(id: string, title: string, overrides: Partial<Session> = {}): Session {
  const seconds = Date.now() / 1000;
  return { id, title, status: 'idle', unread: false, isPinned: false, pinned: false, updatedAt: new Date(seconds * 1000).toISOString(), mtime: seconds, preview: title, lastPrompt: title, bytes: 128, hasLog: true, statusLabel: 'Completed', ...overrides };
}

function textMessage(seq: number, role: Message['role'], text: string): Message {
  return { seq, role, blocks: [{ type: 'text', text }], ts: Date.now() + seq, ...(role === 'assistant' ? { responseId: `response-${seq}`, model: 'gpt-6.1-sol', provider: 'openai-codex' } : {}) };
}

export class MockAside {
  readonly calls: ApiCall[] = [];
  readonly socketMessages: Record<string, unknown>[] = [];
  readonly sessions: Session[] = [
    session(SESSION_A, 'Alpha conversation', { isPinned: true, pinned: true }),
    session(SESSION_B, 'Bravo conversation', { unread: true, status: 'suspended', statusLabel: 'Awaiting approval', suspensionKind: 'approval', mtime: Date.now() / 1000 - 60 }),
    session('sessioncharlie03', 'Charlie conversation', { mtime: Date.now() / 1000 - 120 }),
    session('sessiondelta004', 'Delta conversation', { mtime: Date.now() / 1000 - 180 }),
    session('sessionecho0005', 'Echo conversation', { mtime: Date.now() / 1000 - 240 }),
  ];
  readonly messages = new Map<string, Message[]>([
    [SESSION_A, [textMessage(0, 'user', 'Hello Aside'), textMessage(1, 'assistant', 'Hello from the assistant.')]],
    [SESSION_B, [textMessage(0, 'user', 'Review this change'), textMessage(1, 'assistant', 'I am waiting for approval.')]],
    [SIDECHAT, [textMessage(0, 'user', 'Side question'), textMessage(1, 'assistant', 'Side answer.')]],
  ]);
  readonly followups = new Map<string, Followup[]>([[SESSION_A, []], [SESSION_B, []]]);
  readonly running = new Set<string>();
  readonly unexpected: string[] = [];
  readonly nativeUnreadOverrides = new Map<string, boolean>();
  readonly nativeArchivedOverrides = new Map<string, boolean>();
  readonly allowedConsoleErrors: RegExp[] = [];
  pauseRuns = false;
  queuePaused = false;
  failNextSend = false;
  workspace: Record<string, unknown> = { status: 'idle', summary: 'Two files changed.', agents: [], todos: [], outputs: [] };
  preferences: Record<string, unknown> = { followUpBehavior: 'queue', sidebarRecentChatLimit: 3, defaultProjectId: null };
  tabs = [{ targetId: BROWSER_TAB_ID, title: BROWSER_TAB_TITLE, url: BROWSER_TAB_URL, active: true, loaded: true, lastAccessed: Date.now() }];
  skills: Array<{ name: string; path: string; description?: string; enabled?: boolean }> = [];
  private socket?: WebSocketRoute;
  private pendingRun?: { payload: Record<string, unknown>; gate: Gate };
  private delayedNativePage?: { cursor: string; gate: Gate };
  private nativeRefreshGate?: Gate;
  private heldRequests: HeldRequest[] = [];

  constructor(private readonly page: Page) {}

  async install() {
    await this.page.routeWebSocket('**/ws', ws => {
      this.socket = ws;
      ws.send(JSON.stringify({ op: 'hello', running: [...this.running] }));
      ws.onMessage(message => this.onSocketMessage(String(message)));
    });
    await this.page.route('**/api/**', route => this.route(route));
  }

  holdNextNativePage(cursor: number) {
    const pending = { cursor: String(cursor), gate: gate() };
    this.delayedNativePage = pending;
    return pending.gate.release;
  }

  holdNativeRefreshes() {
    const pending = gate();
    this.nativeRefreshGate = pending;
    return () => {
      if (this.nativeRefreshGate === pending) this.nativeRefreshGate = undefined;
      pending.release();
    };
  }

  holdNextRequest(method: string, path: string | RegExp, failureStatus?: number) {
    const pending = { method, path, gate: gate(), failureStatus };
    this.heldRequests.push(pending);
    return pending.gate.release;
  }

  allowConsoleError(pattern: RegExp) {
    this.allowedConsoleErrors.push(pattern);
  }

  releaseRun() {
    const pending = this.pendingRun;
    if (!pending) throw new Error('No run is waiting.');
    this.pendingRun = undefined;
    pending.gate.release();
  }

  private onSocketMessage(raw: string) {
    const payload = JSON.parse(raw) as Record<string, unknown>;
    this.socketMessages.push(payload);
    if (payload.op !== 'run' && payload.op !== 'continue') return;
    const pending = { payload, gate: gate() };
    if (this.pauseRuns) {
      this.pendingRun = pending;
      void pending.gate.promise.then(() => this.finishRun(payload));
    } else {
      void this.finishRun(payload);
    }
  }

  private finishRun(payload: Record<string, unknown>) {
    const requestId = String(payload.requestId);
    if (this.failNextSend) {
      this.failNextSend = false;
      this.socket?.send(JSON.stringify({ op: 'error', requestId, message: 'Synthetic delivery failure.' }));
      return;
    }
    const id = typeof payload.sessionId === 'string' ? payload.sessionId : NEW_SESSION;
    const runId = `run-${requestId.slice(0, 12)}`;
    const list = this.messages.get(id) ?? [];
    const user = textMessage(list.length, 'user', String(payload.prompt));
    const assistant = textMessage(list.length + 1, 'assistant', 'Streamed assistant reply.');
    if (!this.sessions.some(item => item.id === id)) this.sessions.unshift(session(id, String(payload.prompt)));
    this.messages.set(id, [...list, user, assistant]);
    this.socket?.send(JSON.stringify({ op: 'run.started', requestId, sessionId: id, runId }));
    this.socket?.send(JSON.stringify({ op: 'msg', sessionId: id, message: user }));
    this.socket?.send(JSON.stringify({ op: 'msg.delta', sessionId: id, runId, streamId: `stream-${runId}`, revision: 1, text: 'Streamed ', done: false, responseId: assistant.responseId }));
    this.socket?.send(JSON.stringify({ op: 'msg.delta', sessionId: id, runId, streamId: `stream-${runId}`, revision: 2, text: 'Streamed assistant reply.', done: true, responseId: assistant.responseId }));
    this.socket?.send(JSON.stringify({ op: 'msg', sessionId: id, message: assistant }));
    this.socket?.send(JSON.stringify({ op: 'run.done', sessionId: id, runId }));
    this.running.delete(id);
  }

  private async route(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const body = request.postDataJSON?.() as unknown;
    this.calls.push({ method, path: url.pathname + url.search, body });
    const heldIndex = this.heldRequests.findIndex(item => item.method === method && (typeof item.path === 'string' ? item.path === url.pathname : item.path.test(url.pathname)));
    if (heldIndex >= 0) {
      const [held] = this.heldRequests.splice(heldIndex, 1);
      await held.gate.promise;
      if (held.failureStatus) return json(route, { error: 'Synthetic delayed mutation failure.' }, held.failureStatus);
    }

    if (url.pathname.startsWith('/api/font/css/')) return route.fulfill({ status: 200, contentType: 'text/css', body: '' });
    if (url.pathname.startsWith('/api/font/file/')) return route.fulfill({ status: 200, contentType: 'font/woff2', body: '' });
    if (method === 'GET' && url.pathname === '/api/web-token') return json(route, { token: 'e2e-token' });
    if (method === 'POST' && url.pathname === '/api/auth') return json(route, { ok: true });
    if (method === 'GET' && url.pathname === '/api/health') return json(route, { asideApp: true });
    if (method === 'GET' && url.pathname === '/api/push/config') return json(route, { publicKey: 'A'.repeat(87) });
    if (url.pathname === '/api/push/presence') return json(route, { ok: true });
    if (method === 'GET' && url.pathname === '/api/sessions') {
      const query = (url.searchParams.get('q') ?? '').toLowerCase();
      const items = this.sessions.filter(item => !query || item.title.toLowerCase().includes(query));
      return json(route, { items, nextCursor: undefined, total: items.length, matched: items.length });
    }
    const sessionMessages = url.pathname.match(/^\/api\/sessions\/([^/]+)\/messages$/);
    if (sessionMessages && method === 'GET') {
      const id = decodeURIComponent(sessionMessages[1]);
      const messages = this.messages.get(id) ?? [];
      return json(route, { sessionId: id, messages, offset: 0, nextSeq: messages.length, running: this.running.has(id) });
    }
    if (sessionMessages && method === 'POST') return this.restSend(route, decodeURIComponent(sessionMessages[1]), body);
    const sessionDetails = url.pathname.match(/^\/api\/sessions\/([^/]+)\/details$/);
    if (sessionDetails && method === 'GET') {
      const item = this.sessions.find(entry => entry.id === decodeURIComponent(sessionDetails[1]));
      return json(route, item ? { id: item.id, title: item.title, status: item.status, isPinned: item.isPinned } : {}, item ? 200 : 404);
    }
    const legacySession = url.pathname.match(/^\/api\/sessions\/([^/]+)$/);
    if (legacySession && method === 'PATCH') {
      const item = this.sessions.find(entry => entry.id === decodeURIComponent(legacySession[1]));
      if (!item) return json(route, { error: 'Missing session.' }, 404);
      Object.assign(item, body);
      return json(route, { id: item.id, title: item.title, status: item.status, isPinned: item.isPinned });
    }
    if (legacySession && method === 'DELETE') {
      const index = this.sessions.findIndex(entry => entry.id === decodeURIComponent(legacySession[1]));
      if (index >= 0) this.sessions.splice(index, 1);
      return json(route, { deleted: true });
    }
    const followups = url.pathname.match(/^\/api\/sessions\/([^/]+)\/followups(?:\/([^/]+))?(?:\/(steer))?$/);
    if (followups) return this.handleFollowups(route, method, decodeURIComponent(followups[1]), followups[2] && decodeURIComponent(followups[2]), followups[3], body);
    if (method === 'POST' && /^\/api\/sessions\/[^/]+\/abort$/.test(url.pathname)) return json(route, { aborted: true });
    if (method === 'GET' && /^\/api\/sessions\/[^/]+\/status$/.test(url.pathname)) return json(route, { running: this.running.has(decodeURIComponent(url.pathname.split('/')[3])) });
    if (method === 'GET' && url.pathname === '/api/models') return json(route, { items: [{ id: 'gpt-6.1-sol', name: 'GPT-6.1 Sol', provider: 'openai-codex', thinkingLevels: ['low', 'high'], supportsFastMode: true }, { id: 'gpt-6-luna', name: 'GPT-6 Luna', provider: 'openai-codex', thinkingLevels: ['low'], supportsFastMode: true }], current: { provider: 'openai-codex', modelId: 'gpt-6.1-sol', thinkingLevel: 'high', fastMode: false } });
    if (method === 'PUT' && /^\/api\/sessions\/[^/]+\/model$/.test(url.pathname)) return json(route, body);
    if (method === 'GET' && url.pathname === '/api/native/workspace/preferences') return json(route, this.preferences);
    if (method === 'PATCH' && url.pathname === '/api/native/workspace/preferences') { Object.assign(this.preferences, body); return json(route, this.preferences); }
    if (method === 'GET' && url.pathname === '/api/native/projects') return json(route, { items: [{ id: 'project-one-01', name: 'Project One', archivedAt: null }] });
    if (method === 'GET' && url.pathname === '/api/native/sessions') return this.nativeSessions(route, url);
    const nativeSession = url.pathname.match(/^\/api\/native\/sessions\/([^/]+)(?:\/(read|unread|archive|unarchive|share|command))?$/);
    if (nativeSession) return this.nativeSession(route, method, decodeURIComponent(nativeSession[1]), nativeSession[2], body, url);
    if (method === 'GET' && url.pathname === '/api/tabs') return json(route, { tabs: this.tabs, currentAccount: { id: 'account-001', email: 'user@example.com' } });
    if (method === 'POST' && url.pathname === '/api/tabs') return json(route, { tab: this.tabs[0] });
    if (/^\/api\/tabs\/[^/]+\/shot$/.test(url.pathname)) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: PREVIEW_IMAGE });
    if (/^\/api\/native\/browser\/tabs\/[^/]+\/stream\.mjpeg$/.test(url.pathname)) return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: PREVIEW_IMAGE });
    if (/^\/api\/tabs\/[^/]+\/focus$/.test(url.pathname)) return json(route, { ok: true });
    if (method === 'DELETE' && /^\/api\/tabs\/[^/]+$/.test(url.pathname)) { this.tabs = []; return json(route, { closed: true }); }
    const artifacts = url.pathname.match(/^\/api\/native\/files\/sessions\/([^/]+)\/artifacts$/);
    if (artifacts && method === 'GET') return json(route, { items: [{ name: 'result.txt', path: 'result.txt', absolutePath: '/tmp/result.txt', bytes: 12, mtime: Date.now(), mime: 'text/plain', kind: 'text' }] });
    if (/\/artifact-preview$/.test(url.pathname)) return json(route, { content: 'E2E file content' });
    if (/\/artifacts\/result.txt$/.test(url.pathname)) return route.fulfill({ status: 200, contentType: 'text/plain', body: 'E2E file content' });
    if (method === 'GET' && url.pathname === '/api/native/files/roots') return json(route, { items: [] });
    if (method === 'GET' && url.pathname === '/api/native/workspace/skills') return json(route, { items: this.skills });

    const signature = `${method} ${url.pathname}${url.search}`;
    this.unexpected.push(signature);
    return json(route, { error: `Unexpected E2E API request: ${signature}` }, 501);
  }

  private restSend(route: Route, id: string, body: unknown) {
    const prompt = typeof body === 'object' && body ? String(Reflect.get(body, 'prompt') ?? '') : '';
    if (this.failNextSend) { this.failNextSend = false; return json(route, { error: 'Synthetic delivery failure.' }, 503); }
    const list = this.messages.get(id) ?? [];
    this.messages.set(id, [...list, textMessage(list.length, 'user', prompt)]);
    return json(route, { sessionId: id, runId: 'run-rest-001', running: true });
  }

  private handleFollowups(route: Route, method: string, id: string, itemId: string | undefined, action: string | undefined, body: unknown) {
    const items = this.followups.get(id) ?? [];
    if (method === 'GET' && !itemId) return json(route, { items, isPaused: this.queuePaused });
    if (method === 'POST' && !itemId) { const item = { id: String(Reflect.get(body as object, 'id')), prompt: String(Reflect.get(body as object, 'prompt')), attachments: [], status: 'queued' as const }; items.push(item); this.followups.set(id, items); return json(route, { items, isPaused: this.queuePaused }); }
    if (method === 'POST' && itemId === 'resume') { this.queuePaused = false; return json(route, { items, isPaused: false }); }
    const index = items.findIndex(item => item.id === itemId);
    if (method === 'PATCH' && index >= 0) { Object.assign(items[index], body); return json(route, { items, isPaused: false }); }
    if (method === 'DELETE' && index >= 0) { items.splice(index, 1); return json(route, { items, isPaused: false }); }
    if (method === 'POST' && action === 'steer' && index >= 0) { items.splice(index, 1); return json(route, { items, isPaused: false }); }
    return json(route, { error: 'Missing follow-up.' }, 404);
  }

  private async nativeSessions(route: Route, url: URL) {
    const refreshing = this.nativeRefreshGate;
    if (refreshing) await refreshing.promise;
    const cursor = url.searchParams.get('cursor') ?? '0';
    const delayed = this.delayedNativePage;
    if (delayed?.cursor === cursor) { this.delayedNativePage = undefined; await delayed.gate.promise; }
    const query = (url.searchParams.get('q') ?? '').toLowerCase();
    const projectId = url.searchParams.get('projectId');
    const statuses = url.searchParams.getAll('status');
    const archived = url.searchParams.get('archived');
    let items = this.sessions.filter(item => !query || item.title.toLowerCase().includes(query));
    if (projectId) items = items.filter(item => item.projectId === projectId);
    if (statuses.length) items = items.filter(item => statuses.includes(item.status));
    if (archived === 'only') items = items.filter(item => this.nativeArchivedOverrides.get(item.id) ?? item.archived);
    else if (archived === 'exclude') items = items.filter(item => !(this.nativeArchivedOverrides.get(item.id) ?? item.archived));
    const cursorNumber = Number(cursor);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const page = items.slice(cursorNumber, cursorNumber + limit);
    const nextCursor = cursorNumber + page.length < items.length ? cursorNumber + page.length : null;
    return json(route, { items: page.map(item => ({ ...item, unread: this.nativeUnreadOverrides.get(item.id) ?? item.unread, pinned: item.isPinned })), nextCursor });
  }

  private nativeSession(route: Route, method: string, id: string, action: string | undefined, body: unknown, url: URL) {
    const item = this.sessions.find(entry => entry.id === id);
    if (method === 'GET' && url.searchParams.get('brief') === 'true') return json(route, { ...this.workspace, sessionId: id });
    if (method === 'PATCH') { if (item) { Object.assign(item, body); if (typeof Reflect.get(body as object, 'pinned') === 'boolean') item.isPinned = Boolean(Reflect.get(body as object, 'pinned')); } return json(route, { result: item }); }
    if (method === 'POST' && action === 'read') { if (item) item.unread = false; return json(route, { result: { unread: false } }); }
    if (method === 'POST' && action === 'unread') { if (item) item.unread = true; return json(route, { result: { unread: true } }); }
    if (method === 'POST' && (action === 'archive' || action === 'unarchive')) { if (item) item.archived = action === 'archive'; return json(route, { result: { archived: action === 'archive' } }); }
    if (method === 'POST' && action === 'share') return json(route, { result: { url: 'https://share.example/snapshot-001' } });
    if (method === 'POST' && action === 'command') {
      const command = typeof body === 'object' && body ? Reflect.get(body, 'command') : undefined;
      if (command === 'sidechat') return json(route, { result: { id: SIDECHAT } });
      if (command === 'branch') return json(route, { result: { session: { id: SIDECHAT } } });
      if (command === 'edit-user-message') return json(route, { result: { ok: true } });
      if (command === 'resolve-suspension' || command === 'cancel-question') { this.workspace = { ...this.workspace, suspension: undefined, status: 'running' }; return json(route, { result: { ok: true } }); }
    }
    return json(route, { error: 'Unsupported native session operation.' }, 400);
  }
}

type Fixtures = { mockAside: MockAside };

export const test = base.extend<Fixtures>({
  mockAside: [async ({ page, browserName }, use) => {
    const mock = new MockAside(page);
    const runtimeErrors: string[] = [];
    page.on('pageerror', error => runtimeErrors.push(`pageerror: ${error.message}`));
    page.on('console', message => {
      if (message.type() !== 'error') return;
      const text = message.text();
      if (browserName === 'webkit' && text === 'Viewport argument key "interactive-widget" not recognized and ignored.') return;
      if (/Failed to load resource: the server responded with a status of 503/.test(text)) return;
      if (mock.allowedConsoleErrors.some(pattern => pattern.test(text))) return;
      runtimeErrors.push(`console: ${text}`);
    });
    await mock.install();
    await use(mock);
    expect(mock.unexpected, `Unexpected API requests:\n${mock.unexpected.join('\n')}`).toEqual([]);
    expect(runtimeErrors, `Unhandled browser errors:\n${runtimeErrors.join('\n')}`).toEqual([]);
  }, { auto: true }],
});

export { expect };
