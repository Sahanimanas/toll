import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const PER = 12;
const INIT = { from:'', to:'', lane:'All Lanes', cls:'All Classes', status:'All Status', reg:'', txn:'' };

export default function Transactions() {
  const [items, setItems] = useState([]);
  const [f, setF] = useState(INIT);
  const [page, setPage] = useState(1);

  async function load() {
    const params = new URLSearchParams();
    Object.entries(f).forEach(([k,v]) => { if (v && !v.startsWith?.('All')) params.set(k, v); });
    const r = await api('/api/transactions?' + params.toString());
    setItems(r.items);
    setPage(1);
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line
  }, [f]);

  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / PER));
  const slice = items.slice((page-1)*PER, page*PER);
  const count = s => items.filter(r => r.status === s).length;

  function exportCSV() {
    const headers = ['TXN ID','Date','Time','Lane','Vehicle Reg','Class','Tag ID','Speed (km/h)','Amount (INR)','Mode','Status'];
    const rows = items.map(r => [r.id,r.date,r.time,r.lane,r.reg,r.cls,r.tag,r.speed,r.amount,r.mode,r.status]);
    const csv = [headers, ...rows].map(row => row.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    a.download = `toll-transactions-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  return (
    <>
      <PageHead icon="📋" title="Toll Transactions"
        subtitle={<><span>{total}</span> records found · <span>{f.lane}</span></>}
        right={
          <>
            <button className="btn-ghost" onClick={exportCSV}>⬇ Export CSV</button>
            <button className="btn-primary" onClick={load}>▽ Apply Filters</button>
          </>
        }
      />

      <section className="card filters-card">
        <div className="filters-grid">
          <Lbl label="DATE FROM"><input type="date" value={f.from} onChange={e=>setF({...f,from:e.target.value})} /></Lbl>
          <Lbl label="DATE TO"><input type="date" value={f.to} onChange={e=>setF({...f,to:e.target.value})} /></Lbl>
          <Lbl label="LANE ID">
            <select value={f.lane} onChange={e=>setF({...f,lane:e.target.value})}>
              <option>All Lanes</option><option>Lane 1</option><option>Lane 2</option><option>Lane 3</option><option>Lane 4</option><option>Lane 5</option>
            </select>
          </Lbl>
          <Lbl label="VEHICLE CLASS">
            <select value={f.cls} onChange={e=>setF({...f,cls:e.target.value})}>
              <option>All Classes</option><option>Car / Jeep</option><option>LCV</option><option>Bus</option><option>3-Axle</option><option>Oversized</option>
            </select>
          </Lbl>
          <Lbl label="STATUS">
            <select value={f.status} onChange={e=>setF({...f,status:e.target.value})}>
              <option>All Status</option><option>Paid</option><option>Failed</option><option>Pending</option><option>Exempted</option>
            </select>
          </Lbl>
          <Lbl label="VEHICLE REG. NO."><input value={f.reg} onChange={e=>setF({...f,reg:e.target.value})} placeholder="e.g. HR26..." /></Lbl>
          <Lbl label="TRANSACTION ID"><input value={f.txn} onChange={e=>setF({...f,txn:e.target.value})} placeholder="e.g. TXN..." /></Lbl>
        </div>
        <div className="filters-foot">
          <button className="link-btn" onClick={() => setF(INIT)}>⟳ Reset Filters</button>
          <div className="status-counts">
            <span className="cnt paid">✓ <b>{count('Paid')}</b> Paid</span>
            <span className="cnt failed">✕ <b>{count('Failed')}</b> Failed</span>
            <span className="cnt pending">⧗ <b>{count('Pending')}</b> Pending</span>
            <span className="cnt exempt">↔ <b>{count('Exempted')}</b> Exempted</span>
          </div>
        </div>
      </section>

      <section className="card">
        <table className="table txn-table">
          <thead>
            <tr><th>TXN ID</th><th>DATE &amp; TIME</th><th>LANE</th><th>VEHICLE REG.</th><th>CLASS</th><th>TAG ID</th><th>SPEED</th><th>AMOUNT</th><th>MODE</th><th>STATUS</th></tr>
          </thead>
          <tbody>
            {slice.map(r => (
              <tr key={r.id}>
                <td><span className="txn-id" onClick={() => alert(`Transaction ${r.id}\n\nDate: ${r.date} ${r.time}\nLane: ${r.lane}\nVehicle: ${r.reg}\nClass: ${r.cls}\nTag: ${r.tag}\nSpeed: ${r.speed} km/h\nAmount: ₹${r.amount}\nMode: ${r.mode}\nStatus: ${r.status}`)}>{r.id}</span></td>
                <td><div className="dt-main">{r.date}</div><div className="dt-sub">{r.time}</div></td>
                <td><span className="lane-pill">{r.lane}</span></td>
                <td><span className="reg">{r.reg}</span></td>
                <td>{r.cls}</td>
                <td><span className="tag">{r.tag}</span></td>
                <td className={`spd ${r.speed >= 60 ? 'hi' : ''}`}>{r.speed} km/h</td>
                <td className="amt">₹{r.amount}</td>
                <td>{r.mode}</td>
                <td><span className={`st-pill ${r.status.toLowerCase()}`}>{r.status}</span></td>
              </tr>
            ))}
            {!slice.length && <tr><td colSpan="10" className="muted" style={{textAlign:'center',padding:30}}>No records match the filters.</td></tr>}
          </tbody>
        </table>
        <div className="pager">
          <button className="btn-ghost" disabled={page<=1} onClick={()=>setPage(page-1)}>‹ Prev</button>
          <span className="muted">Page {page} of {pages}</span>
          <button className="btn-ghost" disabled={page>=pages} onClick={()=>setPage(page+1)}>Next ›</button>
        </div>
      </section>
    </>
  );
}

function Lbl({ label, children }) {
  return <label><span>{label}</span>{children}</label>;
}
