const form = document.getElementById('resetForm');
const msg = document.getElementById('resetMessage');
const token = new URLSearchParams(location.search).get('token') || '';
form.addEventListener('submit', async e => {
  e.preventDefault();
  const password = document.getElementById('newPassword').value;
  const confirm = document.getElementById('confirmPassword').value;
  if(password !== confirm) { msg.textContent = 'Passwords do not match.'; return; }
  if(!token) { msg.textContent = 'Reset token is missing. Request a new link.'; return; }
  msg.textContent = 'Updating password…';
  try {
    const r = await fetch('/admin/api/reset-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,password})});
    const d = await r.json(); if(!r.ok) throw new Error(d.detail || 'Reset failed.');
    msg.textContent = d.message; form.querySelector('button').disabled = true;
  } catch(err) { msg.textContent = err.message; }
});
