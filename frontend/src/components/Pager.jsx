export default function Pager({ page, pages, total, onChange, showSize, size, onSize }) {
  return (
    <div className="pager pager-size">
      <span className="muted">Showing {total} records</span>
      {showSize && (
        <div className="size-group">
          <span className="muted">Show:</span>
          {[7, 14, 21].map(s => (
            <button key={s}
              className={'size-btn' + (s === size ? ' active' : '')}
              onClick={() => onSize(s)}>{s}</button>
          ))}
        </div>
      )}
      <div className="page-nums">
        <button className="pg-btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹</button>
        {Array.from({ length: pages }, (_, i) => i + 1).map(n => (
          <button key={n}
            className={'pg-btn' + (n === page ? ' active' : '')}
            onClick={() => onChange(n)}>{n}</button>
        ))}
        <button className="pg-btn" disabled={page >= pages} onClick={() => onChange(page + 1)}>›</button>
      </div>
    </div>
  );
}
