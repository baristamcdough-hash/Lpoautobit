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
        <main className="flex-1 pt-16 pb-24">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/raw-data" element={<RawData />} />
          </Routes>
          <footer className="text-center py-6 px-2 mb-4">
            <p className="text-xs text-gray-400">
              nativecodesdevelopers@gmail.com
            </p>
            <p className="text-xs text-gray-400 mt-1">
              made wt ♥️ by:{' '}
              <a
                href="https://wa.me/254717702563"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-green-500 transition-colors"
              >
                P.oR.iot🍄
              </a>
            </p>
          </footer>
        </main>
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}
