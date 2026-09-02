import { NavLink } from 'react-router-dom';
import Icon from './Icon.jsx';

const NAV = {
  MAIN: [
    { to: '/dashboard',    icon: 'home',        label: 'Dashboard' },
    { to: '/admin',        icon: 'users',       label: 'Admin' },
    { to: '/live',         icon: 'video',       label: 'Live Streaming', pill: 4 },
    { to: '/transactions', icon: 'clipboard',   label: 'Toll Transactions' },
    { to: '/audit',        icon: 'shieldCheck', label: 'Audit' },
    { to: '/eticket',      icon: 'ticket',      label: 'E-Ticket', pill: 7 },
    { to: '/equipment',    icon: 'clock',       label: 'Equipment History', pill: 2 }
  ],
  SYSTEM: [
    { to: '/nms',    icon: 'globe',    label: 'NMS' },
    { to: '/report', icon: 'fileText', label: 'Report' },
    { to: '/config', icon: 'settings', label: 'Configuration' }
  ],
  'WORK STATION': [
    { to: '/control', icon: 'briefcase', label: 'Control Center' }
  ]
};

const SECTION_GLYPH = { MAIN: 'menu', SYSTEM: 'settings', 'WORK STATION': 'briefcase' };

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo brand-logo">
        <div className="brand-mark">MLFF</div>
        <div className="brand-name">Tolling System</div>
      </div>

      {Object.entries(NAV).map(([section, items]) => (
        <div className="nav-group" key={section}>
          <div className="nav-label"><Icon name={SECTION_GLYPH[section]} size={13} /> {section}</div>
          {items.map(it => (
            <NavLink key={it.to} to={it.to}
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <span className="ic"><Icon name={it.icon} size={18} /></span> {it.label}
              {it.pill != null && <span className="pill">{it.pill}</span>}
            </NavLink>
          ))}
        </div>
      ))}

    </aside>
  );
}
