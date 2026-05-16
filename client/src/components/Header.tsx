import { useLocation } from 'react-router-dom';

function getSubtitle(pathname: string): string {
  switch (pathname) {
    case '/upload':
      return 'Upload LPOs';
    case '/raw-data':
      return 'Raw Data';
    case '/dashboard':
    default:
      return 'Marikiti Pick List';
  }
}

export default function Header() {
  const location = useLocation();
  const subtitle = getSubtitle(location.pathname);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900 text-white shadow-md">
      <div className="px-4 py-3">
        <h1 className="text-lg font-bold tracking-tight">LPO Consolidator</h1>
        <p className="text-sm text-slate-300">{subtitle}</p>
      </div>
    </header>
  );
}
