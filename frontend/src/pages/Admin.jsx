import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const ROLE_OPTS = [
  'Authority (IHMCL/NHAI)','Acquirer Bank Users','System Integrator (SI)',
  'Field / Maintenance Staff','TMCC Users'
];

const ROLE_DEFS = [
  { key:'super',    name:'Super Admin',                  desc:'Full system access', users:1, color:'#0e0e0e' },
  { key:'auth',     name:'Authority (IHMCL/NHAI)',       desc:'Regulatory and administrative oversight', users:2,  color:'#e0464b' },
  { key:'tmcc',     name:'TMCC Users',                   desc:'Traffic Management & Control Centre operations', users:5,  color:'#2a4cdb' },
  { key:'acquirer', name:'Acquirer Bank Users',          desc:'Banking and transaction settlement access', users:3,  color:'#5cc26a' },
  { key:'issuer',   name:'Issuer Bank Users',            desc:'FASTag issuance and verification access', users:3,  color:'#7c3aed' },
  { key:'si',       name:'System Integrator (SI)',       desc:'Technical maintenance and system integration', users:4,  color:'#e8a52f' },
  { key:'ops',      name:'Control Centre Operators',     desc:'Real-time monitoring and lane operations', users:12, color:'#5fa8e8' },
  { key:'end',      name:'End Users (Vehicle/FASTag Users)', desc:'Limited access for vehicle/tag owners', users:1500, color:'#9333ea' },
  { key:'field',    name:'Field / Maintenance Staff',    desc:'On-site equipment maintenance and checks', users:6,  color:'#a87b2f' },
];

const MODULES = [
  { key:'dashboard',    name:'Dashboard',         desc:'Real-time KPIs and charts' },
  { key:'live',         name:'Live Streaming',    desc:'Camera feeds and lane monitoring' },
  { key:'txn',          name:'Toll Transactions', desc:'Transaction records and search' },
  { key:'reports',      name:'Reports',           desc:'Generate and download reports' },
  { key:'config',       name:'Configuration',     desc:'System and plaza settings' },
  { key:'admin',        name:'Admin Panel',       desc:'User management and roles' },
  { key:'audit',        name:'Audit Logs',        desc:'Activity and change history' },
  { key:'eticket',      name:'E-Ticket',          desc:'E-ticket acceptance and queue' },
  { key:'equipment',    name:'Equipment History', desc:'Device uptime and maintenance' },
];

const DEFAULT_PERMS = {
  super:    Object.fromEntries(MODULES.map(m => [m.key, { v:true,  e:true,  d:true  }])),
  auth:     Object.fromEntries(MODULES.map(m => [m.key, { v:true,  e:false, d:false }])),
  tmcc:     Object.fromEntries(MODULES.map(m => [m.key, { v:true,  e:m.key !== 'admin' && m.key !== 'audit', d:false }])),
  acquirer: Object.fromEntries(MODULES.map(m => [m.key, { v:m.key === 'txn' || m.key === 'reports' || m.key === 'dashboard', e:m.key === 'txn', d:false }])),
  issuer:   Object.fromEntries(MODULES.map(m => [m.key, { v:m.key !== 'admin' && m.key !== 'config', e:m.key === 'eticket', d:false }])),
  si:       Object.fromEntries(MODULES.map(m => [m.key, { v:true, e:m.key === 'config' || m.key === 'equipment', d:false }])),
  ops:      Object.fromEntries(MODULES.map(m => [m.key, { v:m.key !== 'admin' && m.key !== 'audit', e:m.key === 'live' || m.key === 'eticket', d:false }])),
  end:      Object.fromEntries(MODULES.map(m => [m.key, { v:m.key === 'eticket', e:false, d:false }])),
  field:    Object.fromEntries(MODULES.map(m => [m.key, { v:m.key === 'equipment' || m.key === 'live', e:m.key === 'equipment', d:false }])),
};

function roleClass(r) {
  if (r.startsWith('Authority')) return 'authority';
  if (r.startsWith('Acquirer'))  return 'acquirer';
  if (r.startsWith('System'))    return 'si';
  if (r.startsWith('Field'))     return 'field';
  if (r.startsWith('TMCC'))      return 'tmcc';
  return '';
}
const initials = n => n.trim().charAt(0).toUpperCase();
const PALETTE = ['#2a4cdb','#7c3aed','#16a34a','#d97706','#be185d','#0ea5e9','#ea580c'];

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [tab, setTab] = useState('users');
  const [q, setQ] = useState('');
  const [rf, setRf] = useState('All Roles');
  const [showModal, setShow] = useState(false);
  const [form, setForm] = useState({ name:'', email:'', role:ROLE_OPTS[0], plaza:'NH-48 Gurugram' });
  const [selRole, setSelRole] = useState('super');
  const [perms, setPerms] = useState(DEFAULT_PERMS);
  const togglePerm = (rk, mk, field) =>
    setPerms(p => ({ ...p, [rk]: { ...p[rk], [mk]: { ...p[rk][mk], [field]: !p[rk][mk][field] } } }));

  async function load() { setUsers(await api('/api/users')); }
  useEffect(() => { load(); }, []);

  const filtered = users.filter(u => {
    const okQ = !q || u.name.toLowerCase().includes(q.toLowerCase()) || u.email.toLowerCase().includes(q.toLowerCase());
    const okR = rf === 'All Roles' || u.role === rf;
    return okQ && okR;
  });

  async function act(u, action) {
    if (action === 'del') {
      if (!confirm(`Delete user "${u.name}"?`)) return;
      await api('/api/users/' + u.id, { method: 'DELETE' });
    } else if (action === 'toggle') {
      await api('/api/users/' + u.id, { method: 'PATCH', body: JSON.stringify({ status: u.status === 'Active' ? 'Inactive' : 'Active' }) });
    } else if (action === 'edit') {
      const newName = prompt('New name:', u.name);
      if (!newName) return;
      await api('/api/users/' + u.id, { method: 'PATCH', body: JSON.stringify({ name: newName }) });
    }
    load();
  }

  async function createUser(e) {
    e.preventDefault();
    await api('/api/users', {
      method: 'POST',
      body: JSON.stringify({ ...form, color: PALETTE[Math.floor(Math.random()*PALETTE.length)] })
    });
    setShow(false);
    setForm({ name:'', email:'', role:ROLE_OPTS[0], plaza:'NH-48 Gurugram' });
    load();
  }

  const activeCount = users.filter(u => u.status === 'Active').length;

  return (
    <>
      <PageHead icon="🛡" title="Flow Admin" subtitle="System administration · User management · Configuration"
        right={<button className="btn-primary" onClick={() => setShow(true)}>👤+ Add User</button>} />

      <section className="kpis kpis-4">
        <Kpi ic="b" icon="👥" delta="+2"    value={users.length} label="Total Users" />
        <Kpi ic="g" icon="✓"  delta="Active" value={activeCount}  label="Active Users" />
        <Kpi ic="p" icon="📄" delta="7"     value="7"             label="Roles Defined" />
        <Kpi ic="o" icon="⚠"  delta="Today" down value="3"        label="Login Failures" />
      </section>

      <div className="seg-tabs">
        {['users','roles','config','audit'].map(t => (
          <button key={t} className={'seg-tab' + (t === tab ? ' active' : '')} onClick={() => setTab(t)}>
            {t === 'users' ? 'Users' : t === 'roles' ? 'Roles' : t === 'config' ? 'Configuration' : 'Audit Logs'}
          </button>
        ))}
      </div>

      {tab === 'users' && (
        <section className="card">
          <div className="card-head">
            <div className="card-title"><h3>User Accounts</h3></div>
            <div className="filters">
              <div className="search-box"><span>🔍</span>
                <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search users..." />
              </div>
              <select className="select" value={rf} onChange={e=>setRf(e.target.value)}>
                <option>All Roles</option>
                {ROLE_OPTS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <table className="table users-table">
            <thead><tr><th>USER</th><th>ROLE</th><th>PLAZA</th><th>LAST LOGIN</th><th>STATUS</th><th className="ta-r">ACTIONS</th></tr></thead>
            <tbody>
              {filtered.map(u => (
                <tr key={u.id}>
                  <td>
                    <div className="user-cell">
                      <div className="avatar sm av-color" style={{ background: u.color }}>{initials(u.name)}</div>
                      <div><div className="uname">{u.name}</div><div className="uemail">{u.email}</div></div>
                    </div>
                  </td>
                  <td><span className={`role-tag ${roleClass(u.role)}`}>{u.role}</span></td>
                  <td className="muted">{u.plaza}</td>
                  <td className="muted">{u.last}</td>
                  <td><span className={`status-cell ${u.status === 'Active' ? 'active' : ''}`}><span className="dot" />{u.status}</span></td>
                  <td className="ta-r">
                    <div className="row-actions">
                      <button title="Edit"   onClick={() => act(u, 'edit')}>✎</button>
                      <button title="Toggle" onClick={() => act(u, 'toggle')}>⇆</button>
                      <button className="del" title="Delete" onClick={() => act(u, 'del')}>🗑</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!filtered.length && <tr><td colSpan="6" className="muted" style={{ textAlign:'center', padding:20 }}>No users match.</td></tr>}
            </tbody>
          </table>
        </section>
      )}

      {tab === 'roles' && (
        <div className="roles-layout">
          <div className="roles-list">
            {ROLE_DEFS.map(r => (
              <button
                key={r.key}
                className={'role-row' + (selRole === r.key ? ' active' : '')}
                onClick={() => setSelRole(r.key)}
              >
                <div className="role-row-ic" style={{ background:r.color + '22', color:r.color }}>👤</div>
                <div className="role-row-body">
                  <div className="role-row-head">
                    <div className="role-row-name">{r.name}</div>
                    <div className="role-row-count">{r.users.toLocaleString('en-IN')} users</div>
                  </div>
                  <div className="role-row-desc">{r.desc}</div>
                </div>
              </button>
            ))}
          </div>

          <div className="perm-panel card">
            <div className="perm-head">
              <h3>Permissions — {ROLE_DEFS.find(r => r.key === selRole)?.name}</h3>
              <div className="muted small">Module-level access control</div>
            </div>
            <div className="perm-list">
              <div className="perm-row perm-row-head">
                <div></div>
                <div className="perm-col">View</div>
                <div className="perm-col">Edit</div>
                <div className="perm-col">Delete</div>
              </div>
              {MODULES.map(m => {
                const p = perms[selRole][m.key];
                return (
                  <div className="perm-row" key={m.key}>
                    <div>
                      <div className="perm-mod">{m.name}</div>
                      <div className="muted small">{m.desc}</div>
                    </div>
                    <div className="perm-col"><PermBox checked={p.v} onChange={()=>togglePerm(selRole,m.key,'v')} /></div>
                    <div className="perm-col"><PermBox checked={p.e} onChange={()=>togglePerm(selRole,m.key,'e')} /></div>
                    <div className="perm-col"><PermBox checked={p.d} onChange={()=>togglePerm(selRole,m.key,'d')} /></div>
                  </div>
                );
              })}
            </div>
            <div className="perm-foot">
              <button className="btn-ghost" onClick={()=>setPerms(DEFAULT_PERMS)}>Reset</button>
              <button className="btn-primary" onClick={()=>alert('Permissions saved for ' + ROLE_DEFS.find(r=>r.key===selRole).name)}>Save Permissions</button>
            </div>
          </div>
        </div>
      )}

      {tab === 'config' && <ConfigTab />}

      {tab === 'audit' && <AuditTab />}

      {showModal && (
        <div className="modal" onClick={e => e.target.classList.contains('modal') && setShow(false)}>
          <div className="modal-card">
            <div className="modal-head">
              <h3>Add New User</h3>
              <button className="icon-btn" onClick={() => setShow(false)}>✕</button>
            </div>
            <form className="modal-body" onSubmit={createUser}>
              <label><span>Full Name</span>
                <input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} />
              </label>
              <label><span>Email</span>
                <input type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})} />
              </label>
              <label><span>Role</span>
                <select value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>
                  {ROLE_OPTS.map(r => <option key={r}>{r}</option>)}
                </select>
              </label>
              <label><span>Plaza</span>
                <input value={form.plaza} onChange={e=>setForm({...form,plaza:e.target.value})} />
              </label>
              <div className="modal-foot">
                <button type="button" className="btn-ghost" onClick={() => setShow(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

const AUDIT_LOGS = [
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'21 May 2026, 06:03', ok:true },
  { user:'flowadmin', action:'Logout',         module:'Auth',   ts:'21 May 2026, 06:02', ok:true },
  { user:'flowadmin', action:'Logout',         module:'Auth',   ts:'21 May 2026, 06:02', ok:true },
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'21 May 2026, 05:14', ok:true },
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'20 May 2026, 09:57', ok:true },
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'20 May 2026, 09:36', ok:true },
  { user:'flowadmin', action:'Logout',         module:'Auth',   ts:'20 May 2026, 09:32', ok:true },
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'20 May 2026, 09:17', ok:true },
  { user:'flowadmin', action:'Logout',         module:'Auth',   ts:'19 May 2026, 21:16', ok:true },
  { user:'flowadmin', action:'User Created',   module:'Admin',  ts:'19 May 2026, 14:20', ok:true },
  { user:'flowadmin', action:'Role Changed',   module:'Admin',  ts:'19 May 2026, 11:45', ok:true },
  { user:'flowadmin', action:'Config Updated', module:'Config', ts:'18 May 2026, 16:10', ok:true },
  { user:'flowadmin', action:'Login',          module:'Auth',   ts:'18 May 2026, 09:01', ok:false },
];

function AuditTab() {
  function exportCsv() {
    const headers = ['User','Action','Module','Timestamp','Status'];
    const rows = AUDIT_LOGS.map(l => [l.user, l.action, l.module, l.ts, l.ok ? 'Success' : 'Failed']);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    a.download = 'admin-audit-logs.csv';
    a.click();
  }
  return (
    <section className="card audit-card">
      <div className="audit-head">
        <h3>Admin Audit Logs</h3>
        <button className="btn-ghost audit-export" onClick={exportCsv}>⬇ Export CSV</button>
      </div>
      <table className="table audit-table">
        <thead>
          <tr><th>USER</th><th>ACTION</th><th>MODULE</th><th>TIMESTAMP</th><th>STATUS</th></tr>
        </thead>
        <tbody>
          {AUDIT_LOGS.map((l, i) => (
            <tr key={i}>
              <td className="strong">{l.user}</td>
              <td>{l.action}</td>
              <td><span className="aud-mod">{l.module}</span></td>
              <td className="muted">{l.ts}</td>
              <td><span className={'aud-status ' + (l.ok ? 'ok' : 'bad')}><i/>{l.ok ? 'Success' : 'Failed'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ConfigTab() {
  const [plaza, setPlaza] = useState({ name:'NH-48 Gurugram', id:'PL-NH48-0012', lanes:4, speed:60, anpr:true });
  const [sys, setSys]     = useState({ session:30, sync:15 });
  return (
    <div className="cfg-2col">
      <section className="card cfg-card">
        <div className="cfg-card-head">
          <h3>Plaza Configuration</h3>
          <div className="muted small">NH-48 Gurugram Toll Plaza</div>
        </div>
        <div className="cfg-fields">
          <CfgRow label="Plaza Name">
            <input value={plaza.name} onChange={e=>setPlaza({...plaza,name:e.target.value})} />
          </CfgRow>
          <CfgRow label="Plaza ID">
            <input value={plaza.id} onChange={e=>setPlaza({...plaza,id:e.target.value})} />
          </CfgRow>
          <CfgRow label="Active Lanes">
            <input type="number" value={plaza.lanes} onChange={e=>setPlaza({...plaza,lanes:+e.target.value})} />
          </CfgRow>
          <CfgRow label="Speed Limit (km/h)">
            <input type="number" value={plaza.speed} onChange={e=>setPlaza({...plaza,speed:+e.target.value})} />
          </CfgRow>
          <CfgRow label="ANPR Recognition">
            <button className={'tgl' + (plaza.anpr ? ' on' : '')} onClick={()=>setPlaza({...plaza,anpr:!plaza.anpr})} aria-label="toggle"><span/></button>
          </CfgRow>
        </div>
        <button className="btn-primary cfg-save" onClick={()=>alert('Plaza settings saved.')}>Save Plaza Settings</button>
      </section>

      <section className="card cfg-card">
        <div className="cfg-card-head">
          <h3>System Parameters</h3>
          <div className="muted small">Global MLFF system configuration</div>
        </div>
        <div className="cfg-fields">
          <CfgRow label="Session Timeout (min)">
            <input type="number" value={sys.session} onChange={e=>setSys({...sys,session:+e.target.value})} />
          </CfgRow>
          <CfgRow label="Data Sync Interval (s)">
            <input type="number" value={sys.sync} onChange={e=>setSys({...sys,sync:+e.target.value})} />
          </CfgRow>
        </div>
        <button className="btn-primary cfg-save" onClick={()=>alert('System settings saved.')}>Save System Settings</button>
      </section>
    </div>
  );
}

function CfgRow({ label, children }) {
  return (
    <div className="cfg-row">
      <div className="cfg-row-l"><span className="cfg-dot"/><span>{label}</span></div>
      <div className="cfg-row-c">{children}</div>
    </div>
  );
}

function PermBox({ checked, onChange }) {
  return (
    <button type="button" className={'perm-box' + (checked ? ' on' : '')} onClick={onChange} aria-pressed={checked}>
      {checked && <span className="perm-tick">✓</span>}
    </button>
  );
}

function Kpi({ ic, icon, value, delta, label, down }) {
  return (
    <div className="kpi">
      <div className="kpi-top">
        <div className={`kpi-icon ${ic}`}><span>{icon}</span></div>
        <span className={`delta ${down ? 'down' : 'up'}`}>{delta}</span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
