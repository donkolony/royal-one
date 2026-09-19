export type Theme = 'light' | 'dark';

/** The saved choice, else the system preference. Safe when storage is blocked. */
export function readStoredTheme(): Theme {
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {
    // storage blocked: fall through to the system preference
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Switch the page to `theme`; pass persist=true to remember it. */
export function applyTheme(theme: Theme, persist = false): void {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  if (!persist) return;
  try {
    localStorage.setItem('theme', theme);
  } catch {
    // storage blocked: the choice only lasts for this page view
  }
}

/** Call once before the first render so the sign-in page is themed too, not only the layouts. */
export function initTheme(): void {
  applyTheme(readStoredTheme());
}
