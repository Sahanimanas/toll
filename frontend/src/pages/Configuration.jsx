import { useEffect, useState } from 'react';
import PageHead from '../components/PageHead.jsx';
import { api } from '../api.js';

const TABS = [
  { k:'lane',   icon:'🚧', label:'Lane Config' },
  { k:'camera', icon:'📷', label:'Camera Config' },
  { k:'rfid',   icon:'📡', label:'RFID & Rates' },
  { k:'system', icon:'⚙',  label:'System Settings' },
  { k:'users',  icon:'👤', label:'Users' },
  { k:'thr',    icon:'🔔', label:'Thresholds' },
];

const INITIAL_LANES = [
  { name:'Lane 1', direction:'Entry', speed:60, headway:10, toll:185, active:true  },
  { name:'Lane 2', direction:'Entry', speed:60, headway:10, toll:185, active:true  },
  { name:'Lane 3', direction:'Exit',  speed:60, headway:10, toll:185, active:true  },
  { name:'Lane 4', direction:'Exit',  speed:60, headway:10, toll:185, active:false },
];

export default function Configuration() {
  const [tab, setTab] = useState('lane');
  const [lanes, setLanes] = useState(INITIAL_LANES);

  // Hydrate lanes from the backend SSOT once on mount; fall back to INITIAL_LANES if API is unavailable.
  useEffect(() => {
    api('/api/lanes').then(rows => { if (Array.isArray(rows) && rows.length) setLanes(rows); }).catch(()=>{});
  }, []);

  function update(i, patch) {
    setLanes(ls => ls.map((l, idx) => idx === i ? { ...l, ...patch } : l));
    const lane = lanes[i];
    if (lane && lane.id != null) {
      api('/api/lanes/' + lane.id, { method:'PUT', body: JSON.stringify(patch) }).catch(()=>{});
    }
  }

  function exportCfg() {
    const blob = new Blob([JSON.stringify({ lanes }, null, 2)], { type:'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'config.json';
    a.click();
  }

  return (
    <>
      <PageHead
        icon="⚙"
        title="Configuration"
        subtitle="System settings & component configuration"
        right={
          <div style={{display:'flex',gap:8}}>
            <button className="btn-ghost" onClick={exportCfg}>⬇ Export Config</button>
            <button className="btn-primary" onClick={()=>alert('Configuration saved.')}>✓ Save Changes</button>
          </div>
        }
      />

      <div className="cfg-tabs">
        {TABS.map(t => (
          <button key={t.k} className={'cfg-tab' + (tab === t.k ? ' active' : '')} onClick={()=>setTab(t.k)}>
            <span className="cfg-tab-ic">{t.icon}</span>{t.label}
          </button>
        ))}
      </div>

      {tab === 'lane' && (
        <div className="lane-grid">
          {lanes.map((l, i) => (
            <div className={'card lane-card' + (l.active ? '' : ' disabled')} key={i}>
              <div className="lane-head">
                <h3>{l.name}</h3>
                <div className="lane-toggle">
                  <span className={'tg-label ' + (l.active ? 'on' : 'off')}>{l.active ? 'Active' : 'Disabled'}</span>
                  <button
                    className={'tgl' + (l.active ? ' on' : '')}
                    onClick={()=>update(i,{active:!l.active})}
                    aria-label="toggle"
                  ><span/></button>
                </div>
              </div>
              <div className="lane-form">
                <Field label="DIRECTION">
                  <select value={l.direction} onChange={e=>update(i,{direction:e.target.value})} disabled={!l.active}>
                    <option>Entry</option><option>Exit</option>
                  </select>
                </Field>
                <Field label="SPEED LIMIT (KM/H)">
                  <input type="number" value={l.speed} onChange={e=>update(i,{speed:+e.target.value})} disabled={!l.active}/>
                </Field>
                <Field label="MIN HEADWAY (M)">
                  <input type="number" value={l.headway} onChange={e=>update(i,{headway:+e.target.value})} disabled={!l.active}/>
                </Field>
                <Field label="TOLL AMOUNT (₹)">
                  <input type="number" value={l.toll} onChange={e=>update(i,{toll:+e.target.value})} disabled={!l.active}/>
                </Field>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'camera' && <CameraPanel/>}
      {tab === 'rfid'   && <RfidPanel/>}
      {tab === 'system' && <SystemPanel/>}
      {tab === 'users'  && <UsersPanel/>}
      {tab === 'thr'    && <ThresholdsPanel/>}
    </>
  );
}

function Field({ label, children }) {
  return <label className="lane-field"><span>{label}</span>{children}</label>;
}

function CameraPanel() {
  const [items, setItems] = useState([]);
  const [resolutions, setResolutions] = useState(['4K UHD','1080P','720P']);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    try {
      const r = await api('/api/anpr-cameras');
      setItems(r.items || []);
      if (r.resolutions) setResolutions(r.resolutions);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  function patchLocal(id, patch) {
    setItems(xs => xs.map(c => c.id === id ? { ...c, ...patch } : c));
  }
  async function save(id, patch) {
    patchLocal(id, patch);
    try { await api('/api/anpr-cameras/' + id, { method:'PUT', body: JSON.stringify(patch) }); }
    catch (e) { setError(e.message); load(); }
  }
  async function addRow() {
    const nextLane = 'Lane ' + (Math.max(0, ...items.map(c => +String(c.lane).replace(/\D/g,'') || 0)) + 1);
    try {
      const cam = await api('/api/anpr-cameras', { method:'POST',
        body: JSON.stringify({ lane: nextLane, role:'Front', ip:'', resolution:'1080P', framerate:25, active:true }) });
      setItems(xs => [...xs, cam]);
    } catch (e) { setError(e.message); }
  }
  if (loading) return <section className="card" style={{padding:20}}>Loading…</section>;

  return (
    <section className="card" style={{padding:'18px 20px'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14}}>
        <h3 style={{margin:0,fontSize:15,fontWeight:700}}>ANPR & Surveillance Camera Settings</h3>
        <button className="btn-ghost" onClick={addRow}>+ Add Camera</button>
      </div>

      {error && <div style={{color:'#b91c1c',marginBottom:10,fontSize:13}}>{error}</div>}

      <div style={{display:'grid',gridTemplateColumns:'180px 1fr 1fr 1fr 110px',gap:14,alignItems:'center',padding:'0 4px 8px',fontSize:11,color:'var(--muted)',fontWeight:600,letterSpacing:'.04em'}}>
        <span/>
        <span>IP ADDRESS</span>
        <span>RESOLUTION</span>
        <span>FRAME RATE</span>
        <span>ACTIVE</span>
      </div>

      {items.map(c => (
        <div key={c.id}
             style={{display:'grid',gridTemplateColumns:'180px 1fr 1fr 1fr 110px',gap:14,alignItems:'center',
                     padding:'14px 4px',borderTop:'1px solid var(--line)'}}>
          <div>
            <div style={{fontWeight:700,fontSize:14}}>
              {c.kind === 'Surveillance' ? c.label : `ANPR ${c.role}`}
            </div>
            <div className="muted" style={{fontSize:12}}>
              {c.kind === 'Surveillance' ? c.zone : c.lane}
            </div>
          </div>
          <input className="cfg-inp" value={c.ip}
                 onChange={e=>patchLocal(c.id,{ip:e.target.value})}
                 onBlur={e=>save(c.id,{ip:e.target.value})}
                 disabled={!c.active}/>
          <select className="cfg-inp" value={c.resolution}
                  onChange={e=>save(c.id,{resolution:e.target.value})}
                  disabled={!c.active}>
            {resolutions.map(r => <option key={r}>{r}</option>)}
          </select>
          <input type="number" className="cfg-inp" value={c.framerate}
                 onChange={e=>patchLocal(c.id,{framerate:+e.target.value})}
                 onBlur={e=>save(c.id,{framerate:+e.target.value})}
                 disabled={!c.active}/>
          <button className={'tgl' + (c.active ? ' on' : '')}
                  onClick={()=>save(c.id,{active:!c.active})}
                  aria-label="toggle"><span/></button>
        </div>
      ))}

      {!items.length && <div className="muted" style={{padding:20,textAlign:'center'}}>No cameras configured.</div>}
    </section>
  );
}

function RfidPanel() {
  const [rfid, setRfid] = useState(null);
  const [rates, setRates] = useState([]);
  const [error, setError] = useState('');

  async function load() {
    try {
      const r = await api('/api/rfid-config');
      setRfid(r.rfid); setRates(r.rates || []);
    } catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);

  function patchRfid(patch) { setRfid(r => ({ ...r, ...patch })); }
  async function saveRfid(patch) {
    patchRfid(patch);
    try { await api('/api/rfid-config', { method:'PUT', body: JSON.stringify(patch) }); }
    catch (e) { setError(e.message); load(); }
  }
  function patchRate(id, patch) { setRates(rs => rs.map(r => r.id === id ? { ...r, ...patch } : r)); }
  async function saveRate(id, patch) {
    patchRate(id, patch);
    try { await api('/api/toll-rates/' + id, { method:'PUT', body: JSON.stringify(patch) }); }
    catch (e) { setError(e.message); load(); }
  }

  if (!rfid) return <section className="card" style={{padding:20}}>Loading…</section>;

  return (
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,alignItems:'start'}}>
      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>RFID Reader Configuration</h3>
        {error && <div style={{color:'#b91c1c',marginBottom:10,fontSize:13}}>{error}</div>}
        <div style={{display:'grid',gap:14}}>
          <Field label="NPCI HOST URL">
            <input className="cfg-inp" value={rfid.npciHost}
                   onChange={e=>patchRfid({npciHost:e.target.value})}
                   onBlur={e=>saveRfid({npciHost:e.target.value})}/>
          </Field>
          <Field label="API TIMEOUT (MS)">
            <input type="number" className="cfg-inp" value={rfid.timeoutMs}
                   onChange={e=>patchRfid({timeoutMs:+e.target.value})}
                   onBlur={e=>saveRfid({timeoutMs:+e.target.value})}/>
          </Field>
          <Field label="READ RATE THRESHOLD (%)">
            <input type="number" className="cfg-inp" value={rfid.readRatePct}
                   onChange={e=>patchRfid({readRatePct:+e.target.value})}
                   onBlur={e=>saveRfid({readRatePct:+e.target.value})}/>
          </Field>
          <Field label="RETRY ATTEMPTS">
            <input type="number" className="cfg-inp" value={rfid.retryAttempts}
                   onChange={e=>patchRfid({retryAttempts:+e.target.value})}
                   onBlur={e=>saveRfid({retryAttempts:+e.target.value})}/>
          </Field>

          <ToggleRow title="Auto Blacklist Lookup" sub="Check NPCI blacklist on each read"
                     on={rfid.autoBlacklist} onChange={v=>saveRfid({autoBlacklist:v})}/>
          <ToggleRow title="Duplicate Tag Filter" sub="Ignore reads within 5 seconds"
                     on={rfid.dedupFilter} onChange={v=>saveRfid({dedupFilter:v})}/>
        </div>
      </section>

      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>Toll Rate Configuration</h3>
        <div style={{display:'grid',gap:10}}>
          {rates.map(r => (
            <div key={r.id} style={{display:'grid',gridTemplateColumns:'1fr 140px',gap:12,alignItems:'center',
                                    background:'var(--blue-soft,#f1f4ff)',padding:'10px 14px',borderRadius:10}}>
              <div style={{display:'flex',alignItems:'center',gap:12}}>
                <span style={{fontSize:22}}>{r.icon}</span>
                <div>
                  <div style={{fontWeight:700,fontSize:14}}>{r.label}</div>
                  <div className="muted" style={{fontSize:12}}>{r.sub}</div>
                </div>
              </div>
              <div style={{display:'flex',alignItems:'center',gap:8}}>
                <span style={{color:'var(--muted)'}}>₹</span>
                <input type="number" className="cfg-inp" value={r.amount}
                       onChange={e=>patchRate(r.id,{amount:+e.target.value})}
                       onBlur={e=>saveRate(r.id,{amount:+e.target.value})}/>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SystemPanel() {
  const [s, setS] = useState(null);
  const [error, setError] = useState('');
  async function load() {
    try { setS(await api('/api/system-settings')); } catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);
  function patch(section, patch) { setS(x => ({ ...x, [section]: { ...x[section], ...patch } })); }
  async function save(patchObj) {
    try { await api('/api/system-settings', { method:'PUT', body: JSON.stringify(patchObj) }); }
    catch (e) { setError(e.message); load(); }
  }
  if (!s) return <section className="card" style={{padding:20}}>Loading…</section>;

  const FEATURES = [
    ['autoViolation','Auto Violation Detection','Automatically flag violations from sensor data'],
    ['bankSync','Bank Auto-sync','Sync transactions to bank every 5 minutes'],
    ['cctvRecording','CCTV Recording','Record all camera feeds to local storage'],
    ['nightMode','Night Mode Cameras','Switch cameras to IR mode after sunset'],
    ['smsAlerts','SMS Alerts','Send SMS for critical equipment failures'],
    ['maintenance','Maintenance Mode','Suppress alerts during scheduled maintenance'],
    ['debugLogging','Debug Logging','Verbose logging for diagnostics'],
  ];

  return (
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,alignItems:'start'}}>
      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>General Settings</h3>
        {error && <div style={{color:'#b91c1c',marginBottom:10,fontSize:13}}>{error}</div>}
        <div style={{display:'grid',gap:14}}>
          {[
            ['plazaName','PLAZA NAME','text'],
            ['plazaCode','PLAZA CODE','text'],
            ['timeZone','TIME ZONE','text'],
            ['retentionDays','DATA RETENTION (DAYS)','number'],
            ['reportEmail','REPORT EMAIL','text'],
          ].map(([k,label,type]) => (
            <Field key={k} label={label}>
              <input type={type} className="cfg-inp" value={s.general[k]}
                     onChange={e=>patch('general',{[k]: type==='number'?+e.target.value:e.target.value})}
                     onBlur={e=>save({general:{[k]: type==='number'?+e.target.value:e.target.value}})}/>
            </Field>
          ))}
        </div>
      </section>

      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>Feature Toggles</h3>
        <div style={{display:'grid',gap:10}}>
          {FEATURES.map(([k,title,sub]) => (
            <ToggleRow key={k} title={title} sub={sub} on={!!s.features[k]}
                       onChange={v=>{ patch('features',{[k]:v}); save({features:{[k]:v}}); }}/>
          ))}
        </div>
      </section>
    </div>
  );
}

function UsersPanel() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [edit, setEdit] = useState(null); // user being edited or { id:null } for new
  async function load() { try { setUsers(await api('/api/system-users')); } catch (e) { setError(e.message); } }
  useEffect(() => { load(); }, []);

  async function submit(form) {
    try {
      if (form.id) await api('/api/system-users/' + form.id, { method:'PUT', body: JSON.stringify(form) });
      else         await api('/api/system-users', { method:'POST', body: JSON.stringify(form) });
      setEdit(null); load();
    } catch (e) { setError(e.message); }
  }
  async function del(id) {
    if (!confirm('Delete this user?')) return;
    try { await api('/api/system-users/' + id, { method:'DELETE' }); load(); } catch (e) { setError(e.message); }
  }

  const colors = ['#2563eb','#db2777','#7c3aed','#059669','#d97706'];
  const init = n => (n||'?').trim().charAt(0).toUpperCase();
  const colorFor = i => colors[i % colors.length];

  return (
    <section className="card" style={{padding:'18px 20px'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14}}>
        <h3 style={{margin:0,fontSize:15,fontWeight:700}}>System Users</h3>
        <button className="btn-primary" onClick={()=>setEdit({ id:null, name:'', username:'', role:'Operator', email:'', status:'Active' })}>+ Add User</button>
      </div>
      {error && <div style={{color:'#b91c1c',marginBottom:10,fontSize:13}}>{error}</div>}

      <div style={{display:'grid',gridTemplateColumns:'1.4fr 1fr 1fr 1.4fr 1fr 90px 110px',gap:10,
                   padding:'10px 4px',fontSize:11,color:'var(--muted)',fontWeight:600,letterSpacing:'.04em',
                   background:'#f8f9fb',borderRadius:8}}>
        <span>NAME</span><span>USERNAME</span><span>ROLE</span><span>EMAIL</span><span>LAST LOGIN</span><span>STATUS</span><span>ACTIONS</span>
      </div>

      {users.map((u, i) => (
        <div key={u.id} style={{display:'grid',gridTemplateColumns:'1.4fr 1fr 1fr 1.4fr 1fr 90px 110px',gap:10,
                                alignItems:'center',padding:'14px 4px',borderBottom:'1px solid var(--line)'}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <span style={{width:30,height:30,borderRadius:'50%',background:colorFor(i),color:'#fff',
                          display:'grid',placeItems:'center',fontWeight:700,fontSize:13}}>{init(u.name)}</span>
            <span style={{fontWeight:600,fontSize:14}}>{u.name}</span>
          </div>
          <code style={{fontSize:13}}>{u.username}</code>
          <span style={{display:'inline-block',padding:'4px 10px',background:'var(--blue-soft,#eef2ff)',
                        color:'var(--blue,#2a4cdb)',borderRadius:999,fontSize:12,fontWeight:600,width:'fit-content'}}>{u.role}</span>
          <span style={{fontSize:13}}>{u.email}</span>
          <span style={{fontSize:13,fontFamily:'monospace'}}>{u.last}</span>
          <span style={{color: u.status==='Active' ? '#059669' : '#b91c1c', fontSize:13, fontWeight:600}}>● {u.status}</span>
          <div style={{display:'flex',gap:10}}>
            <button onClick={()=>setEdit({ ...u })} style={{background:'none',border:'none',color:'var(--blue,#2a4cdb)',cursor:'pointer',fontWeight:600,padding:0}}>Edit</button>
            {u.username !== 'admin' && (
              <button onClick={()=>del(u.id)} style={{background:'none',border:'none',color:'#dc2626',cursor:'pointer',fontWeight:600,padding:0}}>Delete</button>
            )}
          </div>
        </div>
      ))}

      {edit && <UserModal user={edit} onCancel={()=>setEdit(null)} onSave={submit}/>}
    </section>
  );
}

function UserModal({ user, onCancel, onSave }) {
  const [f, setF] = useState(user);
  const ROLES = ['Super Admin','Supervisor','Operator','Report Manager'];
  return (
    <div onClick={onCancel}
         style={{position:'fixed',inset:0,background:'rgba(0,0,0,.4)',display:'grid',placeItems:'center',zIndex:50}}>
      <div onClick={e=>e.stopPropagation()} className="card"
           style={{padding:'22px 24px',width:420,display:'grid',gap:14}}>
        <h3 style={{margin:0,fontSize:16,fontWeight:700}}>{f.id ? 'Edit User' : 'Add User'}</h3>
        <Field label="NAME"><input className="cfg-inp" value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></Field>
        <Field label="USERNAME"><input className="cfg-inp" value={f.username} onChange={e=>setF({...f,username:e.target.value})}/></Field>
        <Field label="EMAIL"><input className="cfg-inp" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></Field>
        <Field label="ROLE">
          <select className="cfg-inp" value={f.role} onChange={e=>setF({...f,role:e.target.value})}>
            {ROLES.map(r => <option key={r}>{r}</option>)}
          </select>
        </Field>
        <Field label="STATUS">
          <select className="cfg-inp" value={f.status} onChange={e=>setF({...f,status:e.target.value})}>
            <option>Active</option><option>Inactive</option>
          </select>
        </Field>
        <div style={{display:'flex',gap:10,justifyContent:'flex-end',marginTop:6}}>
          <button className="btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn-primary" onClick={()=>onSave(f)}>Save</button>
        </div>
      </div>
    </div>
  );
}

function ThresholdsPanel() {
  const [t, setT] = useState(null);
  const [c, setC] = useState(null);
  const [error, setError] = useState('');
  async function load() {
    try { const r = await api('/api/thresholds'); setT(r.thresholds); setC(r.comm); } catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);
  function patchT(p) { setT(x => ({ ...x, ...p })); }
  function patchC(p) { setC(x => ({ ...x, ...p })); }
  async function saveT(p) { patchT(p); try { await api('/api/thresholds', { method:'PUT', body: JSON.stringify({thresholds:p}) }); } catch (e) { setError(e.message); load(); } }
  async function saveC(p) { patchC(p); try { await api('/api/thresholds', { method:'PUT', body: JSON.stringify({comm:p}) }); } catch (e) { setError(e.message); load(); } }
  if (!t || !c) return <section className="card" style={{padding:20}}>Loading…</section>;

  const SLIDERS = [
    ['speedKmh',         'SPEED ALERT (KM/H)',        40, 100, 1, v => v + ' km/h'],
    ['violationPct',     'VIOLATION RATE ALERT (%)',  1,  20,  1, v => v + '%'],
    ['failedTxn',        'FAILED TXN ALERT (COUNT)',  1,  50,  1, v => String(v)],
    ['cameraDowntimeMin','CAMERA DOWNTIME ALERT (MIN)',1, 30,  1, v => v + ' min'],
    ['rfidReadRatePct',  'RFID READ RATE MIN (%)',    80, 100, 1, v => v + '%'],
    ['pingTimeoutMs',    'PING TIMEOUT (MS)',         50, 500, 10, v => v + 'ms'],
  ];

  return (
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:18,alignItems:'start'}}>
      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>Alert Thresholds</h3>
        {error && <div style={{color:'#b91c1c',marginBottom:10,fontSize:13}}>{error}</div>}
        <div style={{display:'grid',gap:18}}>
          {SLIDERS.map(([k,label,min,max,step,fmt]) => (
            <div key={k}>
              <div style={{display:'flex',justifyContent:'space-between',marginBottom:6}}>
                <span style={{fontSize:11.5,fontWeight:600,color:'var(--muted)',letterSpacing:'.04em'}}>{label}</span>
                <span style={{fontWeight:700,color:'var(--blue,#2a4cdb)'}}>{fmt(t[k])}</span>
              </div>
              <input type="range" min={min} max={max} step={step} value={t[k]}
                     onChange={e=>patchT({[k]:+e.target.value})}
                     onMouseUp={e=>saveT({[k]:+e.target.value})}
                     onTouchEnd={e=>saveT({[k]:+e.target.value})}
                     style={{width:'100%'}}/>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:11,color:'var(--muted)',marginTop:2}}>
                <span>{fmt(min)}</span><span>{fmt(max)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card" style={{padding:'18px 20px'}}>
        <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>Communication Settings</h3>
        <div style={{display:'grid',gap:14}}>
          <Field label="ALERT EMAIL RECIPIENTS">
            <textarea className="cfg-inp" rows={2} value={c.alertEmails}
                      onChange={e=>patchC({alertEmails:e.target.value})}
                      onBlur={e=>saveC({alertEmails:e.target.value})}/>
          </Field>
          <Field label="SMS ALERT NUMBERS">
            <input className="cfg-inp" value={c.smsNumbers}
                   onChange={e=>patchC({smsNumbers:e.target.value})}
                   onBlur={e=>saveC({smsNumbers:e.target.value})}/>
          </Field>
          <Field label="WEBHOOK URL">
            <input className="cfg-inp" value={c.webhookUrl}
                   onChange={e=>patchC({webhookUrl:e.target.value})}
                   onBlur={e=>saveC({webhookUrl:e.target.value})}/>
          </Field>
          <ToggleRow title="Enable Email Alerts" sub="" on={c.emailAlertsEnabled}
                     onChange={v=>saveC({emailAlertsEnabled:v})}/>
        </div>
      </section>
    </div>
  );
}

function ToggleRow({ title, sub, on, onChange }) {
  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',
                 background:'var(--blue-soft,#f1f4ff)',padding:'12px 14px',borderRadius:10}}>
      <div>
        <div style={{fontWeight:700,fontSize:14}}>{title}</div>
        <div className="muted" style={{fontSize:12}}>{sub}</div>
      </div>
      <button className={'tgl' + (on ? ' on' : '')} onClick={()=>onChange(!on)} aria-label="toggle"><span/></button>
    </div>
  );
}
