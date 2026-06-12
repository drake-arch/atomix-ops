(() => {
  const STORAGE_KEY = 'atomix-theme';
  const THEMES = ['light', 'dark'];

  function getSavedTheme() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return THEMES.includes(saved) ? saved : 'light';
    } catch (_) {
      return 'light';
    }
  }

  function setTheme(theme) {
    const next = THEMES.includes(theme) ? theme : 'light';
    document.documentElement.setAttribute('data-atomix-theme', next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch (_) {}
    document.querySelectorAll('[data-atomix-theme-choice]').forEach((button) => {
      const active = button.getAttribute('data-atomix-theme-choice') === next;
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function buildToggle() {
    if (document.querySelector('.atomix-theme-toggle')) return;

    const wrap = document.createElement('div');
    wrap.className = 'atomix-theme-toggle';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', 'Atomix color mode');
    wrap.innerHTML = `
      <button type="button" data-atomix-theme-choice="light" aria-pressed="false" title="Use light mode">Light</button>
      <button type="button" data-atomix-theme-choice="dark" aria-pressed="false" title="Use dark mode">Dark</button>
    `;

    wrap.addEventListener('click', (event) => {
      const button = event.target.closest('[data-atomix-theme-choice]');
      if (!button) return;
      setTheme(button.getAttribute('data-atomix-theme-choice'));
    });

    document.body.appendChild(wrap);
    setTheme(document.documentElement.getAttribute('data-atomix-theme') || getSavedTheme());
  }

  setTheme(getSavedTheme());

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildToggle, { once: true });
  } else {
    buildToggle();
  }
})();
