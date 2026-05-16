import { NavLink } from 'react-router-dom';
import { Upload, ClipboardList, Table } from 'lucide-react';

const navItems = [
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/dashboard', icon: ClipboardList, label: 'Dashboard' },
  { to: '/raw-data', icon: Table, label: 'Raw Data' },
];

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t-2 border-slate-200 shadow-[0_-1px_3px_rgba(0,0,0,0.05)] pb-[env(safe-area-inset-bottom)]">
      <div className="flex justify-around items-center h-16">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-full h-full text-xs ${
                isActive ? 'text-teal-600 font-semibold' : 'text-slate-400'
              }`
            }
          >
            <Icon className="w-6 h-6 mb-1" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
