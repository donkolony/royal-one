import React, { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from './Button';
import { applyTheme, readStoredTheme } from '../../lib/theme';

export function DarkModeToggle() {
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'));

  useEffect(() => {
    // Follow the stored choice (or the system preference); main.tsx has already applied it at start-up.
    setIsDark(readStoredTheme() === 'dark');
  }, []);

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    applyTheme(next ? 'dark' : 'light', true);
  };

  return (
    <Button variant="ghost" size="sm" onClick={toggle} aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
      {isDark ? <Sun className="w-5 h-5" aria-hidden="true" /> : <Moon className="w-5 h-5" aria-hidden="true" />}
    </Button>
  );
}
