import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';
import { BarChart3D, GroupBars, LineChart, Donut } from '../components/charts.jsx';

const CAM_FILTERS = [
  { key: 'all',          label: 'All' },
  { key: 'connected',    label: 'Connected' },
  { key: 'disconnected', label: 'Not Connected' },
  { key: 'no-signal',    label: 'No Signal' }
];

const CAM_STATUS = {
  live:    { key: 'connected',    cls: 'ok',   label: 'Connected' },
  nosig:   { key: 'no-signal',    cls: 'warn', label: 'No Signal' },
  offline: { key: 'disconnected', cls: 'err',  label: 'Not Connected' }
};
const camKey = c => (CAM_STATUS[c.status] || CAM_STATUS.offline).key;

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [live, setLive] = useState(null);
  const [cams, setCams] = useState([]);
  const [panels, setPanels] = useState(null);
  const [tab, setTab] = useState('Hourly');
  const [camFilter, setCamFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  async function load() { setD(await api('/api/dashboard')); }
  async function loadLive() { try { setLive(await api('/api/dashboard/live')); } catch {} }
  async function loadCams() { try { setCams(await api('/api/cameras')); } catch {} }
  async function loadPanels() { try { setPanels(await api('/api/dashboard/panels')); } catch {} }
  useEffect(() => { load(); loadLive(); loadCams(); loadPanels(); }, []);
  useEffect(() => {
    const id = setInterval(() => { loadLive(); loadCams(); }, 3000);
    return () => clearInterval(id);
  }, []);

  if (!d) return <div className="muted" style={{ padding: 40 }}>Loading…</div>;

  const refresh = async () => {
    setRefreshing(true);
    await Promise.all([load(), loadLive(), loadCams(), loadPanels()]);
    setRefreshing(false);
  };

  const k = live?.kpis;
  const fmtDelta = n => (n > 0 ? '+' : '') + n + '%';

  const tick = v => v ? <span className="check ok">✓</span> : <span className="check no">✕</span>;

  return (
    <>
      <PageHead
        icon="⌂"
        title="Dashboard"
        subtitle="Real-time overview of FLOW tolling operations · NH-48 Gurugram Plaza"
        right={
          <>
            <span className="status-pill ok"><span className="live-dot"/> LIVE</span>
            <span className="status-pill ok">● System Operational</span>
            <button className="btn-ghost" onClick={refresh}>{refreshing ? '⟳ Refreshing…' : '⟳ Refresh'}</button>
          </>
        }
      />

      <section className="kpis">
        <KPI ic="b" icon="₹"  value={k?.revenue.value    ?? '₹24.8L'} delta={k ? fmtDelta(k.revenue.delta)    : '+12.4%'} up={!k || k.revenue.delta    >= 0} label="Total Revenue" />
        <KPI ic="g" icon="🚗" value={k?.vehicles.value   ?? '12,840'} delta={k ? fmtDelta(k.vehicles.delta)   : '+8.2%'}  up={!k || k.vehicles.delta   >= 0} label="Total Vehicles" />
        <KPI ic="p" icon="💳" value={k?.txn.value        ?? '12,284'} delta={k ? fmtDelta(k.txn.delta)        : '+6.1%'}  up={!k || k.txn.delta        >= 0} label="Transactions" />
        <KPI ic="r" icon="⊘"  value={k?.violations.value ?? d.kpis.violations} delta={k ? fmtDelta(k.violations.delta) : '-3.2%'} up={k ? k.violations.delta >= 0 : false} label="Violations" />
        <KPI ic="t" icon="≣"  value={k?.lanes.value      ?? '4 / 4'}  delta="100%" up label="Active Lanes" />
        <KPI ic="o" icon="▭"  value={k?.failed.value     ?? d.kpis.failed}     delta={k ? fmtDelta(k.failed.delta)     : '-18.4%'} up={k ? k.failed.delta >= 0 : false} label="Failed Txns" />
      </section>

      <section className="row row-2-1">
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">📊</div>
              <div><h3>Transaction Volume</h3><p className="muted small">Traffic &amp; Revenue Breakdown</p></div>
            </div>
            <div className="tabs">
              {(panels ? Object.keys(panels.volume) : ['Hourly']).map(k => (
                <button key={k} className={'tab' + (k === tab ? ' active' : '')} onClick={() => setTab(k)}>{k}</button>
              ))}
            </div>
          </div>
          <BarChart3D data={panels?.volume[tab]?.data ?? []} labels={panels?.volume[tab]?.labels ?? []} />
          <div className="chart-foot">
            <div><span className="legend-sq blue" /> Transactions <span className="up small">&nbsp;+{panels?.volume[tab]?.delta ?? 0}%</span> <span className="muted small">Peak: {panels?.volume[tab]?.peak ?? '—'}</span></div>
            <div className="muted small">Total: <b style={{ color: 'var(--ink)' }}>{panels?.volume[tab]?.total?.toLocaleString('en-IN') ?? '—'}</b></div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">◔</div>
              <div><h3>Vehicle Classification</h3><p className="muted small">Distribution · Today</p></div>
            </div>
          </div>
          <div className="donut-wrap">
            <Donut segments={d.classes} />
            <div className="donut-center">
              <div className="donut-val">12,840</div>
              <div className="donut-lbl">TOTAL</div>
            </div>
          </div>
          <ul className="donut-legend">
            {d.classes.map(s => (
              <li key={s.name}>
                <div className="lk"><span className="d" style={{ background: s.color }} />{s.name}</div>
                <div className="bar"><span style={{ width: `${s.value*2}%`, background: s.color }} /></div>
                <div className="pct">{s.value}%</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div className="card-title">
            <div className="card-ic">▦</div>
            <div><h3>Real-Time Equipment Status</h3></div>
            <span className="status-pill ok small">● Live</span>
          </div>
        </div>
        <div className="equip-grid">
          {d.equipment.map(e => {
            const pct = (e.active / e.total) * 100;
            return (
              <div className="equip" key={e.name}>
                <div className="equip-head">
                  <div className="equip-ic">{e.ic}</div>
                  <div className="equip-name">{e.name}</div>
                </div>
                <div className="equip-stat">
                  <div className="equip-total">{e.total}</div>
                  <div className="muted">Total</div>
                </div>
                <div className="equip-rows">
                  <div><span><span className="dot ok" />Active:</span><b>{e.active}</b></div>
                  <div><span><span className="dot err" />Inactive:</span><b>{e.inactive}</b></div>
                </div>
                <div className="equip-bar"><span style={{ width: `${pct}%` }} /></div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div className="card-title">
            <div className="card-ic">📷</div>
            <div><h3>Camera Status</h3><p className="muted small">Connectivity overview · All ANPR &amp; surveillance cameras</p></div>
          </div>
          <div className="tabs">
            {CAM_FILTERS.map(f => {
              const count = f.key === 'all' ? cams.length : cams.filter(c => camKey(c) === f.key).length;
              return (
                <button key={f.key} className={'tab' + (f.key === camFilter ? ' active' : '')} onClick={() => setCamFilter(f.key)}>
                  {f.label} ({count})
                </button>
              );
            })}
          </div>
        </div>
        <div className="cam-summary">
          <div className="cam-stat ok">
            <div className="cam-stat-ic">●</div>
            <div><div className="cam-stat-val">{cams.filter(c => camKey(c) === 'connected').length}</div><div className="muted small">Connected</div></div>
          </div>
          <div className="cam-stat err">
            <div className="cam-stat-ic">●</div>
            <div><div className="cam-stat-val">{cams.filter(c => camKey(c) === 'disconnected').length}</div><div className="muted small">Not Connected</div></div>
          </div>
          <div className="cam-stat warn">
            <div className="cam-stat-ic">●</div>
            <div><div className="cam-stat-val">{cams.filter(c => camKey(c) === 'no-signal').length}</div><div className="muted small">No Signal</div></div>
          </div>
          <div className="cam-stat">
            <div className="cam-stat-ic">📷</div>
            <div><div className="cam-stat-val">{cams.length}</div><div className="muted small">Total</div></div>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr><th>Camera ID</th><th>Name</th><th>Lane</th><th>Resolution</th><th>FPS</th><th>Uptime 24h</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {cams.filter(c => camFilter === 'all' || camKey(c) === camFilter).map(c => {
              const meta = CAM_STATUS[c.status] || CAM_STATUS.offline;
              return (
                <tr key={c.id}>
                  <td>CAM-{String(c.id).padStart(2, '0')}</td>
                  <td>{c.name}</td>
                  <td className="muted">{c.lane}</td>
                  <td className="muted">{c.res}</td>
                  <td className="muted">{c.fps || '—'}</td>
                  <td>
                    <div className="uptime-cell">
                      <div className="uptime-bar">
                        {(c.uptime?.segments ?? []).map((s, i) => (
                          <span key={i} className={`uptime-seg ${CAM_STATUS[s.status]?.cls || 'err'}`} style={{ flex: s.ms }} />
                        ))}
                      </div>
                      <span className="muted small">{c.uptime?.pct ?? '—'}%</span>
                    </div>
                  </td>
                  <td><span className={`tag ${meta.cls}`}>● {meta.label}</span></td>
                  <td><Link className="link" to="/live">View →</Link></td>
                </tr>
              );
            })}
            {cams.length === 0 && (
              <tr><td colSpan="8" className="muted" style={{ textAlign: 'center', padding: 20 }}>Loading cameras…</td></tr>
            )}
            {cams.length > 0 && cams.filter(c => camFilter === 'all' || camKey(c) === camFilter).length === 0 && (
              <tr><td colSpan="8" className="muted" style={{ textAlign: 'center', padding: 20 }}>No cameras in this category</td></tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="row row-1-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">🎫</div>
              <div><h3>E-Ticket</h3><p className="muted small">Today's Summary</p></div>
            </div>
          </div>
          <div className="eticket-list">
            {(panels?.eticket ?? []).map(r => <ETRow key={r.title} {...r} />)}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">📊</div>
              <div><h3>RFID vs ANPR</h3><p className="muted small">Accuracy Comparison · Today</p></div>
            </div>
            <div className="legend-inline">
              <span><span className="legend-sq blue" /> RFID</span>
              <span><span className="legend-sq cyan" /> ANPR</span>
            </div>
          </div>
          <GroupBars a={panels?.accuracy.rfid ?? []} b={panels?.accuracy.anpr ?? []} labels={panels?.accuracy.labels ?? []} />
          <div className="acc-row">
            <div className="acc blue-bg">
              <div className="acc-ic">📡</div>
              <div><div className="muted small">Avg RFID Accuracy</div><div className="acc-val" style={{ color: 'var(--blue)' }}>{panels?.accuracy.avgRfid ?? '—'}%</div></div>
            </div>
            <div className="acc cyan-bg">
              <div className="acc-ic">📷</div>
              <div><div className="muted small">Avg ANPR Accuracy</div><div className="acc-val" style={{ color: '#0aa3c2' }}>{panels?.accuracy.avgAnpr ?? '—'}%</div></div>
            </div>
          </div>
        </div>
      </section>

      <section className="row row-2-1">
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">📈</div>
              <div><h3>Revenue Trend</h3><p className="muted small">Last 7 days</p></div>
            </div>
            <div className="card-amt" style={{ color: 'var(--blue)' }}>{panels?.revenue.total ?? '—'}</div>
          </div>
          <LineChart data={d.revenueTrend} labels={panels?.revenue.labels ?? ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']} />
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">⇅</div>
              <div><h3>Lane Status</h3></div>
            </div>
          </div>
          <ul className="lane-status">
            {d.lanes.map(l => (
              <li key={l.name} className={l.state === 'err' ? 'offline' : ''}>
                <div className="ln-left">
                  <span className={`dot ${l.state}`} />
                  <div>
                    <div className="ln-title">{l.name}</div>
                    <div className="ln-sub">{l.vh} veh/hr</div>
                  </div>
                </div>
                <div>
                  <div className="ln-amt">{l.rev}</div>
                  <div className="ln-tag">{l.status}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="row row-2-1">
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">▥</div>
              <div><h3>Direction &amp; Lane Equipment Status</h3></div>
            </div>
            <Link className="link" to="/equipment">View All →</Link>
          </div>
          <table className="table">
            <thead>
              <tr><th>Direction</th><th>Lane</th><th>📷 ANPR</th><th>📡 RFID</th><th>▣ RADAR</th><th>⚡ LiDAR</th><th>🔒 LC</th><th>Status</th></tr>
            </thead>
            <tbody>
              {d.laneEquip.map(r => (
                <tr key={r.lane}>
                  <td><span className={`tag ${r.dir.toLowerCase()}`}>↪ {r.dir}</span></td>
                  <td>{r.lane}</td>
                  <td>{tick(r.anpr)}</td><td>{tick(r.rfid)}</td>
                  <td>{tick(r.radar)}</td><td>{tick(r.lidar)}</td><td>{tick(r.lc)}</td>
                  <td><span className={`tag ${r.status[0]}`}>● {r.status[1]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-ic">🔔</div>
              <div><h3>System Alerts</h3></div>
            </div>
            <span className="status-pill err small">● {(panels?.alerts ?? []).filter(a => a.type !== 'ok').length} Active</span>
          </div>
          <ul className="alerts">
            {(panels?.alerts ?? []).map((a, i) => <Alert key={i} {...a} />)}
          </ul>
        </div>
      </section>
    </>
  );
}

function KPI({ ic, icon, value, delta, up, label }) {
  return (
    <div className="kpi">
      <div className="kpi-top">
        <div className={`kpi-icon ${ic}`}><span>{icon}</span></div>
        <span className={`delta ${up ? 'up' : 'down'}`}>{delta}</span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}

function ETRow({ type, ic, title, sub, num, pct, color }) {
  return (
    <div className={`eticket-row ${type}`}>
      <div className="et-ic">{ic}</div>
      <div className="et-body">
        <div className="et-title">{title}</div>
        <div className="muted small">{sub}</div>
      </div>
      <div className="et-num">
        <div className="big" style={{ color }}>{num}</div>
        <div className="muted small">{pct}</div>
      </div>
    </div>
  );
}

function Alert({ ic, type, title, sub, time }) {
  return (
    <li>
      <div className={`al-ic ${type}`}>{ic}</div>
      <div className="al-body">
        <div className="al-title">{title}</div>
        <div className="muted small">{sub}</div>
      </div>
      <div className="muted small">{time}</div>
    </li>
  );
}
