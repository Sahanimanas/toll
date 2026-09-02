import { useEffect, useState } from 'react';
import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

function latencyClass(ms) {
  if (ms == null) return 'err';
  if (ms <= 10)   return 'ok';
  return 'warn';
}

export default function Nms() {
  const [d, setD] = useState(null);
  const [pinging, setPinging] = useState(false);

  async function load() { setD(await api('/api/nms')); }
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  async function pingAll() {
    setPinging(true);
    await load();
    setPinging(false);
  }

  if (!d) return <div className="muted" style={{padding:40}}>Loading…</div>;

  return (
    <>
      <PageHead icon="🌐" title="Network Management System"
        subtitle="Real-time equipment health monitoring · All lanes"
        right={
          <>
            <button className="btn-ghost" onClick={pingAll}>{pinging ? '⟳ Pinging…' : '⟳ Ping All'}</button>
            <span className="status-pill ok">{d.totals.online} Online</span>
            <span className="status-pill warn-pill">{d.totals.degraded} Degraded</span>
            <span className="status-pill err">{d.totals.offline} Offline</span>
          </>
        }
      />

      <section className="card health-card">
        <div className="health-head">
          <h3>Overall System Health</h3>
          <div className="health-pct">{d.health}%</div>
        </div>
        <div className="health-bar"><span style={{width:`${d.health}%`}} /></div>
        <div className="health-foot">
          <span className="muted small">Last scan: {d.lastScan}</span>
          <span className="muted small">{d.totals.total} total devices</span>
        </div>
      </section>

      <section className="nms-grid">
        {d.lanes.map(l => (
          <div key={l.id} className={`lane-card ${l.state}`}>
            <div className="lane-head">
              <div className="lane-info">
                <div className="lane-ico">⇄</div>
                <div>
                  <h4>{l.name}</h4>
                  <div className="sub">{l.dir} · {l.id}</div>
                </div>
              </div>
              <div className="status-x">{l.online}/{l.total} Online</div>
            </div>
            <ul className="dev-list">
              {l.devices.map(dev => {
                const pillLabel = dev.status === 'ok' ? 'Online' : dev.status === 'warn' ? 'Degraded' : 'Offline';
                return (
                  <li key={dev.name} className="dev-row">
                    <span className={`dev-dot ${dev.status}`} />
                    <div>
                      <div className="dev-name">{dev.name}</div>
                      <div className="dev-ip">{dev.ip}</div>
                    </div>
                    <div className="dev-meta">
                      {dev.latency != null
                        ? <span className={`lat ${latencyClass(dev.latency)}`}>{dev.latency}ms</span>
                        : <span className="lat err">Timeout</span>}
                      <span className="ts">{dev.ts}</span>
                    </div>
                    <span className={`dev-pill ${dev.status}`}>{pillLabel}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </section>
    </>
  );
}
