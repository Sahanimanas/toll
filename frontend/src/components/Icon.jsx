const P = {
  home:        'M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1Z',
  users:       'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75',
  video:       'M15 10l5-3v10l-5-3 M3 7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z',
  clipboard:   'M9 4h6a1 1 0 0 1 1 1v2H8V5a1 1 0 0 1 1-1Z M5 6h2v14a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6h2 M9 12h6 M9 16h6',
  shieldCheck: 'M12 3 4 6v6c0 4.5 3 8 8 9 5-1 8-4.5 8-9V6Z M9 12l2 2 4-4',
  ticket:      'M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4Z M13 7v10',
  clock:       'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 7v5l3 2',
  globe:       'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M3 12h18 M12 3c2.5 3 2.5 15 0 18 M12 3c-2.5 3-2.5 15 0 18',
  fileText:    'M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z M14 3v6h6 M8 13h8 M8 17h6',
  settings:    'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z M19.4 13.5a7.5 7.5 0 0 0 0-3l2-1.5-2-3.5-2.4 1a7.5 7.5 0 0 0-2.6-1.5L14 2h-4l-.4 2.5A7.5 7.5 0 0 0 7 6L4.6 5l-2 3.5 2 1.5a7.5 7.5 0 0 0 0 3l-2 1.5 2 3.5 2.4-1A7.5 7.5 0 0 0 9.6 19.5L10 22h4l.4-2.5A7.5 7.5 0 0 0 17 18l2.4 1 2-3.5Z',
  briefcase:   'M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2 M3 13h18',
  menu:        'M4 7h16 M4 12h16 M4 17h16',
  dollar:      'M12 2v20 M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H7',
  truck:       'M3 7a1 1 0 0 1 1-1h10v10H4a1 1 0 0 1-1-1Z M14 10h4l3 3v4h-7 M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M17 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4',
  card:        'M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M3 10h18',
  ban:         'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M5.6 5.6l12.8 12.8',
  columns:     'M4 5h16v14H4Z M10 5v14 M16 5v14',
  camera:      'M3 9a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7',
  wifi:        'M2 8.5a15 15 0 0 1 20 0 M5 12a10 10 0 0 1 14 0 M8.5 15.5a5 5 0 0 1 7 0 M12 19h0',
  bulb:        'M12 3a6 6 0 0 0-4 10.5V16h8v-2.5A6 6 0 0 0 12 3Z M9 20h6 M10 17h4',
  grid:        'M3 3h8v8H3Z M13 3h8v8h-8Z M3 13h8v8H3Z M13 13h8v8h-8Z',
  idCard:      'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z M8 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M5 17c.5-2 2-3 3-3h0c1 0 2.5 1 3 3 M14 10h5 M14 14h3',
  barChart:    'M4 20V10 M10 20V4 M16 20v-7 M22 20H2',
  trendingUp:  'M3 17 9 11l4 4 8-8 M14 7h7v7',
  bell:        'M6 8a6 6 0 1 1 12 0c0 6 3 7 3 7H3s3-1 3-7 M10 21a2 2 0 0 0 4 0',
  refresh:     'M3 12a9 9 0 0 1 15-6.7L21 8 M21 4v4h-4 M21 12a9 9 0 0 1-15 6.7L3 16 M3 20v-4h4',
  maximize:    'M4 9V4h5 M20 9V4h-5 M4 15v5h5 M20 15v5h-5',
  exit:        'M14 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2v-2 M10 12h11 M18 9l3 3-3 3',
  sun:         'M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z M12 2v2 M12 20v2 M4.93 4.93l1.41 1.41 M17.66 17.66l1.41 1.41 M2 12h2 M20 12h2 M4.93 19.07l1.41-1.41 M17.66 6.34l1.41-1.41',
  check:       'M5 12l5 5 9-11',
  x:           'M6 6l12 12 M6 18 18 6',
  pie:         'M21 12a9 9 0 1 1-9-9v9Z M12 3a9 9 0 0 1 9 9h-9Z',
  download:    'M12 4v12 M7 11l5 5 5-5 M5 20h14',
  save:        'M5 4h11l3 3v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z M8 4v5h7V4 M8 14h8',
};

export default function Icon({ name, size = 18, stroke = 'currentColor', strokeWidth = 1.8, className, style }) {
  const d = P[name];
  if (!d) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
         className={className} style={style} aria-hidden="true">
      {d.split(' M').map((seg, i) => <path key={i} d={(i === 0 ? '' : 'M') + seg} />)}
    </svg>
  );
}
