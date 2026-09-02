import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3D, GroupBars, LineChart, Donut } from '../components/charts.jsx';
import Icon from '../components/Icon.jsx';

const STATS = [
  { ic:'dollar',   label:'TOTAL REVENUE',  value:'₹24.8L', color:'b' },
  { ic:'truck',    label:'TOTAL VEHICLES', value:'12,840', color:'g' },
  { ic:'card',     label:'TRANSACTIONS',   value:'12,284', color:'p' },
  { ic:'ban',      label:'VIOLATIONS',     value:'556',    color:'r' },
  { ic:'columns',  label:'ACTIVE LANES',   value:'4 / 4',  color:'t' },
  { ic:'card',     label:'FAILED TXNS',    value:'38',     color:'o' },
];

const EQUIP = [
  { ic:'camera', name:'CAMERA', total:9, status:'DEGRADED', stColor:'amber', active:8, inactive:1 },
  { ic:'wifi',   name:'RFID',   total:5, status:'DEGRADED', stColor:'amber', active:4, inactive:1 },
  { ic:'bulb',   name:'RADAR',  total:4, status:'ONLINE',   stColor:'green', active:4, inactive:0 },
  { ic:'grid',   name:'LIDAR',  total:4, status:'DEGRADED', stColor:'amber', active:3, inactive:1 },
  { ic:'idCard', name:'ANPR',   total:9, status:'DEGRADED', stColor:'amber', active:7, inactive:2 },
];

const VC = [
  { label:'Car / Jeep',    value:38, color:'#2a4cdb' },
  { label:'LCV / Mini Bus',value:23, color:'#5fa8e8' },
  { label:'Bus / Truck',   value:16, color:'#5cc26a' },
  { label:'3-Axle Vehicle',value:11, color:'#e8a52f' },
  { label:'Over Sized',    value:12, color:'#e0464b' },
];

const LANE_STATUS = [
  { lane:'Lane 1', anpr:1, rfid:1, radar:1, lidar:1, lc:1, st:'Healthy',  c:'green' },
  { lane:'Lane 2', anpr:1, rfid:1, radar:1, lidar:0, lc:1, st:'Degraded', c:'amber' },
  { lane:'Lane 3', anpr:1, rfid:0, radar:1, lidar:1, lc:1, st:'Degraded', c:'amber' },
  { lane:'Lane 4', anpr:0, rfid:1, radar:0, lidar:0, lc:1, st:'Critical', c:'red'   },
  { lane:'Mid-1',  anpr:1, rfid:1, radar:1, lidar:1, lc:1, st:'Healthy',  c:'green' },
];

function useClock() {
  const [t, setT] = useState(new Date());
  useEffect(() => { const id = setInterval(() => setT(new Date()), 1000); return () => clearInterval(id); }, []);
  return t;
}

export default function ControlCenter() {
  const nav = useNavigate();
  const t = useClock();
  const time = t.toLocaleTimeString('en-US', { hour12:true, hour:'2-digit', minute:'2-digit', second:'2-digit' });
  const date = t.toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric', year:'numeric' }).toUpperCase();

  function fs() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }

  return (
    <div className="cc-wrap">
      <header className="cc-head card">
        <div className="cc-h-left">
          <div className="cc-logo"><Icon name="briefcase" size={24} stroke="#fff"/></div>
          <div>
            <h1>CONTROL CENTER</h1>
            <div className="cc-sub">NH-48 MLFF OPERATIONS HUB</div>
          </div>
        </div>
        <div className="cc-h-center">
          <div className="cc-clock">
            <div className="cc-time">{time}</div>
            <div className="cc-date">{date}</div>
          </div>
          <div className="cc-weather">
            <div className="cc-wx-ic"><Icon name="sun" size={22} stroke="#f59e0b"/></div>
            <div>
              <div className="cc-wx-t">28°C</div>
              <div className="cc-wx-s">CLEAR · GURUGRAM</div>
            </div>
          </div>
        </div>
        <div className="cc-h-right">
          <span className="cc-live"><i/> SYSTEM_ACTIVE_LIVE</span>
          <button className="cc-icon-btn" aria-label="alerts"><Icon name="bell" size={18}/><i className="cc-dot"/></button>
          <button className="cc-btn cc-btn-green" onClick={()=>window.location.reload()}><Icon name="refresh" size={15} stroke="#fff"/> REFRESH</button>
          <button className="cc-btn cc-btn-blue" onClick={fs}><Icon name="maximize" size={15} stroke="#fff"/> FULLSCREEN</button>
          <button className="cc-btn cc-btn-dark" onClick={()=>nav('/dashboard')}><Icon name="exit" size={15} stroke="#fff"/> EXIT TO DASHBOARD</button>
        </div>
      </header>

      <div className="cc-stat-row">
        {STATS.map((s,i) => (
          <div className="card cc-stat" key={i}>
            <div className={`cc-stat-ic c-${s.color}`}><Icon name={s.ic} size={18}/></div>
            <div>
              <div className="cc-stat-l">{s.label}</div>
              <div className="cc-stat-v">{s.value}</div>
            </div>
          </div>
        ))}
        <div className="card cc-eticket">
          <div className="cc-et-head">
            <span className="cc-et-title"><Icon name="ticket" size={14}/> E-TICKET</span>
            <span className="cc-et-feed">LIVE FEED</span>
          </div>
          <div className="cc-et-grid">
            <div><div className="cc-et-l">ACCEPTED</div><div className="cc-et-v g">12,450</div></div>
            <div><div className="cc-et-l">REJECTED</div><div className="cc-et-v r">556</div></div>
            <div><div className="cc-et-l">EXEMPTED</div><div className="cc-et-v o">442</div></div>
          </div>
        </div>
      </div>

      <div className="cc-row-2">
        <section className="card cc-chart">
          <div className="cc-card-head"><h3>TRANSACTION VOLUME</h3><span className="cc-live-sm"><i/>LIVE</span></div>
          <BarChart3D data={[1820, 2010, 1640, 1880, 2150, 2380, 1450]} labels={['MON','TUE','WED','THU','FRI','SAT','SUN']} height={260} />
        </section>

        <section className="card cc-equip-card">
          <div className="cc-card-head"><h3>REAL-TIME EQUIPMENT STATUS</h3><span className="cc-live-sm"><i/>LIVE</span></div>
          <div className="cc-equip-grid">
            {EQUIP.map((e,i) => (
              <div className={`cc-equip ${e.stColor}`} key={i}>
                <div className="cc-eq-top">
                  <div className="cc-eq-ic"><Icon name={e.ic} size={16}/></div>
                  <div className="cc-eq-tot"><div className="n">{e.total}</div><div className="l">TOTAL</div></div>
                </div>
                <div className="cc-eq-name">{e.name}</div>
                <div className={`cc-eq-st ${e.stColor}`}><i/> {e.status}</div>
                <div className="cc-eq-ai">
                  <div><div className="n">{e.active}</div><div className="l">ACTIVE</div></div>
                  <div><div className="n">{e.inactive}</div><div className="l">INACTIVE</div></div>
                </div>
                <div className={`cc-eq-bar ${e.stColor}`}/>
              </div>
            ))}
          </div>
        </section>

        <section className="card cc-vc">
          <div className="cc-card-head">
            <div>
              <h3>VEHICLE CLASSIFICATION</h3>
              <div className="cc-sub-sm">DISTRIBUTION · TODAY</div>
            </div>
            <div className="cc-ic-chip"><Icon name="pie" size={16}/></div>
          </div>
          <div className="cc-donut-wrap">
            <Donut segments={VC.map(v => ({ value:v.value, color:v.color }))} size={200} />
            <div className="cc-donut-center"><div className="n">12,840</div><div className="l">TOTAL</div></div>
          </div>
          <div className="cc-vc-legend">
            {VC.map((v,i) => (
              <div className="cc-vc-row" key={i}>
                <span className="cc-vc-dot" style={{background:v.color}}/>
                <span className="cc-vc-l">{v.label}</span>
                <span className="cc-vc-bar"><span style={{width:`${v.value*2}%`, background:v.color}}/></span>
                <span className="cc-vc-p">{v.value}%</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="cc-row-3">
        <section className="card cc-chart">
          <div className="cc-card-head">
            <h3>LANE PERFORMANCE</h3>
            <div className="cc-legend-sm"><span><i style={{background:'#0e0e0e'}}/>RFID</span><span><i style={{background:'#a87b2f'}}/>ANPR</span></div>
            <div className="cc-ic-chip"><Icon name="barChart" size={16}/></div>
          </div>
          <GroupBars a={[840,910,1020,760]} b={[820,890,990,720]} labels={['LANE 1','LANE 2','LANE 3','LANE 4']} height={240} />
        </section>

        <section className="card cc-chart">
          <div className="cc-card-head">
            <div>
              <h3>REVENUE TREND</h3>
              <div className="cc-sub-sm">WEEKLY GROWTH</div>
            </div>
            <div className="cc-rev-right">
              <div className="cc-rev-v">₹24.8L</div>
              <div className="cc-rev-d">+12%</div>
            </div>
          </div>
          <LineChart data={[2.8, 3.4, 3.6, 3.2, 3.8, 4.1, 4.4]} labels={['Mon','Tue','Wed','Thu','Fri','Sat','Sun']} height={240} />
        </section>

        <section className="card cc-lane-eq">
          <div className="cc-card-head">
            <h3 style={{display:'inline-flex',alignItems:'center',gap:6}}><Icon name="briefcase" size={14}/> LANE EQUIPMENT STATUS</h3>
            <a className="cc-view-all" href="#" onClick={e=>{e.preventDefault();nav('/equipment');}}>View All →</a>
          </div>
          <table className="cc-lane-table">
            <thead>
              <tr><th>LANE</th><th><IconTh n="camera">ANPR</IconTh></th><th><IconTh n="wifi">RFID</IconTh></th><th><IconTh n="bulb">RADAR</IconTh></th><th><IconTh n="trendingUp">LIDAR</IconTh></th><th><IconTh n="shieldCheck">LC</IconTh></th><th>STATUS</th></tr>
            </thead>
            <tbody>
              {LANE_STATUS.map((r,i) => (
                <tr key={i}>
                  <td className="strong">{r.lane}</td>
                  <td><Mark on={r.anpr}/></td>
                  <td><Mark on={r.rfid}/></td>
                  <td><Mark on={r.radar}/></td>
                  <td><Mark on={r.lidar}/></td>
                  <td><Mark on={r.lc}/></td>
                  <td><span className={`cc-pill ${r.c}`}><i/>{r.st}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}

function Mark({ on }) {
  return <span className={'cc-mark ' + (on ? 'ok' : 'no')}><Icon name={on ? 'check' : 'x'} size={13}/></span>;
}
function IconTh({ n, children }) {
  return <span style={{display:'inline-flex',alignItems:'center',gap:5}}><Icon name={n} size={13}/> {children}</span>;
}
