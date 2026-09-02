import { useEffect, useRef } from 'react';

function setup(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width * dpr; canvas.height = r.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, w: r.width, h: r.height };
}

function useResizeRedraw(draw) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    draw(ref.current);
    const onR = () => draw(ref.current);
    window.addEventListener('resize', onR);
    return () => window.removeEventListener('resize', onR);
  });
  return ref;
}

export function BarChart3D({ data, labels, height = 280 }) {
  const ref = useResizeRedraw((c) => {
    const { ctx, w, h } = setup(c);
    ctx.clearRect(0, 0, w, h);
    const padL=30, padR=20, padT=20, padB=30;
    const cw = w-padL-padR, ch = h-padT-padB;
    const max = (Math.max(...data) || 1) * 1.15;
    ctx.strokeStyle = '#eaecf0'; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
    for (let i=0;i<=4;i++){ const y=padT+ch*i/4; ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+cw,y); ctx.stroke(); }
    ctx.setLineDash([]);
    const bw = cw / data.length;
    data.forEach((v,i)=>{
      const x = padL + i*bw + bw*0.18;
      const bh = v > 0 ? (v/max)*ch : 0;
      if (bh <= 0) return;
      const y = padT + ch - bh;
      const width = bw*0.55;
      ctx.fillStyle = '#000000';
      ctx.beginPath(); ctx.moveTo(x+width,y); ctx.lineTo(x+width+8,y-6); ctx.lineTo(x+width+8,y+bh-6); ctx.lineTo(x+width,y+bh); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#2a2a2a';
      ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+8,y-6); ctx.lineTo(x+width+8,y-6); ctx.lineTo(x+width,y); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#0e0e0e'; ctx.fillRect(x,y,width,bh);
    });
    ctx.fillStyle = '#8b94a7'; ctx.font = '11px -apple-system,Segoe UI,sans-serif';
    labels.forEach((lb,i)=>{ const x = padL + i*bw + bw*0.4; ctx.fillText(lb, x-10, h-10); });
  });
  return <canvas ref={ref} style={{ height, width: '100%' }} />;
}

export function GroupBars({ a, b, labels, height = 230 }) {
  const ref = useResizeRedraw((c) => {
    const { ctx, w, h } = setup(c);
    ctx.clearRect(0,0,w,h);
    const padL=30,padR=20,padT=20,padB=30, cw=w-padL-padR, ch=h-padT-padB;
    const max = Math.max(...a,...b)*1.15;
    ctx.strokeStyle='#eaecf0'; ctx.lineWidth=1; ctx.setLineDash([4,4]);
    for (let i=0;i<=4;i++){ const y=padT+ch*i/4; ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+cw,y); ctx.stroke(); }
    ctx.setLineDash([]);
    const groupW = cw/a.length, bw = groupW*0.3;
    function bar(x,y,bh,front,top,side){
      ctx.fillStyle=side; ctx.beginPath(); ctx.moveTo(x+bw,y); ctx.lineTo(x+bw+6,y-4); ctx.lineTo(x+bw+6,y+bh-4); ctx.lineTo(x+bw,y+bh); ctx.closePath(); ctx.fill();
      ctx.fillStyle=top; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+6,y-4); ctx.lineTo(x+bw+6,y-4); ctx.lineTo(x+bw,y); ctx.closePath(); ctx.fill();
      ctx.fillStyle=front; ctx.fillRect(x,y,bw,bh);
    }
    a.forEach((v,i)=>{ const bh=(v/max)*ch, y=padT+ch-bh, x=padL+i*groupW+groupW*0.15; bar(x,y,bh,'#0e0e0e','#2a2a2a','#000000'); });
    b.forEach((v,i)=>{ const bh=(v/max)*ch, y=padT+ch-bh, x=padL+i*groupW+groupW*0.5;  bar(x,y,bh,'#a87b2f','#c89a4a','#8a6526'); });
    ctx.fillStyle='#8b94a7'; ctx.font='11px -apple-system,Segoe UI,sans-serif';
    labels.forEach((lb,i)=>{ const x=padL+i*groupW+groupW*0.5 - ctx.measureText(lb).width/2; ctx.fillText(lb,x,h-10); });
  });
  return <canvas ref={ref} style={{ height, width: '100%' }} />;
}

export function LineChart({ data, labels, height = 230 }) {
  const ref = useResizeRedraw((c) => {
    const { ctx, w, h } = setup(c);
    ctx.clearRect(0,0,w,h);
    const padL=30,padR=20,padT=20,padB=30, cw=w-padL-padR, ch=h-padT-padB;
    const max=Math.max(...data)*1.15, min=Math.min(...data)*0.85;
    ctx.strokeStyle='#eaecf0'; ctx.lineWidth=1; ctx.setLineDash([4,4]);
    for (let i=0;i<=4;i++){ const y=padT+ch*i/4; ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+cw,y); ctx.stroke(); }
    ctx.setLineDash([]);
    const sx = cw/(data.length-1);
    const grad = ctx.createLinearGradient(0,padT,0,padT+ch);
    grad.addColorStop(0,'rgba(14,14,14,.18)'); grad.addColorStop(1,'rgba(14,14,14,0)');
    ctx.beginPath();
    data.forEach((v,i)=>{ const x=padL+i*sx, y=padT+ch-((v-min)/(max-min))*ch; i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); });
    ctx.lineTo(padL+cw,padT+ch); ctx.lineTo(padL,padT+ch); ctx.closePath();
    ctx.fillStyle=grad; ctx.fill();
    ctx.beginPath();
    data.forEach((v,i)=>{ const x=padL+i*sx, y=padT+ch-((v-min)/(max-min))*ch; i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); });
    ctx.strokeStyle='#0e0e0e'; ctx.lineWidth=2.5; ctx.stroke();
    data.forEach((v,i)=>{
      const x=padL+i*sx, y=padT+ch-((v-min)/(max-min))*ch;
      ctx.fillStyle='#0e0e0e'; ctx.beginPath(); ctx.arc(x,y,4,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#fff';    ctx.beginPath(); ctx.arc(x,y,1.8,0,Math.PI*2); ctx.fill();
    });
    ctx.fillStyle='#8b94a7'; ctx.font='11px -apple-system,Segoe UI,sans-serif';
    labels.forEach((lb,i)=>{ const x=padL+i*sx - ctx.measureText(lb).width/2; ctx.fillText(lb,x,h-10); });
  });
  return <canvas ref={ref} style={{ height, width: '100%' }} />;
}

export function Donut({ segments, size = 240 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const c = ref.current;
    const dpr = window.devicePixelRatio || 1;
    const W = size, H = Math.round(size * 0.78);
    c.width = W * dpr; c.height = H * dpr;
    const ctx = c.getContext('2d'); ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    const cx = W / 2, cy = H * 0.46;
    const r  = Math.min(W, H) / 2 - 10;
    const ir = r * 0.55;
    const tilt = 0.45;            // vertical squash (3D feel)
    const depth = 14;             // extrude height
    const total = segments.reduce((a, b) => a + b.value, 0);

    const shade = (hex, amt) => {
      const n = parseInt(hex.slice(1), 16);
      let R = (n >> 16) + amt, G = ((n >> 8) & 0xff) + amt, B = (n & 0xff) + amt;
      R = Math.max(0, Math.min(255, R)); G = Math.max(0, Math.min(255, G)); B = Math.max(0, Math.min(255, B));
      return `rgb(${R},${G},${B})`;
    };

    function ellipseSlice(cx, cy, rx, ry, a0, a1, dir = false) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(1, ry / rx);
      ctx.arc(0, 0, rx, a0, a1, dir);
      ctx.restore();
    }

    // 1) Outer rim side wall (extruded depth) — drawn back-to-front
    const sides = [];
    let a = -Math.PI / 2;
    segments.forEach(s => {
      const ang = (s.value / total) * Math.PI * 2;
      sides.push({ a0: a, a1: a + ang, color: s.color });
      a += ang;
    });
    // Sort by middle-angle so back faces render first
    sides.slice().sort((p, q) => Math.sin((p.a0 + p.a1) / 2) - Math.sin((q.a0 + q.a1) / 2))
      .forEach(s => {
        ctx.beginPath();
        ellipseSlice(cx, cy, r, r * tilt, s.a0, s.a1);
        ellipseSlice(cx, cy + depth, r, r * tilt, s.a1, s.a0, true);
        ctx.closePath();
        ctx.fillStyle = shade(s.color, -40);
        ctx.fill();
      });

    // 2) Inner rim wall (extruded depth) on the inside of the donut hole
    sides.slice().sort((p, q) => Math.sin((p.a0 + p.a1) / 2) - Math.sin((q.a0 + q.a1) / 2))
      .forEach(s => {
        ctx.beginPath();
        ellipseSlice(cx, cy, ir, ir * tilt, s.a0, s.a1);
        ellipseSlice(cx, cy + depth, ir, ir * tilt, s.a1, s.a0, true);
        ctx.closePath();
        ctx.fillStyle = shade(s.color, -55);
        ctx.fill();
      });

    // 3) Top face (ring) with segments
    sides.forEach(s => {
      ctx.beginPath();
      ellipseSlice(cx, cy, r, r * tilt, s.a0, s.a1);
      ellipseSlice(cx, cy, ir, ir * tilt, s.a1, s.a0, true);
      ctx.closePath();
      ctx.fillStyle = s.color;
      ctx.fill();
      // subtle outline
      ctx.strokeStyle = 'rgba(255,255,255,.55)';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // 4) Soft inner highlight
    const ig = ctx.createRadialGradient(cx, cy - r * tilt * 0.3, ir * 0.1, cx, cy, ir);
    ig.addColorStop(0, 'rgba(255,255,255,.55)');
    ig.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = ig;
    ctx.beginPath();
    ellipseSlice(cx, cy, ir - 1, (ir - 1) * tilt, 0, Math.PI * 2);
    ctx.fill();
  }, [segments, size]);
  const h = Math.round(size * 0.78);
  return <canvas ref={ref} width={size} height={h} style={{ width: size, height: h }} />;
}
