import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const PER = 12;

export default function Audit() {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [f, setF] = useState({ status:'All Status', bank:'All Banks', date:'', q:'' });

  async function load() {
    const p = new URLSearchParams();
    Object.entries(f).forEach(([k,v]) => { if (v && !v.startsWith?.('All')) p.set(k, v); });
    const r = await api('/api/audit?' + p.toString());
    setItems(r.items);
    setPage(1);
  }
  useEffect(() => { load(); }, []);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); /* eslint-disable-line */ }, [f]);

  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / PER));
  const slice = items.slice((page-1)*PER, page*PER);

  async function retry(aid) {
    await api(`/api/audit/${aid}/retry`, { method: 'POST' });
    load();
  }
  async function resyncAll() {
    if (!confirm('Re-sync all failed records?')) return;
    const r = await api('/api/audit/resync-failed', { method: 'POST' });
    alert(`Re-synced ${r.count} records.`);
    load();
  }
  function exportCSV() {
    const headers = ['Audit ID','Transaction ID','VRN','Amount','Bank','Bank Reference','Sent At','Settled At','Tag Balance','Status'];
    const rows = items.map(r => [r.aid,r.txn,r.vrn,r.amount,r.bank,r.ref,r.sent,r.settled,r.tagBal,r.status]);
    const csv = [headers, ...rows].map(row => row.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    a.download = `audit-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  return (
    <>
      <PageHead icon="🛡" title="Audit" subtitle="Transaction mapping & bank settlement reconciliation"
        right={
          <>
            <button className="btn-ghost" onClick={exportCSV}>⬇ Export</button>
            <button className="btn-primary" onClick={resyncAll}>⟳ Re-sync All Failed</button>
          </>
        }
      />

      <section className="audit-kpis">
        <AKpi label="TOTAL MAPPED" val="12,284" cls="ink" foot="of 12,840 transactions" bar={95.7} />
        <AKpi label="SETTLED"      val="11,890" cls="green" foot={<><span className="dot ok"/> 96.8% success rate</>} />
        <AKpi label="FAILED"       val="38"     cls="red"   foot={<><span className="dot err"/> Needs retry</>} />
        <AKpi label="PENDING"      val="356"    cls="amber" foot={<><span className="dot warn"/> Processing</>} />
      </section>

      <section className="card audit-filter">
        <select className="filter-sel" value={f.status} onChange={e=>setF({...f,status:e.target.value})}>
          <option>All Status</option><option>Success</option><option>Failed</option><option>Pending</option>
        </select>
        <div className="search-box wide"><span>🔍</span>
          <input value={f.q} onChange={e=>setF({...f,q:e.target.value})} placeholder="Search TxnID / VRN / Bank Ref…" />
        </div>
        <select className="filter-sel" value={f.bank} onChange={e=>setF({...f,bank:e.target.value})}>
          <option>All Banks</option><option>NPCI/HDFC</option><option>NPCI/SBI</option><option>NPCI/ICICI</option><option>NPCI/AXIS</option><option>NPCI/PNB</option>
        </select>
        <input className="filter-sel" type="date" value={f.date} onChange={e=>setF({...f,date:e.target.value})} />
        <span className="muted ta-r" style={{marginLeft:'auto'}}>{total} records</span>
      </section>

      <section className="card">
        <table className="table audit-table">
          <thead>
            <tr><th><input type="checkbox" /></th><th>AUDIT ID</th><th>TRANSACTION ID</th><th>VRN</th><th>AMOUNT</th><th>BANK</th><th>BANK REFERENCE</th><th>SENT AT</th><th>SETTLED AT</th><th>TAG BALANCE</th><th>STATUS</th><th>ACTION</th></tr>
          </thead>
          <tbody>
            {slice.map(r => (
              <tr key={r.aid}>
                <td><input type="checkbox" /></td>
                <td className="aid">{r.aid}</td>
                <td><span className="txn-id">{r.txn}</span></td>
                <td className="vrn">{r.vrn}</td>
                <td className="amt">₹{r.amount}</td>
                <td className="bank">{r.bank}</td>
                <td className="ref">{r.ref}</td>
                <td className="ts">{r.sent}</td>
                <td className="ts">{r.settled}</td>
                <td className="amt">{r.tagBal}</td>
                <td><span className={`st-pill ${r.status.toLowerCase()}`}>{r.status}</span></td>
                <td>
                  {r.status === 'Failed'
                    ? <button className="retry" onClick={()=>retry(r.aid)}>⟳ Retry</button>
                    : <button className="view">View</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager pager-size">
          <span className="muted">Showing {total} records</span>
          <div className="page-nums">
            <button className="btn-ghost" disabled={page<=1} onClick={()=>setPage(page-1)}>← Prev</button>
            {Array.from({length:pages},(_,i)=>i+1).map(n => (
              <button key={n} className={'pg-btn' + (n===page?' active':'')} onClick={()=>setPage(n)}>{n}</button>
            ))}
            <button className="btn-ghost" disabled={page>=pages} onClick={()=>setPage(page+1)}>Next →</button>
          </div>
        </div>
      </section>
    </>
  );
}

function AKpi({ label, val, cls, foot, bar }) {
  return (
    <div className="aud-card">
      <div className="aud-label">{label}</div>
      <div className={`aud-val ${cls}`}>{val}</div>
      <div className="muted small">{foot}</div>
      {bar != null && <div className="aud-bar"><span style={{width:`${bar}%`}} /></div>}
    </div>
  );
}
