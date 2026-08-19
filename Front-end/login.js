const authForm = document.querySelector('#auth-form');
const authTabs = document.querySelectorAll('[data-mode]');
const switcher = document.querySelector('[data-switch]');
const card = document.querySelector('.auth-card');
const title = document.querySelector('#auth-title');
const copy = document.querySelector('#auth-copy');
const submitLabel = document.querySelector('#submit-label');
const authStatus = document.querySelector('#auth-status');
let mode = 'signin';
function setMode(nextMode) {
  mode = nextMode; card.classList.toggle('signup', mode === 'signup');
  authTabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.mode === mode));
  title.textContent = mode === 'signup' ? 'Create your account.' : 'Welcome back.';
  copy.textContent = mode === 'signup' ? 'Start exploring renewable intelligence in minutes.' : 'Sign in to view your energy intelligence workspace.';
  submitLabel.textContent = mode === 'signup' ? 'Create account' : 'Sign in';
  switcher.textContent = mode === 'signup' ? 'Sign in instead' : 'Create an account'; switcher.dataset.switch = mode === 'signup' ? 'signin' : 'signup'; authStatus.textContent = '';
}
authTabs.forEach((tab) => tab.addEventListener('click', () => setMode(tab.dataset.mode)));
switcher.addEventListener('click', () => setMode(switcher.dataset.switch));
document.querySelectorAll('.password-toggle').forEach((button) => button.addEventListener('click', () => { const input = button.previousElementSibling; input.type = input.type === 'password' ? 'text' : 'password'; button.textContent = input.type === 'password' ? '◉' : '◌'; }));
document.querySelector('#forgot-password').addEventListener('click', (event) => { event.preventDefault(); authStatus.textContent = 'Password reset instructions would be sent to your work email.'; });
authForm.addEventListener('submit', (event) => {
  event.preventDefault(); if (!authForm.checkValidity()) { authForm.reportValidity(); return; } const data = new FormData(authForm); const email = String(data.get('email')).trim().toLowerCase(); const password = String(data.get('password'));
  if (!email || !password) return; if (mode === 'signup' && password !== data.get('confirmPassword')) { authStatus.textContent = 'Passwords do not match.'; return; }
  if (mode === 'signup') localStorage.setItem('renewcastDemoUser', JSON.stringify({ name: data.get('name') || 'RenewCast user', email }));
  const user = JSON.parse(localStorage.getItem('renewcastDemoUser') || 'null');
  if (mode === 'signin' && (!user || user.email !== email)) { authStatus.textContent = 'No local demo account found for this email. Create an account instead.'; return; }
  localStorage.setItem('renewcastSession', email); authStatus.textContent = `Welcome${data.get('name') ? `, ${data.get('name')}` : ''}! Opening your Wind dashboard…`; setTimeout(() => { window.location.href = 'wind.html'; }, 650);
});
