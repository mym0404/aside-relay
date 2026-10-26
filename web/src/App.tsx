import { APP_NAME } from './brand';
import { lazy, Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { VirtuosoHandle } from 'react-virtuoso';
import * as stylex from '@stylexjs/stylex';
import { ArrowDown, Check, CircleAlert, Ellipsis, Menu, SquarePen, X } from 'lucide-react';
import { AnimatePresence, MotionConfig, motion, usePresence, useReducedMotion } from 'motion/react';
import { useChat } from './chat';
import { isRecord } from './responses';
import { usePushNotifications } from './notifications';
import type { ChatSession, Toast, RunOptions } from './types';
import { tokens } from './tokens.stylex';
import { Sidebar } from './Sidebar';
import { Composer } from './Composer';
import { Button } from './Button';
import { Dialog, DialogActions, DialogDescription } from './Dialog';
import { BrowserLive } from './BrowserLive';
import { BrowserPanel } from './BrowserPanel';
import { ImagePreview } from './ImagePreview';
import { Settings } from './Settings';
import { SessionWorkspace, type SessionWorkspaceState } from './SessionWorkspace';
import { RenameConversation, SessionMenu, type SessionMenuTarget } from './SessionMenu';
import { applyTheme, loadThemeMode, resolveTheme, loadAppearance, APPEARANCE_STORAGE_KEY, type Appearance, type ThemeMode, THEME_STORAGE_KEY, applyTextSize, loadTextSize, TEXT_SIZE_STORAGE_KEY, type Theme } from './theme';
import { ICON_STROKE, SESSION_MENU_LABEL, DELETE_CONVERSATION_TITLE, OPEN_DIALOG_SELECTOR, Sheet, DialogBackdropReset, IconButton, focusDialogSurface, resolveDialogReturnFocus, trapDialogFocus, styles as ui } from './ui';

const Messages = lazy(() => import('./Messages').then(module => ({ default: module.Messages })));
const Workspace = lazy(() => import('./Workspace').then(module => ({ default: module.Workspace })));
const Artifacts = lazy(() => import('./Artifacts').then(module => ({ default: module.Artifacts })));
const ZOOM_GESTURE_EVENTS = ['gesturestart', 'gesturechange'];
const TOAST_STACK_LIMIT = 3;
const TOAST_DURATION = 3_000;
const TOAST_ERROR_DURATION = 6_000;
const TOAST_HIDDEN = { opacity: 0, y: -16, scale: .96 };
const latestMessage = { index: 'LAST', align: 'end' } as const;
const SWIPE_AXIS_THRESHOLD = 10;
const DRAWER_SWIPE_DISTANCE = 48;
const HORIZONTAL_GESTURE_RATIO = 1.25;
type Panel = 'settings' | 'browser' | 'workspace' | 'files';
const panelsByPath: Record<string, Panel | undefined> = { '/settings': 'settings', '/tabs': 'browser', '/workspace': 'workspace', '/files': 'files' };

export function App() {
  const chat = useChat();
  const shouldReduceMotion = useReducedMotion();
  const [theme, setTheme] = useState<Theme>(() => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
  const [themeMode, setThemeMode] = useState(loadThemeMode);
  const [appearance, setAppearance] = useState(loadAppearance);
  const [textSize, setTextSize] = useState(loadTextSize);
  const [announcement, setAnnouncement] = useState('');
  const announcedRunRef = useRef({ sessionId: chat.sessionId, isRunning: false });
  const [isDrawer, setDrawer] = useState(false);
  const [menuSession, setMenuSession] = useState<SessionMenuTarget>();
  const [renameTarget, setRenameTarget] = useState<Pick<ChatSession, 'id' | 'title'>>();
  const [panel, setPanel] = useState<Panel | undefined>(() => panelsByPath[location.pathname]);
  const [filesSessionId, setFilesSessionId] = useState<string | undefined>(() => new URLSearchParams(location.search).get('session') ?? undefined);
  const [runOptions, setRunOptions] = useState<RunOptions>();
  const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>();
  const [sidechat, setSidechat] = useState<{ messageId: string; text: string }>();
  const [sidechatPrompt, setSidechatPrompt] = useState('');
  const [isStartingSidechat, setStartingSidechat] = useState(false);
  const [browserTarget, setBrowserTarget] = useState<string>();
  const [deleteTarget, setDeleteTarget] = useState<Pick<ChatSession, 'id' | 'title'>>();
  const [clearConfirm, setClearConfirm] = useState(false);
  const [isClearing, setClearing] = useState(false);
  const [zoom, setZoom] = useState<string>();
  const [draft, setDraft] = useState(''); const [revision, setRevision] = useState(0);
  const [isKeyboardOpen, setKeyboardOpen] = useState(false);
  const [localToasts, setLocalToasts] = useState<Toast[]>([]);
  const localToastIdRef = useRef(0);
  const listRef = useRef<VirtuosoHandle>(null);
  const [canJump, setCanJump] = useState(false);
  const viewportRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const effectiveFilesSessionId = filesSessionId ?? chat.sessionId;
  const sessionTitle = chat.sessions.find(session => session.id === chat.sessionId)?.title || (chat.sessionId ? 'Conversation' : 'New chat');
  const toasts = [...chat.toasts, ...localToasts].sort((first, second) => first.createdAt - second.createdAt);

  function changeAtBottom(isAtBottom: boolean) { setCanJump(!isAtBottom); }

  const notify = useCallback((message: string, kind: 'success' | 'error' = 'success') => {
    const id = `local:${++localToastIdRef.current}`; setLocalToasts(current => [...current, { id, createdAt: Date.now(), message, tone: kind }]);
  }, []);
  const notifications = usePushNotifications(chat, notify);
  const dismissToast = useCallback((id: string) => { chat.dismissToast(id); setLocalToasts(current => current.filter(toast => toast.id !== id)); }, [chat.dismissToast]);
  function changeTextSize(size: number) {
    applyTextSize(size); setTextSize(size);
    try { localStorage.setItem(TEXT_SIZE_STORAGE_KEY, String(size)); }
    catch { notify('Text size changed, but your browser could not save the preference.', 'error'); }
  }
  function changeThemeMode(mode: ThemeMode) {
    const next = resolveTheme(mode);
    applyTheme(next, appearance); setTheme(next); setThemeMode(mode);
    try { localStorage.setItem(THEME_STORAGE_KEY, mode); }
    catch { notify('Theme changed, but your browser could not save the preference.', 'error'); }
  }
  function changeAppearance(next: Appearance) {
    applyTheme(theme, next); setAppearance(next);
    try { localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(next)); }
    catch { notify('Appearance changed, but your browser could not save the preference.', 'error'); }
  }
  useEffect(() => {
    if (themeMode !== 'system') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => { const next = resolveTheme('system'); applyTheme(next, appearance); setTheme(next); };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [themeMode, appearance]);
  function newChat() { chat.newChat(); setRunOptions(undefined); setDraft(''); setRevision(value => value + 1); setDrawer(false); setMenuSession(undefined); changeAtBottom(true); }
  async function clearChatMessages() {
    if (!chat.sessionId || isClearing) return;
    setClearing(true);
    try {
      await chat.request(`/api/native/sessions/${encodeURIComponent(chat.sessionId)}/command`, {
        method: 'POST', body: JSON.stringify({ command: 'clear-messages' }),
      });
      setClearConfirm(false);
      await chat.refreshMessages();
      notify('Chat cleared.', 'success');
    } catch { notify('Could not clear this chat.', 'error'); }
    finally { setClearing(false); }
  }
  function newIncognitoChat() { newChat(); setRunOptions({ mode: 'incognito' }); }
  function openSession(id: string) { void chat.openSession(id); setRunOptions(undefined); setDraft(''); setRevision(value => value + 1); setDrawer(false); setMenuSession(undefined); changeAtBottom(true); }
  function openPanel(next: Panel, targetId?: string) { const sessionId = targetId ?? chat.sessionId; const path = next === 'browser' ? '/tabs' : next === 'files' && sessionId ? '/files?session=' + encodeURIComponent(sessionId) : '/' + next; setBrowserTarget(next === 'browser' ? targetId : undefined); if (next === 'files') setFilesSessionId(sessionId); setPanel(next); setDrawer(false); if (panel) history.replaceState({ panel: next }, '', path); else history.pushState({ panel: next }, '', path); }
  function closePanel() { setPanel(undefined); setBrowserTarget(undefined); history.replaceState({}, '', chat.sessionId ? '/c/' + encodeURIComponent(chat.sessionId) : '/'); }
  function composeContext({ text }: { messageId: string; text: string }) { setDraft(current => `${text.split('\n').map(line => '> ' + line).join('\n')}\n\n${current}`); requestAnimationFrame(() => document.querySelector<HTMLTextAreaElement>('#draft')?.focus({ preventScroll: true })); }
  function askSidechat(context: { messageId: string; text: string }) { setSidechatPrompt(''); setSidechat(context); }
  async function startSidechat() {
    if (!sidechat || !chat.sessionId || !sidechatPrompt.trim() || isStartingSidechat) return;
    setStartingSidechat(true);
    try {
      const response = await chat.request(`/api/native/sessions/${encodeURIComponent(chat.sessionId)}/command`, {
        method: 'POST', body: JSON.stringify({ command: 'sidechat', prompt: sidechatPrompt.trim(), quote: sidechat.text }),
      });
      const value: unknown = await response.json();
      const result = isRecord(value) && isRecord(value.result) ? value.result : undefined;
      const id = result && typeof result.id === 'string' ? result.id : undefined;
      if (!id) throw new Error('Aside did not return a side chat.');
      setSidechat(undefined); setSidechatPrompt(''); openSession(id); void chat.refreshSessions();
    } catch { notify('Could not start the side chat. Your message is still here.', 'error'); }
    finally { setStartingSidechat(false); }
  }

  useEffect(() => { if (chat.recoveredDraft !== undefined) { setDraft(current => current ? current + '\n\n' + chat.recoveredDraft : chat.recoveredDraft || ''); chat.clearRecoveredDraft(); } }, [chat.recoveredDraft, chat.clearRecoveredDraft]);
  useEffect(() => {
    const previous = announcedRunRef.current;
    setAnnouncement(chat.isRunning ? 'Response in progress.' : previous.isRunning && previous.sessionId === chat.sessionId ? 'Response ended.' : '');
    announcedRunRef.current = { sessionId: chat.sessionId, isRunning: chat.isRunning };
  }, [chat.isRunning, chat.sessionId]);
  useEffect(() => {
    const preventZoom = (event: Event) => event.preventDefault();
    ZOOM_GESTURE_EVENTS.forEach(event => document.addEventListener(event, preventZoom, { passive: false }));
    return () => ZOOM_GESTURE_EVENTS.forEach(event => document.removeEventListener(event, preventZoom));
  }, []);
  useEffect(() => {
    let swipe: { id: number; x: number; y: number; horizontal: boolean } | undefined;
    function startSwipe(event: TouchEvent) {
      swipe = undefined;
      const target = event.target;
      if (event.touches.length !== 1 || !(target instanceof Element) || !matchMedia('(max-width: 820px)').matches) return;
      if (target.closest('input, textarea, select, [contenteditable="true"], [data-selectable="true"], [aria-label="Live browser preview"], [popover]') || horizontalScroller(target)) return;
      const dialog = target.closest('dialog, [data-app-dialog]');
      if (dialog ? dialog.getAttribute('aria-label') !== 'Conversation menu' : !target.closest('main[aria-label="Chat"]')) return;
      const touch = event.touches[0];
      swipe = { id: touch.identifier, x: touch.clientX, y: touch.clientY, horizontal: false };
    }
    function moveSwipe(event: TouchEvent) {
      if (!swipe) return;
      if (event.touches.length !== 1) { swipe = undefined; return; }
      const touch = [...event.touches].find(touch => touch.identifier === swipe?.id);
      if (!touch) return;
      const dx = Math.abs(touch.clientX - swipe.x);
      const dy = Math.abs(touch.clientY - swipe.y);
      if (!swipe.horizontal) {
        if (Math.max(dx, dy) < SWIPE_AXIS_THRESHOLD) return;
        if (dx <= dy * HORIZONTAL_GESTURE_RATIO) { swipe = undefined; return; }
        swipe.horizontal = true;
      }
      if (event.cancelable) event.preventDefault();
    }
    function finishSwipe(event: TouchEvent) {
      const current = swipe; swipe = undefined;
      if (!current?.horizontal || event.type === 'touchcancel') return;
      const touch = [...event.changedTouches].find(touch => touch.identifier === current.id);
      if (!touch) return;
      const dx = touch.clientX - current.x;
      if (Math.abs(dx) < DRAWER_SWIPE_DISTANCE || document.querySelector('[popover]:popover-open')) return;
      if (dx > 0 && !isDrawer && !document.querySelector(OPEN_DIALOG_SELECTOR)) setDrawer(true);
      else if (dx < 0 && isDrawer) { setMenuSession(undefined); setDrawer(false); }
    }
    function preventHorizontalNavigation(event: WheelEvent) {
      if (event.ctrlKey || Math.abs(event.deltaX) <= Math.abs(event.deltaY) * HORIZONTAL_GESTURE_RATIO) return;
      const scroller = event.target instanceof Element ? horizontalScroller(event.target) : undefined;
      if (scroller && (event.deltaX < 0 ? scroller.scrollLeft > 0 : scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 1)) return;
      if (event.cancelable) event.preventDefault();
    }
    function horizontalScroller(target: Element) {
      for (let element: Element | null = target; element; element = element.parentElement) {
        if (element.scrollWidth > element.clientWidth + 1 && /^(auto|scroll)$/.test(getComputedStyle(element).overflowX)) return element;
      }
    }
    document.addEventListener('touchstart', startSwipe, { passive: true, capture: true });
    document.addEventListener('touchmove', moveSwipe, { passive: false, capture: true });
    document.addEventListener('touchend', finishSwipe, true);
    document.addEventListener('touchcancel', finishSwipe, true);
    document.addEventListener('wheel', preventHorizontalNavigation, { passive: false, capture: true });
    return () => {
      document.removeEventListener('touchstart', startSwipe, true);
      document.removeEventListener('touchmove', moveSwipe, true);
      document.removeEventListener('touchend', finishSwipe, true);
      document.removeEventListener('touchcancel', finishSwipe, true);
      document.removeEventListener('wheel', preventHorizontalNavigation, true);
    };
  }, [isDrawer]);
  useEffect(() => {
    const onPop = () => { setPanel(panelsByPath[location.pathname]); setFilesSessionId(new URLSearchParams(location.search).get('session') ?? undefined); setDrawer(false); setMenuSession(undefined); setDraft(''); setRevision(value => value + 1); changeAtBottom(true); };
    window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop);
  }, []);
  useEffect(() => {
    if (!chat.isReady || !('serviceWorker' in navigator)) return;
    function openNotification(event: MessageEvent<unknown>) {
      if (typeof event.data !== 'object' || event.data === null || Reflect.get(event.data, 'type') !== 'open-conversation') return;
      const url = Reflect.get(event.data, 'url');
      if (typeof url !== 'string') return;
      let target: URL;
      try { target = new URL(url, location.origin); } catch { return; }
      if (target.origin !== location.origin || !/^\/c\/[A-Za-z0-9]{12,32}$/.test(target.pathname)) return;
      if (location.pathname !== target.pathname) history.pushState({}, '', target.pathname);
      setPanel(undefined); setBrowserTarget(undefined); setDrawer(false); setMenuSession(undefined); setRenameTarget(undefined); setDeleteTarget(undefined); setZoom(undefined);
      openSession(target.pathname.slice(3));
      event.ports[0]?.postMessage(target.pathname);
    }
    navigator.serviceWorker.addEventListener('message', openNotification);
    return () => navigator.serviceWorker.removeEventListener('message', openNotification);
  }, [chat.isReady, chat.openSession]);
  useLayoutEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const updateHeight = () => header.parentElement?.style.setProperty('--header-height', header.getBoundingClientRect().height + 'px');
    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    const hasWorkspace = workspaceState?.sessionId === chat.sessionId && !!workspaceState && (workspaceState.agents.length > 0 || workspaceState.todos.length > 0 || workspaceState.outputs.length > 0 || !!workspaceState.summary);
    const hasSuspension = workspaceState?.sessionId === chat.sessionId && !!workspaceState?.suspension;
    viewportRef.current?.style.setProperty('--workspace-height', `${(hasWorkspace ? 40 : 0) + (hasSuspension ? 44 : 0)}px`);
  }, [workspaceState, chat.sessionId]);
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    let expandedHeight = window.innerHeight;
    let viewportWidth = window.innerWidth;
    let frame = 0;
    let settleTimers: number[] = [];
    const resize = () => {
      const root = viewportRef.current;
      if (!root) return;
      const hasDraftFocus = document.activeElement?.id === 'draft';
      const layoutHeight = Math.max(window.innerHeight, document.documentElement.clientHeight);
      if (window.innerWidth !== viewportWidth) { expandedHeight = layoutHeight; viewportWidth = window.innerWidth; }
      else expandedHeight = Math.max(expandedHeight, layoutHeight);
      const isKeyboardVisible = hasDraftFocus && matchMedia('(pointer: coarse)').matches && expandedHeight - viewport.height > 150;
      setKeyboardOpen(isKeyboardVisible);
      if (isKeyboardVisible) {
        root.style.height = viewport.height + 'px';
        root.style.top = viewport.offsetTop + 'px';
      } else {
        root.style.removeProperty('height');
        root.style.removeProperty('top');
      }
      root.style.setProperty('--keyboard-tools-display', isKeyboardVisible ? 'flex' : 'none');
      if (isKeyboardVisible) root.style.setProperty('--composer-bottom-padding', '6px');
      else root.style.removeProperty('--composer-bottom-padding');
    };
    const scheduleResize = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(resize);
      settleTimers.forEach(window.clearTimeout);
      settleTimers = [100, 350].map(delay => window.setTimeout(resize, delay));
    };
    const onVisibilityChange = () => { if (document.visibilityState === 'visible') scheduleResize(); };
    resize(); viewport.addEventListener('resize', scheduleResize); viewport.addEventListener('scroll', scheduleResize);
    window.addEventListener('resize', scheduleResize); window.addEventListener('orientationchange', scheduleResize);
    window.addEventListener('focus', scheduleResize); window.addEventListener('pageshow', scheduleResize);
    document.addEventListener('focusin', scheduleResize); document.addEventListener('focusout', scheduleResize); document.addEventListener('input', scheduleResize);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      cancelAnimationFrame(frame); settleTimers.forEach(window.clearTimeout);
      viewport.removeEventListener('resize', scheduleResize); viewport.removeEventListener('scroll', scheduleResize);
      window.removeEventListener('resize', scheduleResize); window.removeEventListener('orientationchange', scheduleResize);
      window.removeEventListener('focus', scheduleResize); window.removeEventListener('pageshow', scheduleResize);
      document.removeEventListener('focusin', scheduleResize); document.removeEventListener('focusout', scheduleResize); document.removeEventListener('input', scheduleResize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);
  useEffect(() => {
    let frame = 0;
    const returnToLatest = () => {
      if (document.visibilityState === 'hidden') return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => listRef.current?.scrollToIndex(latestMessage));
    };
    const onWindowFocus = () => { if (matchMedia('(pointer: fine)').matches) returnToLatest(); };
    document.addEventListener('visibilitychange', returnToLatest);
    window.addEventListener('focus', onWindowFocus);
    window.addEventListener('pageshow', returnToLatest);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', returnToLatest); window.removeEventListener('focus', onWindowFocus); window.removeEventListener('pageshow', returnToLatest); };
  }, []);

  return <MotionConfig reducedMotion="user"><div ref={viewportRef} {...stylex.props(styles.app)}><DialogBackdropReset />
    <div {...stylex.props(styles.desktopSidebar)}><Sidebar chat={chat} onNew={newChat} onNewIncognito={newIncognitoChat} onOpen={openSession} onSettings={() => openPanel('settings')} onBrowser={() => openPanel('browser')} onMenu={setMenuSession} /></div>
    <main aria-label="Chat" {...stylex.props(styles.main)}>
      <div className="sr-only" role="status" aria-atomic="true">{announcement}</div>
      <header ref={headerRef} id="header" {...stylex.props(styles.header)}>
        <div {...stylex.props(styles.headerLeft)}><span {...stylex.props(ui.glass, styles.mobileMenu)}><IconButton label="Open conversations" style={{ width: 40, height: 40 }} aria-haspopup="dialog" aria-expanded={isDrawer} onClick={() => setDrawer(true)}><Menu size={24} strokeWidth={ICON_STROKE} aria-hidden="true" /></IconButton></span><div {...stylex.props(styles.heading)}><span title={sessionTitle} {...stylex.props(styles.title)}>{sessionTitle}</span><span {...stylex.props(styles.subtitle)}>{runOptions?.mode === 'incognito' && !chat.sessionId ? 'Incognito' : workspaceState && workspaceState.sessionId === chat.sessionId && workspaceState.suspension ? workspaceState.suspension.title : chat.isRunning ? `${APP_NAME} · Working…` : workspaceState?.sessionId === chat.sessionId && workspaceState?.status === 'errored' ? `${APP_NAME} · Task failed` : APP_NAME}</span></div></div>
        <div {...stylex.props(ui.glass, styles.headerActions)}><IconButton label="New chat" style={{ height: 40 }} onClick={newChat}><SquarePen size={23} strokeWidth={ICON_STROKE} aria-hidden="true" /></IconButton>{chat.sessionId && !chat.authError && <IconButton disabled={!chat.isReady || chat.isOpening} label={SESSION_MENU_LABEL} style={{ height: 40 }} aria-haspopup="menu" aria-expanded={menuSession?.id === chat.sessionId} onClick={event => { const id = chat.sessionId; if (menuSession) setMenuSession(undefined); else if (id) setMenuSession({ id, title: sessionTitle, anchor: event.currentTarget }); }}><Ellipsis aria-hidden="true" size={23} strokeWidth={ICON_STROKE} /></IconButton>}</div>
      </header>
      {chat.authError && <div role="alert" {...stylex.props(styles.notice)}><span>Connect to load your conversations.</span><button {...stylex.props(styles.noticeAction)} onClick={() => openPanel('settings')}>Settings</button></div>}
      {chat.isReady && !chat.isConnected && !chat.authError && <div role="status" {...stylex.props(styles.connectionIndicator)}><span className="sr-only">Reconnecting…</span><motion.span aria-hidden="true" {...stylex.props(styles.connectionSpinner)} animate={shouldReduceMotion ? undefined : { rotate: 360 }} transition={{ duration: .8, repeat: Infinity, ease: 'linear' }} /></div>}
      <div {...stylex.props(styles.scrollRegion)}>
        {chat.isOpening || !chat.isReady ? <ConversationLoading /> : chat.messages.length || chat.pendingPrompt !== undefined || chat.isRunning || chat.liveAssistant?.text ? <Suspense fallback={<ConversationLoading />}><Messages key={chat.sessionId} chat={chat} listRef={listRef} onAtBottomChange={changeAtBottom} notify={notify} onZoom={setZoom} onOpenSession={openSession} onComposeContext={composeContext} onAskSidechat={askSidechat} agentIds={workspaceState?.sessionId === chat.sessionId ? workspaceState?.agents.map(agent => agent.id) : undefined} /></Suspense> : <div {...stylex.props(styles.empty)}><h1 {...stylex.props(styles.emptyTitle)}>What’s on your mind?</h1></div>}
        <AnimatePresence>{canJump && !chat.isOpening && <motion.button key="jump" aria-label="Scroll to latest message" {...stylex.props(styles.jump, ui.glass)} initial={{ opacity: 0, scale: .86, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: .9, y: 6 }} transition={{ duration: .16 }} whileTap={{ scale: .9 }} onClick={() => listRef.current?.scrollToIndex(latestMessage)}><ArrowDown size={19} strokeWidth={ICON_STROKE} /></motion.button>}</AnimatePresence>
        {chat.sessionId && chat.isReady && !chat.isOpening && !chat.authError && <BrowserLive key={chat.sessionId} sessionId={chat.sessionId} request={chat.request} isBrowserOpen={panel === 'browser'} isVisible={!panel && !isDrawer && !menuSession && !deleteTarget && !zoom} onOpen={targetId => openPanel('browser', targetId)} />}
      </div>
      {chat.isReady && !chat.isOpening && !chat.authError && <SessionWorkspace chat={chat} notify={notify} onOpenSession={openSession} onOutputs={() => openPanel('files')} onStateChange={setWorkspaceState} />}
      <Composer runOptions={runOptions} chat={chat} onBrowser={() => openPanel('browser')} draft={draft} setDraft={setDraft} revision={revision} notify={notify} textSize={textSize} uiFont={appearance.uiFont} isKeyboardOpen={isKeyboardOpen} onNewChat={newChat} onConfirmClear={() => setClearConfirm(true)} />
    </main>
    <AnimatePresence>{isDrawer && <Drawer key="drawer" onClose={() => { setMenuSession(undefined); setDrawer(false); }}><Sidebar chat={chat} isDrawer onClose={() => { setMenuSession(undefined); setDrawer(false); }} onNew={newChat} onNewIncognito={newIncognitoChat} onOpen={openSession} onSettings={() => openPanel('settings')} onBrowser={() => openPanel('browser')} onMenu={setMenuSession} /></Drawer>}</AnimatePresence>
    <AnimatePresence mode="wait">{panel === 'settings' ? <Dialog key="settings" title="Settings" onClose={closePanel}><Settings chat={chat} notifications={notifications} notify={notify} isDarkMode={theme === 'dark'} onThemeToggle={() => changeThemeMode(theme === 'light' ? 'dark' : 'light')} themeMode={themeMode} onThemeModeChange={changeThemeMode} appearance={appearance} onAppearanceChange={changeAppearance} textSize={textSize} onTextSizeChange={changeTextSize} onWorkspace={() => openPanel('workspace')} /></Dialog> : panel === 'browser' ? <Sheet key={`browser:${chat.sessionId ?? "new"}:${browserTarget ?? "all"}`} title="Browser" isWide onClose={closePanel}><BrowserPanel initialTargetId={browserTarget} sessionId={chat.sessionId} request={chat.request} notify={notify} onClose={closePanel} onStart={prompt => { closePanel(); if (!chat.sessionId) newChat(); setDraft(prompt); }} /></Sheet> : panel === 'workspace' ? <Suspense key="workspace" fallback={<Dialog title="Workspace & preferences" onClose={closePanel}><DialogDescription>Loading workspace…</DialogDescription></Dialog>}><Workspace chat={chat} notify={notify} onClose={closePanel} onOpenSession={id => { closePanel(); openSession(id); }} onNewProjectChat={projectId => { closePanel(); newChat(); setRunOptions({ projectId }); }} /></Suspense> : panel === 'files' && effectiveFilesSessionId ? <Suspense key={effectiveFilesSessionId} fallback={<Dialog title="Files & outputs" onClose={closePanel}><DialogDescription>Loading files…</DialogDescription></Dialog>}><Artifacts sessionId={effectiveFilesSessionId} request={chat.request} notify={notify} onZoom={setZoom} onClose={closePanel} /></Suspense> : undefined}</AnimatePresence>
    {menuSession && !chat.authError && <SessionMenu key={menuSession.id} target={menuSession} chat={chat} onClose={() => setMenuSession(undefined)} notify={notify} onRename={setRenameTarget} onDelete={setDeleteTarget} onFiles={id => openPanel('files', id)} />}
    <AnimatePresence>{sidechat && <Dialog key="sidechat" title="Ask in side chat" onClose={() => { if (!isStartingSidechat) setSidechat(undefined); }}><blockquote {...stylex.props(styles.sidechatQuote)}>{sidechat.text}</blockquote><label {...stylex.props(styles.sidechatLabel)}>Message<textarea autoFocus rows={3} value={sidechatPrompt} disabled={isStartingSidechat} onChange={event => setSidechatPrompt(event.currentTarget.value)} {...stylex.props(ui.field)} /></label><DialogActions><Button disabled={isStartingSidechat} onClick={() => setSidechat(undefined)}>Cancel</Button><Button variant="primary" disabled={isStartingSidechat || !sidechatPrompt.trim()} onClick={() => { void startSidechat(); }}>{isStartingSidechat ? 'Starting…' : 'Send'}</Button></DialogActions></Dialog>}</AnimatePresence>
    <AnimatePresence>{renameTarget && <RenameConversation key={renameTarget.id} session={renameTarget} chat={chat} onClose={() => setRenameTarget(undefined)} />}</AnimatePresence>
    <AnimatePresence>{clearConfirm && <Dialog key="clear-chat" title="Clear chat?" initialFocus={() => document.querySelector<HTMLElement>('[data-app-dialog] button[data-cancel]')} onClose={() => { if (!isClearing) setClearConfirm(false); }}><DialogDescription>This will permanently delete all messages in this chat.</DialogDescription><DialogActions><Button data-cancel="" disabled={isClearing} onClick={() => setClearConfirm(false)}>Cancel</Button><Button variant="danger" disabled={isClearing} onClick={() => { void clearChatMessages(); }}>{isClearing ? 'Clearing…' : 'Clear'}</Button></DialogActions></Dialog>}</AnimatePresence>
    <AnimatePresence>{deleteTarget && <Dialog key={deleteTarget.id} title={DELETE_CONVERSATION_TITLE} initialFocus={() => document.querySelector<HTMLElement>('[data-app-dialog] button[data-cancel]')} onClose={() => setDeleteTarget(undefined)}><p {...stylex.props(styles.deleteTitle)}>{deleteTarget.title}</p><DialogDescription>This also deletes the original conversation and its files in Aside. This cannot be undone.</DialogDescription><DialogActions><Button data-cancel="" onClick={() => setDeleteTarget(undefined)}>Cancel</Button><Button variant="danger" onClick={() => { setDeleteTarget(undefined); setDrawer(false); void chat.deleteSession(deleteTarget.id); }}>Delete</Button></DialogActions></Dialog>}</AnimatePresence>
    <AnimatePresence>{zoom && <ImagePreview key={zoom} src={zoom} onClose={() => setZoom(undefined)} />}</AnimatePresence>
    <ToastStack toasts={toasts} onDismiss={dismissToast} />
  </div></MotionConfig>;
}

function ConversationLoading() {
  const shouldReduceMotion = useReducedMotion();
  return <div role="region" aria-label="Conversation" aria-busy="true" {...stylex.props(styles.conversationLoading)}>
    <span className="sr-only" role="status">Loading messages…</span>
    <motion.div aria-hidden="true" {...stylex.props(styles.messageSkeleton)} animate={shouldReduceMotion ? undefined : { opacity: [.45, .8, .45] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}>
      {[88, 72, 48].map(width => <div key={width} style={{ width: `${width}%` }} {...stylex.props(styles.skeletonLine)} />)}
    </motion.div>
  </div>;
}

function ToastStack({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const shouldReduceMotion = useReducedMotion();
  const visibleToasts = toasts.slice(-TOAST_STACK_LIMIT);
  const [portalTarget, setPortalTarget] = useState<HTMLElement>(() => document.body);
  useLayoutEffect(() => {
    const updateTarget = () => setPortalTarget([...document.querySelectorAll<HTMLElement>(OPEN_DIALOG_SELECTOR)].at(-1) ?? document.body);
    updateTarget();
    const observer = new MutationObserver(updateTarget);
    observer.observe(document.body, { attributes: true, attributeFilter: ['open', 'data-open'], childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  const dismissNotification = useCallback((id: string) => {
    const activeElement = document.activeElement;
    if (activeElement instanceof HTMLElement && activeElement.closest('[data-toast-id]')?.getAttribute('data-toast-id') === id) {
      const previous = returnFocusRef.current;
      if (previous?.isConnected && !previous.matches(':disabled') && previous.getClientRects().length) previous.focus({ preventScroll: true });
      else { const dialog = activeElement.closest<HTMLElement>('dialog, [data-app-dialog]'); if (dialog instanceof HTMLDialogElement) focusDialogSurface(dialog); else if (dialog) dialog.focus({ preventScroll: true }); else document.querySelector<HTMLButtonElement>('button[aria-label="New chat"]')?.focus({ preventScroll: true }); }
    }
    onDismiss(id);
  }, [onDismiss]);
  useEffect(() => {
    const overflowCount = Math.max(0, toasts.length - TOAST_STACK_LIMIT);
    toasts.slice(0, overflowCount).forEach(toast => dismissNotification(toast.id));
    const timers = toasts.slice(overflowCount).map(toast => {
      const duration = toast.tone === 'error' ? TOAST_ERROR_DURATION : TOAST_DURATION;
      return window.setTimeout(() => dismissNotification(toast.id), Math.max(0, toast.createdAt + duration - Date.now()));
    });
    return () => timers.forEach(window.clearTimeout);
  }, [toasts, dismissNotification]);
  return createPortal(<div data-toast-stack="" onFocusCapture={event => { if (!event.currentTarget.contains(event.relatedTarget) && event.relatedTarget instanceof HTMLElement) returnFocusRef.current = event.relatedTarget; }} {...stylex.props(styles.toasts)}><AnimatePresence initial={false}>{visibleToasts.map((toast, index) => {
    const depth = visibleToasts.length - index - 1;
    return <motion.div key={toast.id} data-toast-id={toast.id} {...stylex.props(styles.toast)} style={{ zIndex: index + 1 }} initial={shouldReduceMotion ? { opacity: 0 } : TOAST_HIDDEN} animate={{ opacity: 1, y: depth * 8, scale: 1 - depth * .04 }} exit={shouldReduceMotion ? { opacity: 0 } : TOAST_HIDDEN} transition={{ type: 'tween', duration: shouldReduceMotion ? .12 : .28, ease: [0.22, 1, 0.36, 1] }}><span aria-hidden="true" {...stylex.props(styles.toastIcon)}>{toast.tone === 'error' ? <CircleAlert size={18} strokeWidth={ICON_STROKE} /> : <Check size={18} strokeWidth={ICON_STROKE} />}</span><span role={toast.tone === 'error' ? 'alert' : 'status'} {...stylex.props(styles.toastMessage)}>{toast.message}</span><motion.button type="button" {...stylex.props(styles.toastClose)} style={{ pointerEvents: depth ? 'none' : 'auto' }} tabIndex={depth ? -1 : 0} whileTap={{ scale: .86 }} aria-label="Dismiss notification" onClick={() => dismissNotification(toast.id)}><X size={16} /></motion.button></motion.div>;
  })}</AnimatePresence></div>, portalTarget);
}

function Drawer({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null); const closeRequestedRef = useRef(false); const shouldReduceMotion = useReducedMotion(); const [isPresent, safeToRemove] = usePresence();
  useLayoutEffect(() => { if (isPresent) closeRequestedRef.current = false; else ref.current?.close(); }, [isPresent]);
  useEffect(() => { if (isPresent || !safeToRemove) return; const timer = window.setTimeout(safeToRemove, shouldReduceMotion ? 120 : 240); return () => window.clearTimeout(timer); }, [isPresent, safeToRemove, shouldReduceMotion]);
  useLayoutEffect(() => {
    const dialog = ref.current; returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (dialog && !dialog.open) { dialog.showModal(); focusDialogSurface(dialog); }
    return () => { if (dialog?.open) dialog.close(); requestAnimationFrame(() => { if (!document.querySelector(OPEN_DIALOG_SELECTOR)) resolveDialogReturnFocus(returnFocusRef.current, 'Conversation menu')?.focus({ preventScroll: true }); }); };
  }, []);
  function requestClose() { if (!isPresent || closeRequestedRef.current) return; closeRequestedRef.current = true; onClose(); }
  return <motion.dialog ref={ref} tabIndex={-1} data-motion-overlay="" style={{ pointerEvents: isPresent ? 'auto' : 'none' }} aria-label="Conversation menu" {...stylex.props(styles.drawer)} onKeyDown={trapDialogFocus} onCancel={event => { event.preventDefault(); requestClose(); }}>
    <motion.button type="button" tabIndex={-1} data-overlay-backdrop="" aria-label="Close conversation menu" {...stylex.props(styles.drawerBackdrop)} initial={{ opacity: 0 }} animate={{ opacity: isPresent ? 1 : 0 }} transition={{ duration: shouldReduceMotion ? .1 : .2 }} onClick={requestClose} />
    <motion.div data-dialog-surface="" {...stylex.props(styles.drawerContent)} initial={shouldReduceMotion ? { opacity: 0 } : { x: -340 }} animate={isPresent ? shouldReduceMotion ? { opacity: 1 } : { x: 0 } : shouldReduceMotion ? { opacity: 0 } : { x: -340 }} transition={shouldReduceMotion ? { duration: .12 } : { duration: .22, ease: [0.22, 1, 0.36, 1] }}>{children}</motion.div>
  </motion.dialog>;
}

const styles = stylex.create({
  sidechatQuote: { margin: '0 0 14px', borderLeftWidth: 2, borderLeftStyle: 'solid', borderLeftColor: tokens.border, padding: '4px 12px', maxHeight: '25svh', overflowY: 'auto', color: tokens.muted, fontSize: '.875rem', lineHeight: 1.5, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' },
  sidechatLabel: { display: 'flex', flexDirection: 'column', gap: 8, fontSize: '.875rem' },
  app: { display: 'flex', width: '100%', height: '100dvh', overflow: 'hidden', position: 'fixed', top: 0, left: 0, color: tokens.text, backgroundColor: tokens.canvas },
  desktopSidebar: { width: 288, flexShrink: 0, height: '100%', borderRightWidth: 1, borderRightStyle: 'solid', borderRightColor: tokens.border, '@media (max-width: 820px)': { display: 'none' } },
  main: { display: 'flex', flexDirection: 'column', position: 'relative', height: '100%', minHeight: 0, minWidth: 0, flex: 1 },
  header: { position: 'absolute', top: 0, left: 0, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, minHeight: 68, padding: 'calc(12px + env(safe-area-inset-top)) max(18px, env(safe-area-inset-right)) 12px max(18px, env(safe-area-inset-left))', backgroundImage: 'linear-gradient(to bottom, var(--canvas), color-mix(in srgb, var(--canvas) 80%, transparent) 60%, transparent)', backdropFilter: 'blur(10px)', zIndex: 3, pointerEvents: 'none' },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 12, minWidth: 0, flex: 1 },
  heading: { display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 },
  headerActions: { display: 'flex', alignItems: 'center', gap: 0, padding: 0, borderRadius: 28, flexShrink: 0, pointerEvents: 'auto' },
  mobileMenu: { display: 'none', borderRadius: '50%', pointerEvents: 'auto', '@media (max-width: 820px)': { display: 'inline-flex' } },
  title: { fontSize: '.9375rem', lineHeight: 1.25, fontWeight: 650, letterSpacing: '-.2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  subtitle: { color: tokens.muted, fontSize: '.75rem', lineHeight: 1.25, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  scrollRegion: { position: 'relative', flex: 1, minHeight: 0, minWidth: 0 },
  empty: { display: 'flex', height: '100%', flex: 1, alignItems: 'center', justifyContent: 'center', paddingBottom: 'calc(var(--composer-height) + 70px)', textAlign: 'center' },
  emptyTitle: { fontSize: '1.6875rem', lineHeight: 1.3, letterSpacing: '-.7px', fontWeight: 600, margin: 0, '@media (max-width: 375px)': { fontSize: '1.5rem' } },
  conversationLoading: { display: 'flex', height: '100%', alignItems: 'flex-end', padding: '20px max(20px, env(safe-area-inset-right)) calc(var(--composer-height) + 28px) max(20px, env(safe-area-inset-left))', minWidth: 0 },
  messageSkeleton: { display: 'flex', flexDirection: 'column', gap: 12, width: '100%', maxWidth: 736, margin: '0 auto' },
  skeletonLine: { height: 12, borderRadius: 6, backgroundColor: tokens.bubble },
  jump: { position: 'absolute', left: '50%', marginLeft: -20, bottom: 'calc(var(--composer-height) + var(--workspace-height, 0px) + 10px)', width: 40, height: 40, borderRadius: '50%', borderWidth: 1, borderStyle: 'solid', borderColor: tokens.border, backgroundColor: tokens.canvas, color: tokens.text, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 6px rgb(0 0 0 / .06)' },
  notice: { display: 'flex', position: 'absolute', top: 'var(--header-height)', right: 16, left: 16, zIndex: 3, alignItems: 'center', justifyContent: 'space-between', gap: 10, margin: 0, padding: '10px 14px', borderRadius: 14, backgroundColor: tokens.surface, fontSize: '0.8125rem', lineHeight: 1.5, flexShrink: 0 },
  noticeAction: { backgroundColor: 'transparent', color: tokens.text, borderWidth: 0, minHeight: 32, fontSize: '0.8125rem', textDecoration: 'underline' },
  connectionIndicator: { position: 'absolute', top: 'calc(var(--header-height) + 4px)', left: '50%', marginLeft: -7, width: 14, height: 14, zIndex: 3, pointerEvents: 'none' },
  connectionSpinner: { display: 'block', width: '100%', height: '100%', borderRadius: '50%', borderWidth: 2, borderStyle: 'solid', borderColor: tokens.muted, borderTopColor: 'transparent' },
  drawer: { display: 'block', position: 'fixed', inset: 0, padding: 0, margin: 0, borderWidth: 0, backgroundColor: 'transparent', width: '100%', height: '100dvh', maxWidth: '100%', maxHeight: '100%', overflow: 'hidden' },
  drawerBackdrop: { position: 'absolute', inset: 0, width: '100%', height: '100%', padding: 0, borderWidth: 0, backgroundColor: 'rgb(0 0 0 / .28)' },
  drawerContent: { position: 'relative', zIndex: 1, width: 'min(320px, 87vw)', height: '100%', boxShadow: '8px 0 32px rgb(0 0 0 / .08)' },
  deleteTitle: { fontSize: '1rem', fontWeight: 550, lineHeight: 1.5, overflowWrap: 'anywhere' },
  toasts: { position: 'fixed', top: 'calc(env(safe-area-inset-top) + 72px)', right: 16, left: 16, bottom: 'auto', margin: 0, width: 'auto', height: 'auto', borderWidth: 0, padding: 0, overflow: 'visible', backgroundColor: 'transparent', display: 'grid', justifyItems: 'center', zIndex: 10, pointerEvents: 'none' },
  toast: { gridArea: '1 / 1', transformOrigin: 'top center', display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px 10px 16px', minHeight: 48, width: '100%', maxWidth: 440, boxSizing: 'border-box', backgroundColor: tokens.text, color: tokens.canvas, borderRadius: 18, boxShadow: '0 4px 20px rgb(0 0 0 / .14)', pointerEvents: 'none' },
  toastMessage: { flex: 1, fontSize: '0.8125rem', lineHeight: 1.45, overflowWrap: 'anywhere', minWidth: 0, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 3, overflow: 'hidden' },
  toastIcon: { display: 'flex', flexShrink: 0 },
  toastClose: { backgroundColor: 'transparent', color: 'inherit', borderWidth: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 36, flexShrink: 0, pointerEvents: 'auto' },
});
