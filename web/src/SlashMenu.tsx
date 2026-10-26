import { useEffect, useRef } from 'react';
import * as stylex from '@stylexjs/stylex';
import { Sparkles, Terminal } from 'lucide-react';
import { tokens } from './tokens.stylex';
import { ICON_STROKE } from './ui';
import type { SlashItem } from './slashCommands';

export function SlashMenu({ items, activeIndex, onActiveIndexChange, onSelect, onClose }: {
  items: SlashItem[];
  activeIndex: number;
  onActiveIndexChange: (index: number) => void;
  onSelect: (item: SlashItem) => void;
  onClose: () => void;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const active = listRef.current?.querySelector<HTMLElement>('[data-active="true"]');
    active?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, items]);
  useEffect(() => {
    const onPointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !listRef.current?.contains(event.target)) onClose();
    };
    window.addEventListener('pointerdown', onPointer, true);
    return () => window.removeEventListener('pointerdown', onPointer, true);
  }, [onClose]);

  if (!items.length) {
    return <div role="status" {...stylex.props(styles.menu, styles.empty)}>No matching commands.</div>;
  }

  return <div ref={listRef} role="listbox" aria-label="Slash commands" {...stylex.props(styles.menu)}>
    {items.map((item, index) => {
      const isActive = index === activeIndex;
      const key = item.kind === 'command' ? `command:${item.command.id}` : `skill:${item.skill.path}`;
      const title = item.kind === 'command' ? item.command.name : item.skill.name;
      const meta = item.kind === 'command' ? item.command.description : (item.skill.description || item.skill.path);
      const label = item.kind === 'command' ? item.command.text : `$${item.skill.name}`;
      return <button
        key={key}
        type="button"
        role="option"
        aria-selected={isActive}
        data-active={isActive ? 'true' : undefined}
        {...stylex.props(styles.row, isActive && styles.activeRow)}
        onMouseEnter={() => onActiveIndexChange(index)}
        onClick={() => onSelect(item)}
      >
        {item.kind === 'command' ? <Terminal size={18} strokeWidth={ICON_STROKE} /> : <Sparkles size={18} strokeWidth={ICON_STROKE} />}
        <span {...stylex.props(styles.rowText)}>
          <strong {...stylex.props(styles.rowTitle)}>{title}</strong>
          <small {...stylex.props(styles.rowMeta)}>{meta}</small>
        </span>
        <span {...stylex.props(styles.badge)}>{label}</span>
      </button>;
    })}
  </div>;
}

const styles = stylex.create({
  menu: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 'calc(100% + 8px)',
    zIndex: 4,
    maxHeight: 'min(42dvh, 320px)',
    overflowY: 'auto',
    overscrollBehavior: 'contain',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: tokens.border,
    borderRadius: 22,
    backgroundColor: tokens.surface,
    boxShadow: '0 8px 32px rgb(0 0 0 / .22)',
    pointerEvents: 'auto',
  },
  empty: { padding: 16, color: tokens.muted, fontSize: '.875rem', textAlign: 'center' },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    minHeight: 56,
    padding: '8px 12px',
    borderWidth: 0,
    borderBottomWidth: 1,
    borderStyle: 'solid',
    borderColor: tokens.border,
    backgroundColor: 'transparent',
    color: tokens.muted,
    textAlign: 'left',
  },
  activeRow: { backgroundColor: tokens.canvas, color: tokens.text },
  rowText: { display: 'flex', flex: 1, minWidth: 0, flexDirection: 'column', gap: 2, color: tokens.text, overflow: 'hidden' },
  rowTitle: { fontSize: '.875rem', fontWeight: 550, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  rowMeta: { fontSize: '.75rem', color: tokens.muted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  badge: { flexShrink: 0, color: tokens.muted, fontSize: '.75rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
});
