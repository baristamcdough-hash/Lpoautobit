import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import UploadPage from './pages/Upload';
import Dashboard from './pages/Dashboard';
import RawData from './pages/RawData';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 pt-16 pb-20">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/raw-data" element={<RawData />} />
          </Routes>
          <footer className="text-center py-4 px-2">
            <p className="text-xs text-gray-400">
              Developed by NativeCodes Developers
            </p>
            <p className="text-xs text-gray-400">
              nativecodesdevelopers@gmail.com
            </p>
          </footer>
        </main>
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}
