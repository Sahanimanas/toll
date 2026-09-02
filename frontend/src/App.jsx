import { Routes, Route, Navigate } from 'react-router-dom';
import { getToken } from './api.js';
import Login from './pages/Login.jsx';
import Layout from './components/Layout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Admin from './pages/Admin.jsx';
import Live from './pages/Live.jsx';
import Transactions from './pages/Transactions.jsx';
import Audit from './pages/Audit.jsx';
import ETicket from './pages/ETicket.jsx';
import Equipment from './pages/Equipment.jsx';
import Nms from './pages/Nms.jsx';
import Report from './pages/Report.jsx';
import Configuration from './pages/Configuration.jsx';
import ControlCenter from './pages/ControlCenter.jsx';
import ComingSoon from './pages/ComingSoon.jsx';

function Protected({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/control" element={<Protected><ControlCenter /></Protected>} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/live" element={<Live />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/eticket" element={<ETicket />} />
        <Route path="/equipment" element={<Equipment />} />
        <Route path="/nms" element={<Nms />} />
        <Route path="/report" element={<Report />} />
        <Route path="/config" element={<Configuration />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
