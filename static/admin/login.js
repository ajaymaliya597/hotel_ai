const $ = (id) => document.getElementById(id);
$('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault(); const msg = $('loginMessage'); msg.textContent = 'Signing in…';
  try {
    const r = await fetch('/admin/api/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:$('email').value,password:$('password').value})});
    const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Sign in failed.');
    window.location.assign(d.redirect || '/admin/dashboard');
  } catch (err) { msg.textContent = err.message; }
});
$('forgotLink').addEventListener('click', e => { e.preventDefault(); $('forgotModal').hidden = false; $('recoveryEmail').focus(); });
$('closeModal').addEventListener('click', () => $('forgotModal').hidden = true);
$('forgotModal').addEventListener('click', e => { if(e.target === $('forgotModal')) $('forgotModal').hidden = true; });
$('forgotForm').addEventListener('submit', async e => {
  e.preventDefault(); const msg = $('forgotMessage'); msg.textContent = 'Sending request…';
  try {
    const r = await fetch('/admin/api/forgot-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:$('recoveryEmail').value})});
    const d = await r.json(); if(!r.ok) throw new Error(d.detail || 'Could not send reset email.');
    msg.textContent = d.message;
  } catch(err) { msg.textContent = err.message; }
});
