const apiBase = '/api';

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error((await res.json()).detail || 'Request failed');
  return res.json();
}

function saveToken(token) {
  localStorage.setItem('token', token.access_token);
  window.location.href = '/static/app.html';
}

document.getElementById('register-btn').onclick = async () => {
  const msg = document.getElementById('register-msg');
  msg.textContent = '';
  try {
    const data = await postJSON(`${apiBase}/register`, {
      username: document.getElementById('reg-username').value,
      name: document.getElementById('reg-name').value,
      email: document.getElementById('reg-email').value,
      password: document.getElementById('reg-password').value,
    });
    saveToken(data);
  } catch (err) {
    msg.textContent = err.message;
  }
};

document.getElementById('login-btn').onclick = async () => {
  const msg = document.getElementById('login-msg');
  msg.textContent = '';
  try {
    const data = await postJSON(`${apiBase}/login`, {
      username_or_email: document.getElementById('login-username').value,
      password: document.getElementById('login-password').value,
    });
    saveToken(data);
  } catch (err) {
    msg.textContent = err.message;
  }
};
