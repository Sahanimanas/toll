const TOKEN_KEY = 'mlff_token';
const USER_KEY  = 'mlff_user';

export function getToken() { return localStorage.getItem(TOKEN_KEY); }
export function getUser()  { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
export function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = 'Bearer ' + token;
  const base = import.meta.env.VITE_BACKEND_URL || '';
  const url = /^https?:\/\//.test(path) ? path : base + path;
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401 && !path.endsWith('/login')) {
    clearSession();
    window.location.href = '/login';
    return;
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.error || res.statusText);
  }
  return res.json();
}
