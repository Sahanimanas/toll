import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar.jsx';
import Topbar from './Topbar.jsx';

export default function Layout() {
  return (
    <div className="app-shell">
      <div className="app">
        <Sidebar />
        <main className="main">
          <Topbar />
          <Outlet />
        </main>
      </div>
      <footer className="powered-footer">
        <span>Powered by</span>
        <img src="/xenochiper-logo.png" alt="Xenochiper" className="powered-logo"/>
      </footer>
    </div>
  );
}
