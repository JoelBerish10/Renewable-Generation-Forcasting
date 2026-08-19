const form = document.querySelector('#contact-form');
const status = document.querySelector('#form-status');
form?.addEventListener('submit', (event) => {
  event.preventDefault();
  const name = new FormData(form).get('name')?.trim() || 'there';
  status.textContent = `Thanks, ${name}. Your message is ready to send—we’ll be in touch soon.`;
  form.reset();
});
