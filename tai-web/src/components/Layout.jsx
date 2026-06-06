import { NavLink } from 'react-router-dom';
import { Package, BookOpen, FileText, MessageSquare, LayoutDashboard } from 'lucide-react';

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/products', icon: Package, label: 'Ürünler' },
  { to: '/knowledge', icon: BookOpen, label: 'Bilgi Kayıtları' },
  { to: '/quotes', icon: FileText, label: 'Teklifler' },
  { to: '/sessions', icon: MessageSquare, label: 'Oturumlar' },
];

export default function Layout({ children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <nav style={{
        width: 220, flexShrink: 0,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        position: 'sticky', top: 0, height: '100vh',
      }}>
        {/* Logo */}
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg,#4f7cff,#ef4444)',
              flexShrink: 0,
            }} />
            <div>
              <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: -.3 }}>The Blue Red</div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: .5 }}>ADMIN PANEL</div>
            </div>
          </div>
        </div>

        {/* Nav items */}
        <div style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 8,
                color: isActive ? 'var(--accent)' : 'var(--text-dim)',
                background: isActive ? 'var(--accent-dim)' : 'transparent',
                fontWeight: isActive ? 600 : 400,
                fontSize: 13, transition: 'all .15s',
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)', fontSize: 11, color: 'var(--text-dim)' }}>
          v1.0.0 · backend :8000
        </div>
      </nav>

      {/* Main */}
      <main style={{ flex: 1, padding: 28, overflowX: 'hidden' }}>
        {children}
      </main>
    </div>
  );
}
