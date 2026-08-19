/* Shared navigation polish for every RenewCast page. */
(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.body.classList.add('page-ready');

  document.querySelectorAll('a[href]').forEach((link) => {
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || /^(mailto:|tel:|javascript:)/i.test(href) || link.target === '_blank') return;

    link.addEventListener('click', (event) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      document.body.classList.add('page-leaving');
      window.setTimeout(() => { window.location.href = href; }, reduceMotion ? 0 : 180);
    });
  });

  const menuButton = document.querySelector('.menu-button');
  const navLinks = document.querySelector('.nav-links');
  if (menuButton && navLinks) {
    menuButton.addEventListener('click', () => {
      const open = navLinks.classList.toggle('is-open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('.solution-card').forEach((card) => {
    const destination = card.querySelector('a[href]');
    if (!destination) return;
    card.tabIndex = 0;
    card.setAttribute('role', 'link');
    card.setAttribute('aria-label', `Open ${destination.textContent.trim()}`);
    card.addEventListener('click', (event) => {
      if (!event.target.closest('a, button')) destination.click();
    });
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        destination.click();
      }
    });
  });

  document.querySelectorAll('.energy-toggle a').forEach((link) => {
    link.addEventListener('click', () => document.body.classList.add('energy-switching'));
  });
})();
