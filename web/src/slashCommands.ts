export type SlashCommandId = 'clear' | 'compact' | 'feedback' | 'new';

export type SlashCommand = {
  id: SlashCommandId;
  name: string;
  text: string;
  description: string;
  keywords: string[];
  argsPlaceholder?: string;
};

export type SlashSkill = { name: string; path: string; description?: string };

export type SlashItem =
  | { kind: 'command'; command: SlashCommand }
  | { kind: 'skill'; skill: SlashSkill };

export type SlashQuery = {
  char: '/' | '$';
  start: number;
  end: number;
  query: string;
};

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: 'clear',
    name: 'Clear',
    text: '/clear',
    description: 'Clear all messages in this chat.',
    keywords: ['clear', '/clear', 'delete messages', 'clear chat'],
  },
  {
    id: 'compact',
    name: 'Compact',
    text: '/compact',
    description: 'Summarize this chat to free up context.',
    keywords: ['compact', '/compact', 'compress', 'summarize context'],
    argsPlaceholder: 'custom instructions...',
  },
  {
    id: 'feedback',
    name: 'Feedback',
    text: '/feedback',
    description: 'Send this task to Aside for debugging.',
    keywords: ['feedback', '/feedback', 'report', 'report task'],
    argsPlaceholder: 'feedback note...',
  },
  {
    id: 'new',
    name: 'New',
    text: '/new',
    description: 'Start a new chat.',
    keywords: ['new', '/new', 'new chat', 'new task'],
  },
];

export function slashQueryAt(text: string, cursor: number): SlashQuery | undefined {
  let start = cursor;
  while (start > 0 && !/\s/.test(text[start - 1]!)) start -= 1;
  const char = text[start];
  if (char !== '/' && char !== '$') return undefined;
  if (start > 0 && !/\s/.test(text[start - 1]!)) return undefined;
  let end = start + 1;
  while (end < text.length && !/\s/.test(text[end]!)) end += 1;
  if (cursor < start || cursor > end) return undefined;
  return { char, start, end, query: text.slice(start + 1, end) };
}

export function parseSubmittedSlash(text: string): { command: SlashCommand; args?: string } | undefined {
  const trimmed = text.trim();
  for (const command of SLASH_COMMANDS) {
    if (trimmed === command.text) return { command };
    if (!command.argsPlaceholder) continue;
    if (!trimmed.startsWith(`${command.text} `)) continue;
    const args = trimmed.slice(command.text.length + 1).trim();
    if (args) return { command, args };
  }
  return undefined;
}

export function filterSlashItems(query: string, skills: SlashSkill[], includeCommands: boolean): SlashItem[] {
  const normalized = query.trim().toLocaleLowerCase();
  const commands = includeCommands
    ? SLASH_COMMANDS.filter(command => matchesSlash(normalized, command.name, command.description, command.keywords))
      .map((command): SlashItem => ({ kind: 'command', command }))
    : [];
  const skillItems = skills
    .filter(skill => matchesSlash(normalized, skill.name, skill.description ?? '', [skill.name, skill.path, skill.description ?? '']))
    .map((skill): SlashItem => ({ kind: 'skill', skill }));
  return [...commands, ...skillItems];
}

function matchesSlash(query: string, name: string, description: string, keywords: string[]) {
  if (!query) return true;
  const haystack = [name, description, ...keywords].join(' ').toLocaleLowerCase();
  return haystack.includes(query) || name.toLocaleLowerCase().startsWith(query);
}

export function skillReference(skill: SlashSkill) {
  return `[@skill "${skill.name}"](${skill.path})`;
}
