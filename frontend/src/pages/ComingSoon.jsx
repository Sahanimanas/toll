import PageHead from '../components/PageHead.jsx';

export default function ComingSoon({ name, icon }) {
  return (
    <>
      <PageHead icon={icon} title={name} subtitle="This section is part of the MLFF Tolling System." />
      <section className="card">
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
          <div style={{ fontSize: 48, marginBottom: 10 }}>{icon}</div>
          <h3 style={{ color: 'var(--ink)', margin: '0 0 6px' }}>Coming Soon</h3>
          <p style={{ margin: 0 }}>This module is under construction.</p>
        </div>
      </section>
    </>
  );
}
