export type Toast = {
  title: string;
  description?: string;
  kind?: 'success' | 'error' | 'info';
};

type Listener = (t: Toast) => void;

let listener: Listener | null = null;

export function setToastListener(fn: Listener) {
  listener = fn;
}

export function showToast(toast: Toast) {
  if (listener) listener(toast);
}
