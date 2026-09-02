export default function PageHead({ icon, title, subtitle, right }) {
  return (
    <section className="page-head">
      <div className="page-head-left">
        {icon && <div className="page-icon">{icon}</div>}
        <div>
          <h1>{title}</h1>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      </div>
      {right && <div className="page-head-right">{right}</div>}
    </section>
  );
}
