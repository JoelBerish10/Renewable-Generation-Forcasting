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
