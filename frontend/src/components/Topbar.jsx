import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api, clearSession, getUser } from '../api.js';
import Icon from './Icon.jsx';

const LANGS = [
  { code:'en', label:'English',    flag:'🇬🇧' },
  { code:'hi', label:'हिन्दी',       flag:'🇮🇳' },
  { code:'ru', label:'Russian',    flag:'🇷🇺' },
  { code:'pt', label:'Portuguese', flag:'🇵🇹' },
  { code:'da', label:'Danish',     flag:'🇩🇰' },
  { code:'nl', label:'Dutch',      flag:'🇳🇱' },
  { code:'ro', label:'Romanian',   flag:'🇷🇴' },
];

const CRUMB = {
  '/dashboard': 'Dashboard',
  '/admin': 'Admin',
  '/live': 'Live Streaming',
  '/transactions': 'Toll Transactions',
  '/audit': 'Audit',
  '/eticket': 'E-Ticket',
  '/equipment': 'Equipment History',
  '/nms': 'Nms',
  '/report': 'Report',
  '/control': 'Control Center',
  '/config': 'Configuration'
};

const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const pad = n => String(n).padStart(2, '0');

function fmtTime(iso) {
  const d = new Date(iso);
  let h = d.getHours(), m = pad(d.getMinutes()), ap = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  return `${h}:${m} ${ap}`;
}

export default function Topbar() {
  const [now, setNow] = useState(new Date());
  const [open, setOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const [profOpen, setProfOpen] = useState(false);
  const [lang, setLang] = useState(() => localStorage.getItem('mlff_lang') || 'en');
  const [dark, setDark] = useState(() => localStorage.getItem('mlff_dark') === '1');
  const [notif, setNotif] = useState({ unread:0, items:[] });
  const popRef = useRef(null);
  const langRef = useRef(null);
  const profRef = useRef(null);
  const loc = useLocation();
  const nav = useNavigate();
  const user = getUser() || { name:'Flow Admin', email:'admin@flow.com', role:'admin' };

  useEffect(() => {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('mlff_dark', dark ? '1' : '0');
  }, [dark]);

  useEffect(() => { localStorage.setItem('mlff_lang', lang); }, [lang]);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    api('/api/notifications').then(setNotif).catch(()=>{});
  }, []);

  useEffect(() => {
    function onDoc(e) {
      if (open && popRef.current && !popRef.current.contains(e.target)) setOpen(false);
      if (langOpen && langRef.current && !langRef.current.contains(e.target)) setLangOpen(false);
      if (profOpen && profRef.current && !profRef.current.contains(e.target)) setProfOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open, langOpen, profOpen]);

  function signOut() {
    api('/api/auth/logout', { method:'POST' }).catch(()=>{});
    clearSession();
    nav('/login');
  }

  async function markAll() {
    await api('/api/notifications/read-all', { method:'POST' }).catch(()=>{});
    setNotif(n => ({ unread:0, items: n.items.map(i => ({ ...i, read:true })) }));
  }
  async function clearAll() {
    await api('/api/notifications/clear', { method:'POST' }).catch(()=>{});
    setNotif({ unread:0, items:[] });
  }

  const iconFor = k => k === 'error' ? 'ban' : k === 'warn' ? 'bell' : 'check';
  const colorFor = k => k === 'error' ? 'r' : k === 'warn' ? 'o' : 'g';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="icon-btn" onClick={() => document.body.classList.toggle('sidebar-collapsed')} aria-label="toggle sidebar">☰</button>
        <div className="crumbs">
          <span className="muted">MLFF</span>
          <span className="sep">›</span>
          <b>{CRUMB[loc.pathname] || 'Page'}</b>
        </div>
      </div>
      <div className="topbar-right">
        <div className="clock">
          <div>{`${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`}</div>
          <div className="muted small">
            {`${DAYS[now.getDay()]}, ${now.getDate()} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`}
          </div>
        </div>
        <div className="notif-wrap" ref={popRef}>
          <button className="icon-btn bell" onClick={()=>setOpen(o=>!o)}>🔔{notif.unread > 0 && <span className="bell-dot" />}</button>
          {open && (
            <div className="notif-pop">
              <div className="notif-head">
                <div>
                  <div className="notif-title">Notifications</div>
                  <div className="muted small">{notif.unread} unread</div>
                </div>
                <div className="notif-actions">
                  <button className="link-blue" onClick={markAll}>Mark all read</button>
                  <button className="link-muted" onClick={clearAll}>Clear</button>
                </div>
              </div>
              <div className="notif-list">
                {notif.items.length === 0 && <div className="notif-empty muted small">No notifications</div>}
                {notif.items.map(n => (
                  <div className={'notif-item' + (n.read ? ' read' : '')} key={n.id}>
                    <div className={`notif-ic c-${colorFor(n.kind)}`}><Icon name={iconFor(n.kind)} size={14}/></div>
                    <div className="notif-body">
                      <div className="notif-row">
                        <div className="notif-h">{n.title}</div>
                        <div className="notif-t">{fmtTime(n.time)}</div>
                        {!n.read && <span className="notif-dot"/>}
                      </div>
                      <div className="notif-msg">{n.body}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="notif-foot"><button className="link-blue" onClick={()=>setOpen(false)}>View all notifications</button></div>
            </div>
          )}
        </div>
        <button className="icon-btn" onClick={()=>setDark(d=>!d)} aria-label="toggle theme">{dark ? '☀' : '🌙'}</button>

        <div className="lang-wrap" ref={langRef}>
          <button className="lang-btn" onClick={()=>setLangOpen(o=>!o)}>🌐 {(LANGS.find(l=>l.code===lang)||LANGS[0]).code.toUpperCase()} {(LANGS.find(l=>l.code===lang)||LANGS[0]).flag}</button>
          {langOpen && (
            <div className="lang-pop">
              <div className="lang-head">
                <div className="lang-title">SELECT LANGUAGE</div>
                <div className="muted small">Global translations active</div>
              </div>
              <div className="lang-list">
                {LANGS.map(l => (
                  <button key={l.code} className={'lang-row' + (l.code === lang ? ' active' : '')} onClick={()=>{setLang(l.code);setLangOpen(false);}}>
                    <span className="lang-flag">{l.flag}</span>
                    <span className="lang-name">{l.label}</span>
                    {l.code === lang && <span className="lang-check"><Icon name="check" size={14}/></span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="prof-wrap" ref={profRef}>
          <div className="profile" onClick={()=>setProfOpen(o=>!o)}>
            <div className="avatar sm">{(user.name || 'F')[0]}</div>
            <div>
              <div className="user-name">{user.name || 'Flow Admin'}</div>
              <div className="user-role">{user.role || 'admin'}</div>
            </div>
            <span className="muted">⌄</span>
          </div>
          {profOpen && (
            <div className="prof-pop">
              <div className="prof-head">
                <div className="prof-name">{user.name || 'Flow Admin'}</div>
                <div className="muted small">{user.email || 'admin@flow.com'}</div>
              </div>
              <button className="prof-row" onClick={()=>{setProfOpen(false);nav('/admin');}}><Icon name="users" size={16}/> My Profile</button>
              <button className="prof-row" onClick={()=>{setProfOpen(false);nav('/config');}}><Icon name="settings" size={16}/> Settings</button>
              <div className="prof-sep"/>
              <button className="prof-row danger" onClick={signOut}><Icon name="exit" size={16}/> Sign Out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
