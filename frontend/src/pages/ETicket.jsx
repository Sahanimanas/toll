import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const typeClass = t => t.toLowerCase().replace(/[^a-z]/g, '');

export default function ETicket() {
  const [items, setItems] = useState([]);
  const [sel, setSel] = useState(null);
  const [type, setType] = useState('All Types');
  const [q, setQ] = useState('');
  const [size, setSize] = useState(7);
  const [page, setPage] = useState(1);

  async function load() {
    const p = new URLSearchParams();
    if (type !== 'All Types') p.set('type', type);
    if (q) p.set('q', q);
    const r = await api('/api/violations?' + p.toString());
    setItems(r.items);
  }
  useEffect(() => { load(); }, []);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); /* eslint-disable-line */ }, [type, q]);

  async function act(id, status) {
    await api('/api/violations/' + id, { method: 'PATCH', body: JSON.stringify({ status }) });
    load();
  }

  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / size));
  const start = (page - 1) * size;
  const slice = items.slice(start, start + size);

  const counts = items.reduce((a, v) => (a[v.type] = (a[v.type]||0)+1, a), {});
  const sc = s => items.filter(v => v.status === s).length;
  const max = Math.max(...['No FASTag','Speeding','Wrong Lane','Axle Violation'].map(k => counts[k] || 0), 1);
  const brk = [
    { ic:'🪪', name:'No FASTag',      n: counts['No FASTag'] || 0 },
    { ic:'🚀', name:'Speeding',       n: counts['Speeding']  || 0 },
    { ic:'🚥', name:'Wrong Lane',     n: counts['Wrong Lane']|| 0 },
    { ic:'⚖',  name:'Axle Violation', n: counts['Axle Violation'] || 0 }
  ];

  function exportCSV() {
    const headers = ['Violation ID','VRN','Date','Time','Lane','Type','Speed','Fine','Status'];
    const rows = items.map(v => [v.id,v.vrn,v.date,v.time,v.lane,v.type,v.speed||'—',v.fine,v.status]);
    const csv = [headers, ...rows].map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    a.download = `e-tickets-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  return (
    <>
      <PageHead title="E-Ticket" subtitle="Violation management and e-challan processing"
        right={
          <>
            <span className="status-pill warn-pill">{sc('Pending')} Pending Review</span>
            <button className="btn-ghost" onClick={() => alert(`E-Notice will be generated for ${sc('Pending')} pending violations.`)}>▤ Generate E-Notice</button>
            <button className="btn-primary" onClick={exportCSV}>⬇ Export Tickets</button>
          </>
        }
      />

      <section className="row row-1-1">
        <div className="card">
          <div className="card-head">
            <h3 style={{margin:0,fontSize:15,fontWeight:700}}>Violation Preview</h3>
            <div className="seg-tabs">
              <button className="seg-tab active">📷 Image</button>
              <button className="seg-tab">🎬 Video</button>
            </div>
          </div>
          {sel ? (
            <div className="preview has-img">
              <div className="pv-frame" />
              <div className="pv-tag">{sel.type.toUpperCase()}</div>
              <div className="pv-bot">
                <div>
                  <div className="pv-plate">{sel.vrn}</div>
                  <div className="muted small" style={{color:'#cbd5e1'}}>{sel.lane} · {sel.date} {sel.time}</div>
                </div>
                <div>
                  <div style={{fontWeight:700}}>₹{sel.fine}</div>
                  <div className="muted small" style={{color:'#cbd5e1'}}>{sel.speed ? sel.speed + ' km/h' : '—'}</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="preview">
              <div className="preview-empty">
                <div className="prev-warn">⚠</div>
                <div className="prev-title">No violation selected</div>
                <div className="muted small">Click a row in the table below to view details</div>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{margin:'0 0 14px',fontSize:15,fontWeight:700}}>Violation Breakdown</h3>
          <ul className="brk-list">
            {brk.map(b => (
              <li key={b.name}>
                <span>{b.ic} {b.name}</span>
                <div className="brk-bar"><span style={{width:`${(b.n/max)*100}%`}} /></div>
                <span className="brk-n">{b.n}</span>
              </li>
            ))}
          </ul>
          <div className="status-grid">
            <Mini cls="amber"   ic="⧗" n={sc('Pending')}   lbl="Pending" />
            <Mini cls="green"   ic="✓" n={sc('Accepted')}  lbl="Accepted" />
            <Mini cls="red"     ic="✕" n={sc('Rejected')}  lbl="Rejected" />
            <Mini cls="amber-l" ic="✓" n={sc('Exempted')}  lbl="Exempted" />
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div className="card-title">
            <h3 style={{margin:0,fontSize:15}}>Violation Records <span className="muted small">{items.length} total</span></h3>
          </div>
          <div className="filters">
            <div className="search-box"><span>🔍</span>
              <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search VRN…" />
            </div>
            <select className="select" value={type} onChange={e=>setType(e.target.value)}>
              <option>All Types</option><option>No FASTag</option><option>Speeding</option><option>Wrong Lane</option><option>Axle Violation</option>
            </select>
          </div>
        </div>
        <table className="table eticket-table">
          <thead>
            <tr><th>VIOLATION ID</th><th>VRN</th><th>DATE &amp; TIME</th><th>LANE</th><th>TYPE</th><th>SPEED</th><th>FINE</th><th>STATUS</th><th>ACTIONS</th></tr>
          </thead>
          <tbody>
            {slice.map(v => {
              const spd = v.speed != null ? `${v.speed} km/h` : '—';
              const stCls = v.status === 'Pending' ? 'pending' : v.status === 'Accepted' ? 'paid' : v.status === 'Rejected' ? 'failed' : 'exempted';
              return (
                <tr key={v.id} className={v.id === sel?.id ? 'selected' : ''} onClick={() => setSel(v)}>
                  <td className="aid">{v.id}</td>
                  <td className="vrn">{v.vrn}</td>
                  <td><div className="dt-main">{v.date}</div><div className="dt-sub">{v.time}</div></td>
                  <td><span className="lane-pill">{v.lane}</span></td>
                  <td><span className={`vio-type ${typeClass(v.type)}`}>{v.type}</span></td>
                  <td className={v.speed >= 80 ? 'spd hi' : 'muted'}>{spd}</td>
                  <td className="amt">₹{v.fine}</td>
                  <td><span className={`st-pill ${stCls}`}>{v.status}</span></td>
                  <td onClick={e=>e.stopPropagation()}>
                    {v.status === 'Pending' ? (
                      <>
                        <button className="act-btn accept" onClick={()=>act(v.id,'Accepted')}>Accept</button>
                        <button className="act-btn reject" onClick={()=>act(v.id,'Rejected')}>Reject</button>
                        <button className="act-btn exempt" onClick={()=>act(v.id,'Exempted')}>Exempt</button>
                      </>
                    ) : <span className={`done-tag ${v.status.toLowerCase()}`}>{v.status}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="pager pager-size">
          <span className="muted">{total ? `Showing ${start+1}–${start+slice.length} of ${total} records` : 'Showing 0–0 of 0 records'}</span>
          <div className="size-group">
            <span className="muted">Show:</span>
            {[7,14,21].map(s => (
              <button key={s} className={'size-btn' + (s===size?' active':'')} onClick={()=>{setSize(s);setPage(1);}}>{s}</button>
            ))}
          </div>
          <div className="page-nums">
            <button className="pg-btn" disabled={page<=1} onClick={()=>setPage(page-1)}>‹</button>
            {Array.from({length:pages},(_,i)=>i+1).map(n => (
              <button key={n} className={'pg-btn' + (n===page?' active':'')} onClick={()=>setPage(n)}>{n}</button>
            ))}
            <button className="pg-btn" disabled={page>=pages} onClick={()=>setPage(page+1)}>›</button>
          </div>
        </div>
      </section>
    </>
  );
}

function Mini({ cls, ic, n, lbl }) {
  return (
    <div className={`stat-mini ${cls}`}>
      <div className="mini-ic">{ic}</div>
      <div className="mini-n">{n}</div>
      <div className="muted small">{lbl}</div>
    </div>
  );
}
