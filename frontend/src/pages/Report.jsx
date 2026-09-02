import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const TYPES = [
  'Equipment & Lane Reports','Daily Revenue','Weekly Traffic',
  'Violations Log','Vehicle Class Split','FASTag Reconciliation'
];
const SHIFTS = [['All','All'],['Day','Day (06-14)'],['Eve','Eve (14-22)'],['Night','Night (22-06)']];

export default function Report() {
  const [f, setF] = useState({ type:TYPES[0], from:'', to:'', lane:'All Lanes', cls:'All Classes' });
  const [shift, setShift] = useState('All');
  const [data, setData] = useState(null);
  const [dlOpen, setDlOpen] = useState(false);

  async function show() {
    const p = new URLSearchParams({ ...f, shift });
    const d = await api('/api/report?' + p.toString());
    setData(d);
  }

  useEffect(() => {
    const close = () => setDlOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  function download(fmt) {
    if (!data) { alert('Generate a report first.'); return; }
    const stamp = new Date().toISOString().slice(0,10);
    if (fmt === 'csv') {
      const flat = data.rows.map(r => {
        if (r && r.total) return r.cells.map(c => typeof c === 'object' ? c.value : c);
        return r.map(c => typeof c === 'object' ? c.value : c);
      });
      const csv = [data.headers, ...flat].map(row => row.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
      a.download = `report-${stamp}.csv`;
      a.click();
    } else if (fmt === 'json') {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type:'application/json' }));
      a.download = `report-${stamp}.json`;
      a.click();
    } else if (fmt === 'print') {
      window.print();
    }
  }

  const gen = data ? new Date(data.generatedAt) : null;
  const genStr = gen ? `Generated: ${gen.getDate()}/${gen.getMonth()+1}/${gen.getFullYear()}, ${gen.toLocaleTimeString('en-GB',{hour12:true,hour:'numeric',minute:'2-digit',second:'2-digit'}).toLowerCase()}` : '';

  return (
    <>
      <PageHead icon="▤" title="Report" subtitle="Generate and download detailed operational reports" />

      <section className="card report-filters">
        <div className="rf-title">▽ Report Filters</div>
        <div className="filters-grid filters-5">
          <Lbl label="REPORT TYPE">
            <select value={f.type} onChange={e=>setF({...f,type:e.target.value})}>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </Lbl>
          <Lbl label="DATE FROM"><input type="date" value={f.from} onChange={e=>setF({...f,from:e.target.value})} /></Lbl>
          <Lbl label="DATE TO"><input type="date" value={f.to} onChange={e=>setF({...f,to:e.target.value})} /></Lbl>
          <Lbl label="LANE">
            <select value={f.lane} onChange={e=>setF({...f,lane:e.target.value})}>
              <option>All Lanes</option><option>Lane 1</option><option>Lane 2</option><option>Lane 3</option><option>Lane 4</option><option>Lane 5</option>
            </select>
          </Lbl>
          <Lbl label="VEHICLE CLASS">
            <select value={f.cls} onChange={e=>setF({...f,cls:e.target.value})}>
              <option>All Classes</option><option>Car / Jeep</option><option>LCV</option><option>Bus</option><option>3-Axle</option><option>Oversized</option>
            </select>
          </Lbl>
        </div>
        <div className="rf-foot">
          <div className="shift-group">
            <span className="muted small" style={{marginRight:8}}>SHIFT:</span>
            {SHIFTS.map(([k, lbl]) => (
              <button key={k} className={'shift-btn' + (k === shift ? ' active' : '')} onClick={() => setShift(k)}>{lbl}</button>
            ))}
          </div>
          <div className="rf-actions">
            <button className="btn-primary" onClick={show}>▥ Show Report</button>
            <div className="dl-wrap">
              <button className="btn-ghost" onClick={e=>{e.stopPropagation();setDlOpen(o=>!o);}}>⬇ Download ⌄</button>
              {dlOpen && (
                <div className="dl-menu">
                  <button onClick={()=>download('csv')}>⬇ CSV</button>
                  <button onClick={()=>download('json')}>⬇ JSON</button>
                  <button onClick={()=>download('print')}>🖨 Print</button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        {!data ? (
          <div className="report-empty">
            <div className="re-ic">▤</div>
            <div className="re-title">No Report Generated</div>
            <div className="muted small">Configure filters above and click "Show Report" to generate</div>
          </div>
        ) : (
          <>
            <div className="rep-kpis">
              {data.kpis.map((k, i) => (
                <div className="rep-kpi" key={i}>
                  <div className="rk-label">{k.label}</div>
                  <div className={`rk-value c-${k.color || 'k'}`}>{k.value}</div>
                  {k.delta && (
                    <div className="rk-delta"><span className="up">↑ {k.delta}</span> <span className="muted small">vs previous</span></div>
                  )}
                </div>
              ))}
            </div>
            <div className="rep-table-head">
              <h3>{data.title}</h3>
              <div className="muted small">{genStr}</div>
            </div>
            <table className="table">
              <thead><tr>{data.headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
              <tbody>
                {data.rows.map((r, i) => {
                  if (r && r.total) return <tr className="tot-row" key={i}>{r.cells.map((c,j) => renderCell(c,j))}</tr>;
                  return <tr key={i}>{r.map((c,j) => renderCell(c,j))}</tr>;
                })}
              </tbody>
            </table>
          </>
        )}
      </section>
    </>
  );
}

function renderCell(c, j) {
  if (c == null) return <td key={j}>—</td>;
  if (typeof c !== 'object') return <td key={j}>{c}</td>;
  switch (c.type) {
    case 'lane':      return <td key={j}><span className="lane-pill">{c.value}</span></td>;
    case 'bold':      return <td key={j} className="amt">{c.value}</td>;
    case 'violation': return <td key={j} className={c.value >= 50 ? 'spd hi' : 'amt'}>{c.value}</td>;
    case 'progress':  return <td key={j}><div className="prog-cell"><div className="prog-bar"><span style={{width:`${c.value}%`}}/></div><span className="prog-n">{c.value}%</span></div></td>;
    case 'fail':      return <td key={j}><span className={`fail-pill ${c.value >= 6 ? 'bad' : 'ok'}`}>● {c.value}</span></td>;
    case 'totlabel':  return <td key={j} className="tot-label">{c.value}</td>;
    case 'totmuted':  return <td key={j} className="muted">{c.value}</td>;
    case 'totbold':   return <td key={j} className="amt">{c.value}</td>;
    case 'totblue':   return <td key={j} className="tot-blue">{c.value}</td>;
    case 'totred':    return <td key={j} className="tot-red">{c.value}</td>;
    default: return <td key={j}>{c.value ?? ''}</td>;
  }
}

function drawBar(canvas, data, labels) {
  const dpr = window.devicePixelRatio || 1;
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width * dpr; canvas.height = r.height * dpr;
  const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
  const w = r.width, h = r.height;
  ctx.clearRect(0,0,w,h);
  const padL=40, padR=20, padT=20, padB=30, cw=w-padL-padR, ch=h-padT-padB;
  const max = Math.max(...data)*1.15;
  ctx.strokeStyle = '#eaecf0'; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
  for (let i=0;i<=4;i++){ const y=padT+ch*i/4; ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+cw,y); ctx.stroke(); }
  ctx.setLineDash([]);
  const bw = cw / data.length;
  data.forEach((v,i)=>{
    const x = padL + i*bw + bw*0.2;
    const bh = (v/max)*ch;
    const y = padT + ch - bh;
    const width = bw*0.6;
    const grad = ctx.createLinearGradient(0,y,0,y+bh);
    grad.addColorStop(0,'#4f6ff0'); grad.addColorStop(1,'#2a4cdb');
    ctx.fillStyle = grad; ctx.fillRect(x,y,width,bh);
  });
  ctx.fillStyle='#8b94a7'; ctx.font='11px -apple-system,Segoe UI,sans-serif';
  labels.forEach((lb,i)=>{
    const x = padL + i*bw + bw*0.5 - ctx.measureText(lb).width/2;
    ctx.fillText(lb, x, h-10);
  });
}

function Lbl({ label, children }) { return <label><span>{label}</span>{children}</label>; }
