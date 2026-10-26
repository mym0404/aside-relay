import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import * as stylex from '@stylexjs/stylex';
import { ArrowUp, FileText, Folder, Globe2, Mic, Plus, Sparkles, Square, X, type LucideIcon } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { tokens } from './tokens.stylex';
import { ICON_STROKE, OPEN_DIALOG_SELECTOR, BrowserIcon, IconButton, styles as ui } from './ui';
import type { RunOptions, UploadAttachment, UseChat } from './types';
import { ModelPicker, useModelSelection } from './ModelPicker';
import { ContextPicker, parseSkills, type ContextReference, type ContextSkill } from './ContextPicker';
import { SlashMenu } from './SlashMenu';
import {
  filterSlashItems,
  parseSubmittedSlash,
  skillReference,
  slashQueryAt,
  type SlashCommandId,
  type SlashItem,
} from './slashCommands';

type Attachment = { key: string; preview?: string; name: string; mime: string; upload?: UploadAttachment; hasError?: boolean };
type ContextChip = ContextReference & { key: string };
type SpeechRecognitionResult = { 0?: { transcript?: string } };
type SpeechRecognitionEvent = { resultIndex: number; results: ArrayLike<SpeechRecognitionResult> };
type SpeechRecognitionLike = { continuous: boolean; interimResults: boolean; lang: string; onresult?: (event: SpeechRecognitionEvent) => void; onend?: () => void; onerror?: () => void; start: () => void; stop: () => void };
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const MAX_ATTACHMENTS = 12;
const COMPACT_DRAFT_HEIGHT = 28;
const MAX_DRAFT_HEIGHT = 160;

export function Composer({ chat, onBrowser, draft, setDraft, revision, notify, textSize, uiFont, isKeyboardOpen, runOptions, onNewChat, onConfirmClear }: {
  chat: UseChat; onBrowser: () => void; draft: string; setDraft: (value: string) => void; revision: number; notify: (text: string, kind?: 'error' | 'success') => void; textSize: number; uiFont: string; isKeyboardOpen: boolean; runOptions?: RunOptions; onNewChat: () => void; onConfirmClear: () => void;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  const footerRef = useRef<HTMLElement>(null);
  const modelSelection = useModelSelection(chat, notify);
  const shouldReduceMotion = useReducedMotion();
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | undefined>(undefined);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [contextChips, setContextChips] = useState<ContextChip[]>([]);
  const [hasFocus, setFocus] = useState(false);
  const contextChipsRef = useRef<ContextChip[]>([]);
  const [followUpBehavior, setFollowUpBehavior] = useState<'queue' | 'steer'>('queue');
  useEffect(() => {
    if (!chat.isReady || chat.authError) return;
    const controller = new AbortController();
    async function refreshPreference() {
      try {
        const response = await chat.request('/api/native/workspace/preferences', { signal: controller.signal });
        const value: unknown = await response.json();
        if (typeof value === 'object' && value !== null) setFollowUpBehavior(Reflect.get(value, 'followUpBehavior') === 'steer' ? 'steer' : 'queue');
      } catch { /* Preserve the last known preference while disconnected. */ }
    }
    void refreshPreference();
    window.addEventListener('aside:preferences-changed', refreshPreference);
    return () => { controller.abort(); window.removeEventListener('aside:preferences-changed', refreshPreference); };
  }, [chat.request, chat.isReady, chat.authError]);
  const [isAddingContext, setAddingContext] = useState(false);
  const [isDictating, setDictating] = useState(false);
  const [skills, setSkills] = useState<ContextSkill[]>([]);
  const [cursor, setCursor] = useState(0);
  const [slashIndex, setSlashIndex] = useState(0);
  const [slashDismissed, setSlashDismissed] = useState(false);
  const [speechRecognition] = useState<SpeechRecognitionConstructor | undefined>(() => {
    const browser = window as typeof window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
    return browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  });
  const isExpanded = isKeyboardOpen || hasFocus && matchMedia('(pointer: fine)').matches;
  const attachmentRef = useRef<Attachment[]>([]);
  const draftRef = useRef(draft);
  const slashQuery = useMemo(() => slashQueryAt(draft, cursor), [draft, cursor]);
  const slashItems = useMemo(
    () => slashQuery ? filterSlashItems(slashQuery.query, skills, slashQuery.char === '/') : [],
    [slashQuery, skills],
  );
  const slashOpen = !!slashQuery && !chat.authError && !slashDismissed;
  useEffect(() => { setSlashIndex(0); setSlashDismissed(false); }, [slashQuery?.char, slashQuery?.query, slashQuery?.start]);
  useEffect(() => {
    if (!slashOpen || !chat.isReady || chat.authError) return;
    const controller = new AbortController();
    void chat.request('/api/native/workspace/skills', { signal: controller.signal })
      .then(response => response.json())
      .then(value => { if (!controller.signal.aborted) setSkills(parseSkills(value)); })
      .catch(() => { if (!controller.signal.aborted) setSkills([]); });
    return () => controller.abort();
  }, [slashOpen, chat.request, chat.isReady, chat.authError]);
  // A touch submits before iOS can blur the input. Its later click must not send again or activate the replacement Stop button.
  const isTouchSubmissionRef = useRef(false);
  const pendingPreviewRevokesRef = useRef<string[]>([]);
  const submittedPreviewRevokesRef = useRef(new Map<string, { canRevoke: boolean; hasUnmounted: boolean }>());
  const revisionRef = useRef(revision);
  useEffect(() => { draftRef.current = draft; }, [draft]);
  useEffect(() => { attachmentRef.current = attachments; }, [attachments]);
  useEffect(() => { contextChipsRef.current = contextChips; }, [contextChips]);
  useEffect(() => {
    if (!chat.recoveredAttachments.length) return;
    const restored = chat.recoveredAttachments.map(upload => ({ key: crypto.randomUUID(), preview: upload.mime.startsWith('image/') ? upload.url : undefined, name: upload.name, mime: upload.mime, upload }));
    setAttachments(current => [...current, ...restored].slice(0, MAX_ATTACHMENTS));
  }, [chat.recoveredAttachments]);
  useEffect(() => {
    revisionRef.current = revision;
    pendingPreviewRevokesRef.current.push(...attachmentRef.current.flatMap(attachment => attachment.preview ? [attachment.preview] : []));
    attachmentRef.current = []; setAttachments([]);
    contextChipsRef.current = []; setContextChips([]);
    if (!document.querySelector(OPEN_DIALOG_SELECTOR)) input.current?.focus({ preventScroll: true });
  }, [revision]);
  useEffect(() => () => {
    recognitionRef.current?.stop();
    [...attachmentRef.current.flatMap(attachment => attachment.preview ? [attachment.preview] : []), ...pendingPreviewRevokesRef.current, ...submittedPreviewRevokesRef.current.keys()].forEach(preview => URL.revokeObjectURL(preview));
    submittedPreviewRevokesRef.current.clear();
  }, []);
  function resizeInput() { if (input.current) { input.current.style.height = 'auto'; input.current.style.height = Math.min(input.current.scrollHeight, MAX_DRAFT_HEIGHT) + 'px'; } }
  useLayoutEffect(resizeInput, [draft, textSize, uiFont, isExpanded]);
  useLayoutEffect(() => {
    const footer = footerRef.current;
    if (!footer) return;
    const updateHeight = () => footer.parentElement?.style.setProperty('--composer-height', footer.getBoundingClientRect().height + 'px');
    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(footer);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const area = input.current; if (!area) return;
    let width = area.clientWidth;
    const observer = new ResizeObserver(() => { if (area.clientWidth !== width) { width = area.clientWidth; resizeInput(); } });
    observer.observe(area);
    document.fonts.addEventListener('loadingdone', resizeInput);
    return () => { observer.disconnect(); document.fonts.removeEventListener('loadingdone', resizeInput); };
  }, [isExpanded]);
  const hasUploadPending = attachments.some(attachment => !attachment.upload && !attachment.hasError);
  const hasInput = draft.length > 0 || attachments.length > 0 || contextChips.length > 0;
  const hasDraftContent = draft.trim().length > 0 || attachments.some(attachment => attachment.upload) || contextChips.length > 0;
  const hasSlashSubmit = !!parseSubmittedSlash(draft);
  const canSubmit = chat.isReady && !chat.authError && !chat.isOpening && !modelSelection.isUpdating && !hasUploadPending && (hasSlashSubmit || ((!!chat.sessionId || !!modelSelection.current) && hasDraftContent));
  const shouldQueue = chat.isRunning || chat.queuedMessages.length > 0;
  const submitLabel = shouldQueue ? chat.isRunning && followUpBehavior === 'steer' ? 'Steer message' : 'Queue message' : chat.isSending ? 'Starting response' : 'Send message';
  function flushPreviewRevokes() { pendingPreviewRevokesRef.current.splice(0).forEach(preview => URL.revokeObjectURL(preview)); }
  const markSubmittedPreviewUnmounted = useCallback((preview: string) => {
    const pending = submittedPreviewRevokesRef.current.get(preview);
    if (!pending) return;
    if (pending.canRevoke) {
      URL.revokeObjectURL(preview);
      submittedPreviewRevokesRef.current.delete(preview);
    } else {
      pending.hasUnmounted = true;
    }
  }, []);
  function allowSubmittedPreviewRevokes(sentAttachments: Attachment[]) {
    sentAttachments.forEach(attachment => {
      if (!attachment.preview) return;
      const pending = submittedPreviewRevokesRef.current.get(attachment.preview);
      if (!pending) return;
      if (pending.hasUnmounted) {
        URL.revokeObjectURL(attachment.preview);
        submittedPreviewRevokesRef.current.delete(attachment.preview);
      } else {
        pending.canRevoke = true;
      }
    });
  }

  async function addFiles(files: File[]) {
    const remaining = MAX_ATTACHMENTS - attachmentRef.current.length;
    if (files.length > remaining) notify(`You can attach up to ${MAX_ATTACHMENTS} files.`, 'error');
    const generation = revisionRef.current;
    for (const file of files.slice(0, remaining)) {
      const key = crypto.randomUUID(); const isPreviewableImage = /^image\/(jpeg|png|gif|webp)$/.test(file.type);
      const preview = isPreviewableImage ? URL.createObjectURL(file) : undefined;
      const slot = { key, preview, name: file.webkitRelativePath || file.name, mime: file.type || 'application/octet-stream' };
      attachmentRef.current = [...attachmentRef.current, slot]; setAttachments(attachmentRef.current);
      try {
        const prepared = isPreviewableImage ? await resizeImage(file) : file;
        const uploadFile = slot.name === prepared.name ? prepared : new File([prepared], slot.name, { type: prepared.type, lastModified: prepared.lastModified });
        const upload = await chat.upload(uploadFile);
        if (generation !== revisionRef.current) { if (preview) URL.revokeObjectURL(preview); continue; }
        attachmentRef.current = attachmentRef.current.map(attachment => attachment.key === key ? { ...attachment, upload, mime: upload.mime } : attachment);
        setAttachments(attachmentRef.current);
      } catch {
        if (generation === revisionRef.current) {
          attachmentRef.current = attachmentRef.current.map(attachment => attachment.key === key ? { ...attachment, hasError: true } : attachment);
          setAttachments(attachmentRef.current);
        }
      }
    }
  }

  function addContextChip(reference: ContextReference) {
    setContextChips(current => {
      if (current.some(item => item.value === reference.value)) return current;
      const next = [...current, { ...reference, key: crypto.randomUUID() }];
      contextChipsRef.current = next;
      return next;
    });
    requestAnimationFrame(() => input.current?.focus({ preventScroll: true }));
  }

  function addContext(reference: ContextReference) {
    addContextChip(reference);
  }

  function replaceSlashToken(replacement: string) {
    const area = input.current;
    const active = slashQueryAt(draftRef.current, area?.selectionStart ?? draftRef.current.length);
    if (!active) return;
    const next = `${draftRef.current.slice(0, active.start)}${replacement}${draftRef.current.slice(active.end)}`;
    const nextCursor = active.start + replacement.length;
    draftRef.current = next; setDraft(next); setCursor(nextCursor);
    requestAnimationFrame(() => { area?.focus({ preventScroll: true }); area?.setSelectionRange(nextCursor, nextCursor); });
  }

  async function runSlashCommand(id: SlashCommandId, args?: string) {
    if (id === 'new') { onNewChat(); return; }
    if (id === 'feedback') {
      notify('Send feedback from the Aside desktop app for now.', 'error');
      return;
    }
    if (!chat.sessionId) {
      notify('Open a conversation first.', 'error');
      return;
    }
    if (id === 'clear') { onConfirmClear(); return; }
    try {
      await chat.request(`/api/native/sessions/${encodeURIComponent(chat.sessionId)}/command`, {
        method: 'POST',
        body: JSON.stringify(args ? { command: 'compact', instructions: args } : { command: 'compact' }),
      });
      await chat.refreshMessages();
      notify('Context compacted.', 'success');
    } catch {
      notify('Could not compact this conversation.', 'error');
    }
  }

  function chooseSlashItem(item: SlashItem) {
    if (item.kind === 'skill') {
      replaceSlashToken('');
      addContextChip({ kind: 'skill', label: item.skill.name, value: skillReference(item.skill) });
      return;
    }
    if (item.command.argsPlaceholder) {
      replaceSlashToken(`${item.command.text} `);
      return;
    }
    replaceSlashToken('');
    void runSlashCommand(item.command.id);
  }

  function composePrompt(text: string, chips: ContextChip[]) {
    const refs = chips.map(chip => chip.value).join('\n');
    if (!refs) return text;
    if (!text.trim()) return refs;
    return `${refs}\n\n${text}`;
  }

  function toggleDictation() {
    if (isDictating) { recognitionRef.current?.stop(); return; }
    if (!speechRecognition) return;
    const recognition = new speechRecognition();
    recognition.continuous = true; recognition.interimResults = false; recognition.lang = document.documentElement.lang || navigator.language;
    recognition.onresult = event => {
      const transcript = Array.from(event.results).slice(event.resultIndex).map(result => result[0]?.transcript ?? '').join(' ').trim();
      if (!transcript) return;
      const next = `${draftRef.current}${draftRef.current && !/\s$/.test(draftRef.current) ? ' ' : ''}${transcript}`;
      draftRef.current = next; setDraft(next);
    };
    recognition.onerror = () => { setDictating(false); notify('Dictation is unavailable. Check microphone access.', 'error'); };
    recognition.onend = () => { recognitionRef.current = undefined; setDictating(false); };
    recognitionRef.current = recognition; setDictating(true);
    try { recognition.start(); } catch { recognitionRef.current = undefined; setDictating(false); notify('Dictation could not start.', 'error'); }
  }

  async function submit() {
    const slashSubmit = parseSubmittedSlash(draftRef.current);
    if (slashSubmit && !attachments.some(attachment => attachment.upload) && contextChipsRef.current.length === 0) {
      draftRef.current = ''; setDraft(''); setCursor(0);
      input.current?.blur();
      await runSlashCommand(slashSubmit.command.id, slashSubmit.args);
      return;
    }
    if (!canSubmit) return;
    const sentChips = contextChipsRef.current;
    const sentText = draftRef.current;
    const sentDraft = composePrompt(sentText, sentChips);
    const sentRevision = revisionRef.current;
    const sentAttachments = attachmentRef.current;
    const uploads = sentAttachments.flatMap(attachment => attachment.upload ? [attachment.upload] : []);
    sentAttachments.forEach(attachment => { if (attachment.preview) submittedPreviewRevokesRef.current.set(attachment.preview, { canRevoke: false, hasUnmounted: false }); });
    draftRef.current = ''; setDraft(''); setCursor(0);
    attachmentRef.current = []; setAttachments([]);
    contextChipsRef.current = []; setContextChips([]);
    input.current?.blur();
    const accepted = shouldQueue ? await chat.queue(sentDraft, uploads, chat.isRunning && followUpBehavior === 'steer') : await chat.send(sentDraft, uploads, modelSelection.current, runOptions);
    const shouldRestore = !accepted && sentRevision === revisionRef.current;
    if (shouldRestore) {
      sentAttachments.forEach(attachment => { if (attachment.preview) submittedPreviewRevokesRef.current.delete(attachment.preview); });
      attachmentRef.current = [...sentAttachments, ...attachmentRef.current].slice(0, MAX_ATTACHMENTS); setAttachments(attachmentRef.current);
      contextChipsRef.current = [...sentChips, ...contextChipsRef.current]; setContextChips(contextChipsRef.current);
      if (sentText) {
        const restoredDraft = draftRef.current ? sentText + '\n\n' + draftRef.current : sentText;
        draftRef.current = restoredDraft; setDraft(restoredDraft);
      }
      return;
    }
    allowSubmittedPreviewRevokes(sentAttachments);
    if (sentRevision !== revisionRef.current) return;
    const sentKeys = new Set(sentAttachments.map(attachment => attachment.key));
    attachmentRef.current = attachmentRef.current.filter(attachment => !sentKeys.has(attachment.key));
    setAttachments(attachmentRef.current);
  }

  return <footer ref={footerRef} id="composer" {...stylex.props(styles.footer, isExpanded && styles.expandedFooter)} onFocusCapture={() => setFocus(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setFocus(false); }}>
    <div {...stylex.props(styles.tools)}>
      <motion.button type="button" aria-haspopup="dialog" aria-label="Open browser" {...stylex.props(styles.browser, ui.glass)} whileTap={shouldReduceMotion ? undefined : { scale: .96 }} onPointerDown={event => { if (event.pointerType === 'touch') { event.preventDefault(); onBrowser(); } }} onClick={onBrowser}><BrowserIcon size={17} /><span>Browser</span></motion.button>
      <ModelPicker selection={modelSelection} disabled={!chat.isReady || chat.isOpening || chat.isSending || !!chat.authError} isRunning={chat.isRunning} />
    </div>
    <form {...stylex.props(styles.composer, ui.glass, isExpanded && styles.expandedComposer)} onSubmit={event => { event.preventDefault(); void submit(); }} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); void addFiles([...event.dataTransfer.files]); }}>
      {slashOpen && <SlashMenu items={slashItems} activeIndex={slashIndex} onActiveIndexChange={setSlashIndex} onSelect={chooseSlashItem} onClose={() => setSlashDismissed(true)} />}
      <AnimatePresence initial={false}>
        {contextChips.length > 0 && <motion.div key="context-chips" {...stylex.props(styles.contextChips)} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: .18 }}>
          {contextChips.map(chip => <ContextChipItem key={chip.key} chip={chip} onRemove={() => {
            const next = contextChipsRef.current.filter(item => item.key !== chip.key);
            contextChipsRef.current = next; setContextChips(next);
          }} />)}
        </motion.div>}
      </AnimatePresence>
      <AnimatePresence initial={false} onExitComplete={flushPreviewRevokes}>
        {attachments.length > 0 && <motion.div key="attachments" {...stylex.props(styles.attachments)} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 82 }} exit={{ opacity: 0, height: 0 }} transition={{ duration: .18 }}>
          <AnimatePresence initial={false} onExitComplete={flushPreviewRevokes}>{attachments.map(attachment => <AttachmentItem key={attachment.key} attachment={attachment} onPreviewUnmount={markSubmittedPreviewUnmounted} onRemove={() => { if (attachment.preview) pendingPreviewRevokesRef.current.push(attachment.preview); attachmentRef.current = attachmentRef.current.filter(item => item.key !== attachment.key); setAttachments(attachmentRef.current); }} />)}</AnimatePresence>
        </motion.div>}
      </AnimatePresence>
      <div {...stylex.props(styles.inputActions)}><IconButton label="Add to message" aria-haspopup="dialog" style={{ width: 36, height: 36 }} disabled={!chat.isReady || chat.isOpening || !!chat.authError} onClick={() => setAddingContext(true)}><Plus size={24} strokeWidth={ICON_STROKE} /></IconButton>{speechRecognition && <IconButton label={isDictating ? 'Stop dictation' : 'Dictate'} aria-pressed={isDictating} style={{ width: 36, height: 36 }} disabled={!chat.isReady || chat.isOpening || !!chat.authError} onClick={toggleDictation}><Mic size={21} strokeWidth={ICON_STROKE} /></IconButton>}</div>
      <textarea ref={input} id="draft" aria-label="Message" placeholder={chat.authError ? 'Connect in Settings' : chat.isRunning ? 'Follow up' : 'Message'} rows={1} value={draft} disabled={!chat.isReady || chat.isOpening || !!chat.authError} {...stylex.props(styles.input, isExpanded && styles.expandedInput)} onChange={event => { draftRef.current = event.target.value; setDraft(event.target.value); setCursor(event.target.selectionStart); }} onSelect={event => setCursor(event.currentTarget.selectionStart)} onClick={event => setCursor(event.currentTarget.selectionStart)} onKeyUp={event => setCursor(event.currentTarget.selectionStart)} onPaste={event => { const files = [...event.clipboardData.files]; if (files.length) { event.preventDefault(); void addFiles(files); } }} onKeyDown={event => {
        if (slashOpen && slashItems.length) {
          if (event.key === 'ArrowDown') { event.preventDefault(); setSlashIndex(index => (index + 1) % slashItems.length); return; }
          if (event.key === 'ArrowUp') { event.preventDefault(); setSlashIndex(index => (index - 1 + slashItems.length) % slashItems.length); return; }
          if (event.key === 'Escape') { event.preventDefault(); replaceSlashToken(''); return; }
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); chooseSlashItem(slashItems[Math.min(slashIndex, slashItems.length - 1)]!); return; }
          if (event.key === 'Tab' && !event.shiftKey) { event.preventDefault(); chooseSlashItem(slashItems[Math.min(slashIndex, slashItems.length - 1)]!); return; }
        }
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && matchMedia('(pointer: fine)').matches) { event.preventDefault(); void submit(); }
      }} />
      <div {...stylex.props(styles.submitActions)}>{chat.isRunning && !hasInput
        ? <motion.button key="stop" type="button" aria-label={chat.isStopping ? 'Stopping response' : 'Stop response'} title="Stop response" disabled={chat.isStopping} aria-busy={chat.isStopping} whileTap={shouldReduceMotion ? undefined : { scale: .88 }} {...stylex.props(styles.stop)} onPointerDown={event => { isTouchSubmissionRef.current = false; if (event.pointerType === 'touch') event.preventDefault(); }} onClick={event => { if (event.detail === 0 || !isTouchSubmissionRef.current) void chat.abort(); }}><Square size={13} fill="currentColor" /></motion.button>
        : <motion.button key="send" type="submit" id="send" aria-label={submitLabel} title={submitLabel} disabled={!canSubmit} whileTap={shouldReduceMotion ? undefined : { scale: .88 }} {...stylex.props(styles.send)} onPointerDown={event => { isTouchSubmissionRef.current = event.pointerType === 'touch'; if (isTouchSubmissionRef.current) { event.preventDefault(); void submit(); } }} onClick={event => { if (isTouchSubmissionRef.current && event.detail > 0) event.preventDefault(); }}><ArrowUp size={22} strokeWidth={2.2} /></motion.button>}</div>
      <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/gif,image/webp,image/avif,application/pdf,video/mp4,video/quicktime,video/webm,text/*,.md,.json,.xml,.yaml,.yml,.toml,.js,.jsx,.ts,.tsx,.py,.rb,.go,.rs,.java,.kt,.c,.cc,.cpp,.h,.hpp,.docx,.xlsx,.pptx" multiple hidden onChange={event => { void addFiles([...event.target.files || []]); event.target.value = ''; }} />
      <input ref={element => { folderInput.current = element; element?.setAttribute('webkitdirectory', ''); }} type="file" multiple hidden onChange={event => { void addFiles([...event.target.files || []]); event.target.value = ''; }} />
    </form>
    <AnimatePresence>{isAddingContext && <ContextPicker request={chat.request} sessionId={chat.sessionId} onSelect={addContext} onChooseFiles={() => fileInput.current?.click()} onChooseFolder={() => folderInput.current?.click()} onClose={() => setAddingContext(false)} />}</AnimatePresence>
  </footer>;
}

const CONTEXT_CHIP_ICONS: Record<ContextReference['kind'], LucideIcon> = {
  skill: Sparkles,
  tab: Globe2,
  folder: Folder,
  file: FileText,
};

function ContextChipItem({ chip, onRemove }: { chip: ContextChip; onRemove: () => void }) {
  const Icon = CONTEXT_CHIP_ICONS[chip.kind];
  return <span {...stylex.props(styles.contextChip)}>
    <Icon size={15} strokeWidth={ICON_STROKE} aria-hidden="true" />
    <span {...stylex.props(styles.contextChipLabel)}>{chip.label}</span>
    <button type="button" aria-label={'Remove ' + chip.label} {...stylex.props(styles.contextChipRemove)} onClick={onRemove}><X size={14} strokeWidth={2} /></button>
  </span>;
}

function AttachmentItem({ attachment, onPreviewUnmount, onRemove }: { attachment: Attachment; onPreviewUnmount: (preview: string) => void; onRemove: () => void }) {
  useEffect(() => () => { if (attachment.preview) onPreviewUnmount(attachment.preview); }, [attachment.preview, onPreviewUnmount]);
  return <motion.div layout {...stylex.props(styles.attachment)} initial={{ opacity: 0, scale: .86, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: .84, y: -6 }} transition={{ duration: .18, ease: [0.22, 1, 0.36, 1] }}>
    {attachment.preview ? <img src={attachment.preview} alt={attachment.name} {...stylex.props(styles.thumbnail)} /> : <div {...stylex.props(styles.fileAttachment)}><FileText size={25} aria-hidden="true" /><span {...stylex.props(styles.fileName)}>{attachment.name}</span></div>}
    {!attachment.upload && <span role="status" aria-label={attachment.name + (attachment.hasError ? ' failed to upload' : ' uploading')} {...stylex.props(styles.uploadState)}>{attachment.hasError ? 'Failed' : 'Uploading…'}</span>}
    <motion.button type="button" {...stylex.props(styles.remove)} whileTap={{ scale: .86 }} aria-label={'Remove ' + attachment.name} onClick={onRemove}><X size={14} strokeWidth={2} /></motion.button>
  </motion.div>;
}

async function resizeImage(file: File) {
  const image = new Image(); const url = URL.createObjectURL(file);
  try {
    image.src = url; await image.decode();
    const scale = Math.min(1, 1600 / Math.max(image.width, image.height));
    if (scale === 1 || file.type === 'image/gif') return file;
    const canvas = document.createElement('canvas'); canvas.width = Math.round(image.width * scale); canvas.height = Math.round(image.height * scale);
    const context = canvas.getContext('2d'); if (!context) throw new Error('Image processing unavailable'); context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const mime = file.type === 'image/jpeg' ? 'image/jpeg' : 'image/png';
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(result => result ? resolve(result) : reject(new Error('Image processing failed')), mime, 0.85));
    return new File([blob], file.name.replace(/\.[^.]+$/, '') + (mime === 'image/jpeg' ? '.jpg' : '.png'), { type: blob.type });
  } finally { URL.revokeObjectURL(url); }
}

const styles = stylex.create({
  footer: { position: 'absolute', bottom: 0, left: 0, width: '100%', zIndex: 3, pointerEvents: 'none', padding: '6px max(32px, env(safe-area-inset-right)) var(--composer-bottom-padding, max(18px, env(safe-area-inset-bottom))) max(32px, env(safe-area-inset-left))', '@media (max-width: 375px)': { paddingLeft: 20, paddingRight: 20 } },
  expandedFooter: { paddingLeft: 'max(16px, env(safe-area-inset-left))', paddingRight: 'max(16px, env(safe-area-inset-right))' },
  tools: { display: 'var(--composer-tools-display, none)', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 10, minWidth: 0 },
  composer: { position: 'relative', display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr) auto', alignItems: 'center', width: '100%', maxWidth: 736, margin: '0 auto', borderRadius: 30, padding: '2px 4px', minWidth: 0, pointerEvents: 'auto' },
  expandedComposer: { borderRadius: 28, padding: 8 },
  input: { display: 'block', width: '100%', resize: 'none', borderWidth: 0, backgroundColor: 'transparent', color: tokens.text, fontSize: '1rem', lineHeight: 1.5, minHeight: COMPACT_DRAFT_HEIGHT, maxHeight: MAX_DRAFT_HEIGHT, overflowY: 'auto', overflowWrap: 'anywhere', padding: '2px 4px', '::placeholder': { color: tokens.muted } },
  expandedInput: { order: -1, gridColumn: '1 / -1', minHeight: 44, padding: '8px 10px 12px' },
  browser: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, minHeight: 32, padding: '0 10px', borderRadius: 24, color: tokens.text, fontSize: '.6875rem', fontWeight: 500, pointerEvents: 'auto' },
  inputActions: { display: 'flex', alignItems: 'center', gap: 0 },
  submitActions: { display: 'flex', gridColumn: 3, alignItems: 'center', gap: 4, minWidth: 0 },
  stop: { width: 38, height: 38, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderStyle: 'solid', borderColor: tokens.primary, backgroundColor: tokens.primary, color: tokens.primaryForeground, flexShrink: 0 },
  send: { width: 38, height: 38, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderWidth: 0, backgroundColor: tokens.primary, color: tokens.primaryForeground, flexShrink: 0 },
  contextChips: { order: -3, gridColumn: '1 / -1', display: 'flex', flexWrap: 'wrap', gap: 8, padding: '4px 10px 8px', maxWidth: '100%', minWidth: 0 },
  contextChip: { display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%', minHeight: 32, padding: '4px 6px 4px 10px', borderRadius: 999, backgroundColor: tokens.canvas, color: tokens.text, borderWidth: 1, borderStyle: 'solid', borderColor: tokens.border },
  contextChipLabel: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '.8125rem', fontWeight: 550 },
  contextChipRemove: { display: 'grid', placeItems: 'center', width: 24, height: 24, flexShrink: 0, borderWidth: 0, borderRadius: '50%', color: tokens.muted, backgroundColor: 'transparent' },
  attachments: { order: -2, gridColumn: '1 / -1', display: 'flex', gap: 10, overflowX: 'auto', padding: '0 10px 10px', maxWidth: '100%', minWidth: 0 },
  attachment: { position: 'relative', width: 72, height: 72, flexShrink: 0 },
  thumbnail: { width: '100%', height: '100%', objectFit: 'cover', borderRadius: 14 },
  fileAttachment: { display: 'flex', width: '100%', height: '100%', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, padding: 6, borderRadius: 14, backgroundColor: tokens.surface, color: tokens.muted, borderWidth: 1, borderStyle: 'solid', borderColor: tokens.border },
  fileName: { width: '100%', overflow: 'hidden', color: tokens.text, fontSize: '.625rem', lineHeight: 1.2, textAlign: 'center', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  remove: { position: 'absolute', right: -4, top: -4, width: 28, height: 28, borderRadius: '50%', color: tokens.canvas, backgroundColor: tokens.text, borderWidth: 2, borderStyle: 'solid', borderColor: tokens.surface, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  uploadState: { position: 'absolute', left: 0, bottom: 0, width: '100%', borderRadius: '0 0 14px 14px', padding: 5, backgroundColor: 'rgb(0 0 0 / .6)', color: tokens.mediaWhite, fontSize: '0.625rem', textAlign: 'center' },
});
