export interface Logger {
  info(message: string, meta?: Record<string, unknown>): void;
  warn(message: string, meta?: Record<string, unknown>): void;
  error(message: string, meta?: Record<string, unknown>): void;
  debug(message: string, meta?: Record<string, unknown>): void;
}

function logWithLevel(level: 'info' | 'warn' | 'error' | 'debug', scope: string, message: string, meta?: Record<string, unknown>): void {
  const prefix = `[bot:${scope}]`;
  const payload = meta ? { message, ...meta } : message;
  // eslint-disable-next-line no-console
  console[level](prefix, payload);
}

export function createLogger(scope: string): Logger {
  return {
    info: (message, meta) => logWithLevel('info', scope, message, meta),
    warn: (message, meta) => logWithLevel('warn', scope, message, meta),
    error: (message, meta) => logWithLevel('error', scope, message, meta),
    debug: (message, meta) => logWithLevel('debug', scope, message, meta),
  };
}
