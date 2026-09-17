import React from 'react';
import {
  Shield,
  LayoutDashboard,
  MapPin,
  Flame,
  LifeBuoy,
  Cpu,
  Users,
  AlertTriangle,
  BarChart3,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'map', label: 'SafeZone Map', icon: MapPin },
  { id: 'crimes', label: 'Crime Incidents', icon: Flame },
  { id: 'help-points', label: 'Safe Help Points', icon: LifeBuoy },
  { id: 'optimization', label: 'PRP Optimizer', icon: Cpu },
  { id: 'patrols', label: 'Patrol Fleet', icon: Users },
  { id: 'sos', label: 'SOS Emergency', icon: AlertTriangle },
  { id: 'evaluation', label: 'Model Evaluation', icon: BarChart3 },
];

export default function Sidebar({ activeTab, onSelectTab }) {
  const { logout, user } = useAuth();

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ background: 'var(--accent-blue)', padding: '8px', borderRadius: '8px', display: 'flex' }}>
          <Shield size={22} color="#fff" />
        </div>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>SafeZone</h2>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Admin Portal</span>
        </div>
      </div>

      {/* Navigation List */}
      <div style={{ flex: 1, padding: '12px 0', overflowY: 'auto' }}>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab(item.id)}
            >
              <Icon size={18} />
              <span className="nav-text">{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* User Section & Logout */}
      <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ overflow: 'hidden' }}>
            <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user?.full_name || 'Administrator'}
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user?.email}
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-rose)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
