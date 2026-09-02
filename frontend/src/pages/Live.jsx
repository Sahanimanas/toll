import { useEffect, useRef, useState } from 'react';

import { api } from '../api.js';
import PageHead from '../components/PageHead.jsx';

const pad = n => String(n).padStart(2, '0');
const tsNow = () => { const d = new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

export default function Live() {
  const [cams, setCams] = useState([]);
  const [grid, setGrid] = useState('3');
  const [tick, setTick] = useState(0);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name:'ANPR Camera', lane:'Lane 1', res:'1080P', status:'live', fps:25, type:'ANPR', url:'' });

  async function load() { setCams(await api('/api/cameras')); }
  useEffect(() => { load(); }, []);

  async function addCamera(e) {
    e.preventDefault();
    await api('/api/cameras', { method:'POST', body: JSON.stringify(form) });
    setShowAdd(false);
    setForm({ name:'ANPR Camera', lane:'Lane 1', res:'1080P', status:'live', fps:25, type:'ANPR', url:'' });
    load();
  }
  async function delCamera(id) {
    if (!confirm('Remove this camera?')) return;
    await api('/api/cameras/' + id, { method:'DELETE' });
    load();
  }

  // Real ANPR reads: the backend returns each camera's latest recognition
  // (plate + capture time) and switches `url` to the annotated MJPEG stream
  // once the pipeline starts feeding frames. Refresh both on an interval.
  useEffect(() => {
    const t1 = setInterval(() => setTick(t => t + 1), 1000);
    const t2 = setInterval(() => {
      api('/api/cameras')
        .then(next => setCams(curr => {
          // Only replace when something actually changed, so the <img>/<video>
          // element is not needlessly re-rendered mid-stream.
          const same = curr.length === next.length && curr.every((c, i) =>
            c.id === next[i].id && c.url === next[i].url &&
            c.plate === next[i].plate && c.status === next[i].status);
          return same ? curr : next;
        }))
        .catch(() => {});
    }, 3000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);

  const liveCount = cams.filter(c => c.status === 'live').length;
  const offCount  = cams.filter(c => c.status === 'offline').length;
  const now = tsNow();

  return (
    <>
      <PageHead
        icon="📹"
        title="Live Streaming"
        subtitle="Real-time camera feeds from all lanes · NH-48 Gurugram Plaza"
        right={
          <>
            <span className="live-count"><span className="dot ok" />{liveCount} Live</span>
            <span className="live-count"><span className="dot err" />{offCount} Offline</span>
            <div className="seg-tabs">
              {['2','3','4'].map(g => (
                <button key={g} className={'seg-tab' + (g === grid ? ' active' : '')} onClick={() => setGrid(g)}>{g}×{g}</button>
              ))}
            </div>
            <button className="btn-primary" onClick={()=>setShowAdd(true)}>＋ Add Camera</button>
          </>
        }
      />

      <section className="cam-grid" data-grid={grid}>
        {[...cams].sort((a,b) => {
          const ar = !!a.url, br = !!b.url;        // real streams first
          if (ar !== br) return ar ? -1 : 1;
          return b.id - a.id;                       // newest next
        }).map((c, i) => <Cam key={c.id} c={c} now={now} idx={i} onDelete={delCamera} />)}
      </section>

      {showAdd && (
        <div className="modal" onClick={e=>e.target.classList.contains('modal') && setShowAdd(false)}>
          <div className="modal-card">
            <div className="modal-head">
              <h3>Add Camera</h3>
              <button className="icon-btn" onClick={()=>setShowAdd(false)}>✕</button>
            </div>
            <form className="modal-body" onSubmit={addCamera}>
              <label><span>Camera Name</span>
                <input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="ANPR Camera Front" />
              </label>
              <label><span>Lane / Location</span>
                <input required value={form.lane} onChange={e=>setForm({...form,lane:e.target.value})} placeholder="Lane 1" />
              </label>
              <label><span>Type</span>
                <select value={form.type} onChange={e=>setForm({...form,type:e.target.value})}>
                  <option>ANPR</option><option>Surveillance</option><option>Overhead</option><option>Side</option>
                </select>
              </label>
              <label><span>Resolution</span>
                <select value={form.res} onChange={e=>setForm({...form,res:e.target.value})}>
                  <option>4K UHD</option><option>1080P</option><option>720P</option>
                </select>
              </label>
              <label><span>FPS</span>
                <input type="number" value={form.fps} onChange={e=>setForm({...form,fps:+e.target.value})} />
              </label>
              <label><span>Stream URL</span>
                <input value={form.url} onChange={e=>setForm({...form,url:e.target.value})} placeholder="http://…/stream.m3u8 or .mjpg" />
                <small className="muted small" style={{marginTop:4}}>Leave blank for a mock tile. HLS (.m3u8) plays via &lt;video&gt;, MJPEG plays via &lt;img&gt;.</small>
              </label>
              <label><span>Status</span>
                <select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
                  <option value="live">Live</option>
                  <option value="degraded">Degraded</option>
                  <option value="nosig">No Signal</option>
                  <option value="offline">Offline</option>
                </select>
              </label>
              <div className="modal-foot">
                <button type="button" className="btn-ghost" onClick={()=>setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Add Camera</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

function Cam({ c, now, onDelete }) {
  const ref = useRef(null);
  const tag = c.status === 'live' ? 'LIVE' : c.status === 'offline' ? 'OFFLINE' : c.status === 'degraded' ? 'DEGRADED' : 'LIVE';
  const cls = c.status === 'live' ? 'live' : c.status === 'offline' ? 'offline' : c.status === 'degraded' ? 'degraded live' : 'nosig live';

  const overlay = c.status === 'offline'
    ? <div className="center-msg"><div className="x">⊘</div><div>Camera Offline</div><div className="sub">Signal lost · Reconnecting…</div></div>
    : (c.status === 'nosig' || c.status === 'degraded')
    ? <div className="nosig-text">NO SIGNAL FEED</div>
    : null;

  return (
    <div ref={ref} className={`cam ${cls}`}>
      <CamMedia url={c.url} status={c.status} />
      {c.status !== 'offline' && <div className="scan" />}
      <div className="tl">{tag}</div>
      <div className="fps">{c.fps} fps</div>
      {overlay}
      <div className="cam-tr">
        <button title="Fullscreen" onClick={()=>ref.current?.requestFullscreen?.()}>⛶</button>
        {onDelete && <button title="Remove camera" onClick={()=>onDelete(c.id)}>🗑</button>}
      </div>
      <div className="info">
        <div className="title">
          <span>{c.name}</span>
          {c.annotated && <span className="anpr-badge" title="Live ANPR detection overlay">ANPR</span>}
        </div>
        <div className="lane"><span>{c.lane}</span><span>{c.res}</span></div>
        {c.status !== 'offline' && (
          <div className="read">
            Last Read: {c.plate || '—'} — <span className="t">{c.plateAt || now}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function CamMedia({ url, status }) {
  const v = useRef(null);
  const isRtsp  = url && /^rtsp:\/\//i.test(url);
  const isHls   = url && /\.m3u8(\?|$)/i.test(url);
  const isMjpeg = url && /\.(mjpg|mjpeg)(\?|$)/i.test(url);
  const isFile  = url && /\.(mp4|webm|mov)(\?|$)/i.test(url);
  const isWebcam = url === 'webcam';
  // 'connecting' until first frame arrives, 'playing' once frames flow, 'error' on failure
  const [state, setState] = useState(url ? 'connecting' : 'idle');

  useEffect(() => {
    setState(url ? 'connecting' : 'idle');
    if (isWebcam && v.current) {
      let stream;
      navigator.mediaDevices.getUserMedia({ video:true }).then(s => {
        stream = s; v.current.srcObject = s; setState('playing');
      }).catch(()=> setState('error'));
      return () => stream && stream.getTracks().forEach(t => t.stop());
    }
    if (!isHls || !v.current) return;
    const video = v.current;
    const onPlaying = () => setState('playing');
    const onError   = () => setState('error');
    video.addEventListener('playing', onPlaying);
    video.addEventListener('error',   onError);
    // If HLS never produces a segment, surface an error after 12s
    const watchdog = setTimeout(() => setState(s => s === 'connecting' ? 'error' : s), 12000);

    if (video.canPlayType('application/vnd.apple.mpegurl')) { video.src = url; }
    let hls;
    (async () => {
      try {
        const mod = await import(/* @vite-ignore */ 'hls.js');
        const Hls = mod.default || mod;
        if (Hls.isSupported && Hls.isSupported()) {
          hls = new Hls();
          hls.on(Hls.Events.ERROR, (_, d) => { if (d.fatal) setState('error'); });
          hls.loadSource(url); hls.attachMedia(video);
        } else if (!video.src) { video.src = url; }
      } catch { if (!video.src) video.src = url; }
    })();
    return () => {
      clearTimeout(watchdog);
      video.removeEventListener('playing', onPlaying);
      video.removeEventListener('error',   onError);
      if (hls) hls.destroy();
    };
  }, [url, isHls, isWebcam]);

  if (!url || status === 'offline') return <div className="feed" />;
  if (isRtsp) return (
    <div className="feed cam-rtsp">
      <div className="rtsp-msg">
        <div className="rtsp-title">⚠ RTSP not supported in browser</div>
        <div className="rtsp-sub">Run a media gateway (e.g. MediaMTX) to convert this stream to HLS, then use the .m3u8 URL instead.</div>
        <code>{url}</code>
      </div>
    </div>
  );
  if (isMjpeg) return <img className="feed" src={url} alt="" onLoad={()=>setState('playing')} onError={()=>setState('error')} />;
  if (isFile) return <video className="feed" src={url} autoPlay muted loop playsInline onPlaying={()=>setState('playing')} onError={()=>setState('error')} />;

  const overlay = state === 'connecting'
    ? <div className="feed-overlay"><div className="spinner" /><div>Connecting to stream…</div><div className="sub">{url}</div></div>
    : state === 'error'
    ? <div className="feed-overlay err"><div className="x">⚠</div><div>Stream unavailable</div><div className="sub">Camera not responding. Check RTSP URL / credentials.</div></div>
    : null;

  return (
    <>
      <video className="feed" ref={v} autoPlay muted playsInline />
      {overlay}
    </>
  );
}
