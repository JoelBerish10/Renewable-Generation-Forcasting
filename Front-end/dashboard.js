document.querySelectorAll('.location-select').forEach((button) => {
  const locations = button.textContent.includes('Solar') ? ['Solar Farm A', 'Solar Farm B', 'Rooftop Array C'] : ['Wind Farm A', 'Wind Farm B', 'Coastal Farm C'];
  let position = 0;
  button.addEventListener('click', () => { position = (position + 1) % locations.length; button.childNodes[0].nodeValue = `${locations[position]} `; });
});
document.querySelectorAll('.time-button').forEach((button) => {
  button.addEventListener('click', () => { const isDay = button.textContent.includes('24'); button.childNodes[0].nodeValue = isDay ? '48 HOURS ' : '24 HOURS '; });
});
const updated = document.querySelector('.sidebar-bottom small');
if (updated) updated.textContent = `Snapshot ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

const sidebar = document.querySelector('.sidebar');
if (sidebar) {
  const toggle = document.createElement('button');
  toggle.className = 'sidebar-toggle';
  toggle.type = 'button';
  toggle.setAttribute('aria-label', 'Collapse sidebar');
  toggle.setAttribute('aria-expanded', 'true');
  toggle.textContent = '‹';
  document.body.append(toggle);
  toggle.addEventListener('click', () => {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    toggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    toggle.setAttribute('aria-expanded', String(!collapsed));
  });
}

document.querySelector('.avatar')?.addEventListener('click', () => { window.location.href = 'login.html'; });

const sideLinks = [...document.querySelectorAll('.side-nav a[href^="#"]')];
const allSideLinks = [...document.querySelectorAll('.side-nav a')];
const moveSidebarSelection = (link) => {
  const index = allSideLinks.indexOf(link);
  if (index >= 0) sidebar?.style.setProperty('--active-nav-index', index);
};
const setActiveLink = (targetId) => {
  sideLinks.forEach((link) => {
    const selected = link.getAttribute('href') === `#${targetId}`;
    link.classList.toggle('active', selected);
    link.toggleAttribute('aria-current', selected);
    if (selected) moveSidebarSelection(link);
  });
};

const dashboardLink = document.querySelector('.side-nav a[href$=".html"]');
const setDashboardActive = () => {
  if (!dashboardLink) return;
  document.querySelectorAll('.side-nav a').forEach((link) => {
    const selected = link === dashboardLink;
    link.classList.toggle('active', selected);
    link.toggleAttribute('aria-current', selected);
    if (selected) moveSidebarSelection(link);
  });
};

allSideLinks.forEach((link) => link.addEventListener('click', () => moveSidebarSelection(link)));

sideLinks.forEach((link) => {
  link.addEventListener('click', () => setActiveLink(link.getAttribute('href').slice(1)));
});

const dashboardSections = [
  ['forecast', document.querySelector('#forecast')],
  ['data', document.querySelector('#data')],
  ['analytics', document.querySelector('#analytics')]
].filter(([, section]) => section);

if ('IntersectionObserver' in window) {
  const sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) setActiveLink(visible.target.id);
  }, { rootMargin: '-18% 0px -55% 0px', threshold: [0.1, 0.35] });
  dashboardSections.forEach(([, section]) => sectionObserver.observe(section));
}

window.addEventListener('scroll', () => {
  if (window.scrollY < 80) setDashboardActive();
}, { passive: true });
