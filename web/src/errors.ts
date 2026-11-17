export const BROWSER_CONNECTION_MESSAGE = 'Connect the Aside browser on your computer, then try again.';
export const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.';
const RUNNING_MESSAGE = 'This conversation is already running.';
const CONNECTION_MESSAGE = 'Check your connection and try again.';

const STATUS_MESSAGES: Record<number, string> = {
  401: 'Check your access token in Settings.',
  403: 'Your access token does not have permission for this action.',
  404: 'That conversation is no longer available.',
  413: 'The image is too large. Choose a smaller image.',
  415: 'Choose a supported image file.',
  429: 'Too many requests. Please wait a moment and try again.',
  503: 'The service is unavailable. Please try again shortly.',
  504: 'The request timed out. Please try again.',
};

const SAFE_ERROR_MESSAGES = [
  BROWSER_CONNECTION_MESSAGE,
  GENERIC_ERROR_MESSAGE,
  'This queued message is already being sent',
  'Queued message not found',
  'The message could not start. Review it and resume the queue.',
  'The message could not be delivered. Review it and resume the queue.',
  'Delivery was interrupted. Review the message and resume the queue.',
  'The response could not start. Please try again.',
  'The response ended with an error. Please try again.',
  RUNNING_MESSAGE,
  CONNECTION_MESSAGE,
  ...Object.values(STATUS_MESSAGES),
];

export function formatRequestError({ message, status }: { message?: string; status?: number }) {
  if (message && SAFE_ERROR_MESSAGES.includes(message)) return message;
  if (message && /(?:Aside Browser profile[\s\S]*not connected to (?:the )?daemon|Chrome extension not connected)/i.test(message)) return BROWSER_CONNECTION_MESSAGE;
  if (message && /(?:conversation is already running|session.*already running)/i.test(message)) return RUNNING_MESSAGE;
  if (status !== undefined && STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];
  if (message && /^(?:Failed to fetch|Load failed|NetworkError.*)$/i.test(message)) return CONNECTION_MESSAGE;
  return GENERIC_ERROR_MESSAGE;
}
