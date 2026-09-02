import { useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const PER = 12;
const INIT = { from:'', to:'', lane:'All Lanes', cls:'All Classes', equipment:'— Select Equipment —', reg:'' };

export default function Equipment() {
  const [f, setF] = useState(INIT);
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [page, setPage] = useState(1);

  async function apply() {
    if (!f.from || !f.to || f.equipment === '— Select Equipment —') {
      alert('Please fill Date From, Date To and Equipment.');
      return;
    }
    const params = new URLSearchParams(f);
    try {
      const r = await api('/api/equipment-history?' + params.toString());
      setItems(r.items);
      setLoaded(true);
      setPage(1);
    } catch (e) { alert(e.message || 'Could not load equipment history.'); }
  }
  function reset() { setF(INIT); setItems([]); setLoaded(false); }
  function exportCSV() {
    if (!items.length) { alert('Apply filters first.'); return; }
    const headers = ['Read ID','Timestamp','Equipment','Lane','Vehicle Reg','Class','Value','Confidence (%)','Status'];
    const rows = items.map(r => [r.id,r.timestamp,r.equipment,r.lane,r.reg,r.cls,r.value,r.conf,r.status]);
    const csv = [headers, ...rows].map(row => row.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    a.download = `equipment-history-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / PER));
  const slice = items.slice((page-1)*PER, page*PER);

  return (
    <>
      <PageHead icon="▦" title="Equipment History"
        subtitle={<>Raw sensor read logs · <span>{loaded ? `${f.equipment} · ${f.lane}` : 'All equipment · All lanes'}</span></>}
        right={
          <>
            <button className="btn-ghost" onClick={exportCSV}>⬇ Export CSV</button>
            <button className="btn-primary" onClick={apply}>▽ Apply Filters</button>
          </>
        }
      />

      <section className="card filters-card">
        <div className="filters-grid filters-6">
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
          <Lbl label="EQUIPMENT">
            <select value={f.equipment} onChange={e=>setF({...f,equipment:e.target.value})}>
              <option>— Select Equipment —</option><option>ANPR</option><option>RFID</option><option>Lidar</option><option>4D Radar</option>
            </select>
          </Lbl>
          <Lbl label="VEHICLE REG NO."><input value={f.reg} onChange={e=>setF({...f,reg:e.target.value})} placeholder="e.g. HR26..." /></Lbl>
        </div>
        <div className="filters-foot">
          <button className="link-btn" onClick={reset}>⟳ Reset Filters</button>
          <div className="status-counts">
            <span className="cnt eq-anpr">📷 ANPR: <b>50</b></span>
            <span className="cnt eq-rfid">📡 RFID: <b>50</b></span>
            <span className="cnt eq-lidar">⚡ Lidar: <b>50</b></span>
            <span className="cnt eq-radar">▣ 4D Radar: <b>50</b></span>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h3 style={{margin:0,fontSize:14,color:'var(--muted)',fontWeight:600}}>
            {loaded ? `${f.equipment} reads · ${items.length} records` : 'Awaiting filter selection'}
          </h3>
        </div>
        {!loaded ? (
          <div className="eq-empty">
            <div className="eq-empty-ic">▽</div>
            <div className="eq-empty-title">No Data Loaded</div>
            <div className="muted small">Fill in <b>Date From</b>, <b>Date To</b> and <b>Equipment</b>, then click <span className="link">Apply Filters</span> to load data.</div>
            <div className="muted small">Lane ID, Vehicle Class and Vehicle Reg No. are optional.</div>
          </div>
        ) : (
          <>
            <table className="table txn-table">
              <thead>
                <tr><th>READ ID</th><th>TIMESTAMP</th><th>EQUIPMENT</th><th>LANE</th><th>VEHICLE REG.</th><th>CLASS</th><th>VALUE</th><th>CONFIDENCE</th><th>STATUS</th></tr>
              </thead>
              <tbody>
                {slice.map(r => {
                  const stCls = r.status === 'OK' ? 'paid' : r.status === 'Error' ? 'failed' : 'pending';
                  return (
                    <tr key={r.id}>
                      <td><span className="aid">{r.id}</span></td>
                      <td><div className="dt-main">{r.timestamp}</div></td>
                      <td>{r.equipment}</td>
                      <td><span className="lane-pill">{r.lane}</span></td>
                      <td className="vrn">{r.reg}</td>
                      <td>{r.cls}</td>
                      <td className="reg">{r.value}</td>
                      <td className={r.conf < 80 ? 'spd hi' : ''}>{r.conf}%</td>
                      <td><span className={`st-pill ${stCls}`}>{r.status}</span></td>
                    </tr>
                  );
                })}
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
          </>
        )}
      </section>
    </>
  );
}

function Lbl({ label, children }) { return <label><span>{label}</span>{children}</label>; }
