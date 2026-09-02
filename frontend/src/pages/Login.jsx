import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setSession } from '../api.js';

export default function Login() {
  const [username, setU] = useState('');
  const [password, setP] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      setSession(r.token, r.user);
      nav('/dashboard');
    } catch (e2) {
      setErr(e2.message || 'Invalid credentials. Try admin / 12345678');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-body">
      <div className="auth-shell-wrap">
        <div className="auth-shell">
          <aside className="auth-hero">
            <div className="auth-hero-inner">
              <div className="brand">
                <div className="brand-mark">MLFF</div>
                <div className="brand-name">Tolling System</div>
              </div>
              <h1>Multi-Lane<br/>Free Flow Tolling</h1>
              <p>Real-time vehicle detection, ANPR, FASTag reconciliation, and revenue analytics — all in one operator console.</p>
              <ul className="hero-points">
                <li><HeroIcon name="eye"/>      <span>Live lane monitoring</span></li>
                <li><HeroIcon name="bolt"/>     <span>Automatic toll calculation</span></li>
                <li><HeroIcon name="shield"/>   <span>Violation & exception handling</span></li>
                <li><HeroIcon name="chart"/>    <span>Daily revenue insights</span></li>
              </ul>
              <div className="hero-footer">© 2026 MLFF Tolling</div>
            </div>
          </aside>

          <main className="auth-card">
            <header>
              <h2>Welcome back</h2>
              <p>Sign in to access the operator dashboard.</p>
            </header>

            <form onSubmit={submit}>
              <label>
                <span>Username</span>
                <div className="inp-wrap">
                  <FieldIcon name="user"/>
                  <input value={username} onChange={e=>setU(e.target.value)} placeholder="admin" autoComplete="username" required />
                </div>
              </label>

              <label>
                <span>Password</span>
                <div className="inp-wrap">
                  <FieldIcon name="lock"/>
                  <input type={showPw ? 'text' : 'password'} value={password} onChange={e=>setP(e.target.value)} placeholder="••••••••" autoComplete="current-password" required />
                  <button type="button" className="inp-eye" onClick={()=>setShowPw(s=>!s)} tabIndex={-1} aria-label="toggle password">
                    {showPw ? '🙈' : '👁'}
                  </button>
                </div>
              </label>

              <div className="row-between">
                <label className="checkbox"><input type="checkbox"/><span>Remember me</span></label>
                <a href="#" className="link">Forgot password?</a>
              </div>

              <button type="submit" className="btn-primary auth-submit" disabled={busy}>
                {busy ? 'Signing in…' : 'Sign in'}
              </button>

              {err && <p className="error">{err}</p>}

              <div className="demo-creds">
                <span className="demo-tag">DEMO</span>
                <span><b>admin</b> / <b>12345678</b></span>
              </div>
            </form>

            <footer className="auth-foot">
              Don't have an account? <a href="#" className="link">Request access</a>
            </footer>

            <div className="card-powered">
              <span>Powered by</span>
              <img src="/xenochiper-logo.png" alt="Xenochiper"/>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

function HeroIcon({ name }) {
  const paths = {
    eye:    'M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z M12 9a3 3 0 100 6 3 3 0 000-6z',
    bolt:   'M13 2L3 14h7l-1 8 10-12h-7l1-8z',
    shield: 'M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4z',
    chart:  'M3 3v18h18 M7 14l3-3 3 3 4-5',
  };
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[name]}/>
    </svg>
  );
}

function FieldIcon({ name }) {
  const paths = {
    user: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2 M12 11a4 4 0 100-8 4 4 0 000 8z',
    lock: 'M5 11h14v10H5z M8 11V7a4 4 0 018 0v4',
  };
  return (
    <svg className="inp-ic" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[name]}/>
    </svg>
  );
}
