import React, { useState, useEffect } from 'react';
import {
  Flame,
  MapPin,
  Users,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Clock,
  Shield,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import ApiClient from '../api/client';

export default function DashboardOverview({ onNavigate }) {
  const [stats, setStats] = useState({
    totalCrimes: 0,
    activeCrimes: 0,
    activePRPs: 0,
    availablePatrols: 0,
    totalPatrols: 0,
    activeSOS: 0,
    recentCrimes: [],
    recentAssignments: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch Crimes
      const crimesData = await ApiClient.get('/crimes', { page: 1, page_size: 5 });

      // 2. Fetch Patrol Status Summary
      const patrolSummary = await ApiClient.get('/admin/patrols/summary');

      // 3. Fetch PRPs
      const prpsData = await ApiClient.get('/admin/optimization/prps', { status: 'APPROVED', page_size: 10 });

      // 4. Fetch Assignments
      const assignData = await ApiClient.get('/admin/assignments', { page: 1, page_size: 5 });

      setStats({
        totalCrimes: crimesData.total || 0,
        activeCrimes: crimesData.items?.length || 0,
        activePRPs: prpsData.total || 0,
        availablePatrols: patrolSummary.available || 0,
        totalPatrols: patrolSummary.total || 0,
        activeSOS: 0, // Placeholder for SOS stage
        recentCrimes: crimesData.items || [],
        recentAssignments: assignData.items || [],
      });
    } catch (err) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', gap: '10px', color: 'var(--text-secondary)' }}>
        <Loader2 size={24} className="animate-spin" />
        <span>Loading operational overview...</span>
      </div>
    );
  }

  return (
    <div>
      {/* Error Alert */}
      {error && (
        <div style={{ background: 'rgba(244, 63, 94, 0.12)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '12px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', color: 'var(--accent-rose)', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {/* KPI Metric Cards */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        {/* Card 1: Crimes */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-rose)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Total Recorded Crimes</p>
              <h3 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>{stats.totalCrimes}</h3>
            </div>
            <div style={{ background: 'rgba(244, 63, 94, 0.15)', padding: '10px', borderRadius: '8px' }}>
              <Flame size={20} color="var(--accent-rose)" />
            </div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <TrendingUp size={14} color="var(--accent-emerald)" />
            <span>Active demand points tracked</span>
          </div>
        </div>

        {/* Card 2: Active PRPs */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-blue)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Active PRPs</p>
              <h3 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>{stats.activePRPs}</h3>
            </div>
            <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '10px', borderRadius: '8px' }}>
              <MapPin size={20} color="var(--accent-blue)" />
            </div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <CheckCircle2 size={14} color="var(--accent-blue)" />
            <span>Approved patrol response points</span>
          </div>
        </div>

        {/* Card 3: Patrol Units */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-emerald)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Available Patrols</p>
              <h3 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                {stats.availablePatrols} <span style={{ fontSize: '16px', fontWeight: 400, color: 'var(--text-muted)' }}>/ {stats.totalPatrols}</span>
              </h3>
            </div>
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '10px', borderRadius: '8px' }}>
              <Users size={20} color="var(--accent-emerald)" />
            </div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <Clock size={14} color="var(--accent-emerald)" />
            <span>Ready for dispatch & deployment</span>
          </div>
        </div>

        {/* Card 4: Active SOS */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-amber)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Active SOS Alerts</p>
              <h3 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>{stats.activeSOS}</h3>
            </div>
            <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '10px', borderRadius: '8px' }}>
              <AlertTriangle size={20} color="var(--accent-amber)" />
            </div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <Shield size={14} color="var(--accent-amber)" />
            <span>Real-time emergency monitoring</span>
          </div>
        </div>
      </div>

      {/* Quick Action Navigation */}
      <div className="grid-3" style={{ marginBottom: '24px' }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>PRP Optimization Solver</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Execute Google OR-Tools MCLP optimization to maximize patrol risk coverage.
            </p>
          </div>
          <button onClick={() => onNavigate('optimization')} className="btn btn-primary btn-sm" style={{ marginTop: '16px', alignSelf: 'flex-start' }}>
            <span>Run Optimizer</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>Interactive Tactical Map</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Inspect live multi-layer map with crimes, PRPs, patrol positions, and help points.
            </p>
          </div>
          <button onClick={() => onNavigate('map')} className="btn btn-secondary btn-sm" style={{ marginTop: '16px', alignSelf: 'flex-start' }}>
            <span>Open Map</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>Patrol Fleet Management</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Manage police officers, inspect unit availability, and trigger automated dispatch.
            </p>
          </div>
          <button onClick={() => onNavigate('patrols')} className="btn btn-secondary btn-sm" style={{ marginTop: '16px', alignSelf: 'flex-start' }}>
            <span>Manage Patrols</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Recent Activity Sections */}
      <div className="grid-2">
        {/* Recent Crimes */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h4 className="card-title" style={{ margin: 0 }}>
              <Flame size={18} color="var(--accent-rose)" />
              <span>Recent Crime Incidents</span>
            </h4>
            <button onClick={() => onNavigate('crimes')} className="btn btn-secondary btn-sm">View All</button>
          </div>
          {stats.recentCrimes.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>No recent crime incidents.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recentCrimes.map((c) => (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600 }}>{c.incident_number}</td>
                      <td>{c.category}</td>
                      <td>
                        <span className={`badge ${c.severity >= 4 ? 'badge-rose' : c.severity === 3 ? 'badge-amber' : 'badge-blue'}`}>
                          Lvl {c.severity}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{new Date(c.incident_time).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Assignments */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h4 className="card-title" style={{ margin: 0 }}>
              <Users size={18} color="var(--accent-blue)" />
              <span>Recent Patrol Deployments</span>
            </h4>
            <button onClick={() => onNavigate('patrols')} className="btn btn-secondary btn-sm">View Fleet</button>
          </div>
          {stats.recentAssignments.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>No active patrol assignments.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Call Sign</th>
                    <th>PRP Target</th>
                    <th>Shift</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recentAssignments.map((a) => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 600 }}>{a.call_sign}</td>
                      <td>{a.prp_name}</td>
                      <td>{a.shift}</td>
                      <td>
                        <span className={`badge ${a.status === 'COMPLETED' ? 'badge-emerald' : a.status === 'ARRIVED' ? 'badge-blue' : 'badge-amber'}`}>
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
