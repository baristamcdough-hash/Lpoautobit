import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import FooterCredit from './components/FooterCredit';
import UploadPage from './pages/Upload';
import Dashboard from './pages/Dashboard';
import RawData from './pages/RawData';
import Login from './pages/Login';

export default function App() {
  const [authenticated, setAuthenticated] = useState(
    () => sessionStorage.getItem('authenticated') === 'true'
  );

  if (!authenticated) {
    return <Login onLogin={() => setAuthenticated(true)} />;
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 pt-16 pb-28 bg-slate-50">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/raw-data" element={<RawData />} />
          </Routes>
        </main>
        <FooterCredit />
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}
