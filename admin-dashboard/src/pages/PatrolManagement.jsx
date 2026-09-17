import React, { useState, useEffect } from 'react';
import ApiClient from '../api/client';
import {
  Users,
  Shield,
  Plus,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Navigation,
  XCircle,
  Car,
} from 'lucide-react';

export default function PatrolManagement() {
  const [activeTab, setActiveTab] = useState('fleet'); // 'fleet' | 'officers' | 'assignments'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Fleet & Officers Data
  const [patrols, setPatrols] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [assignments, setAssignments] = useState([]);

  // Modals
  const [showUnitModal, setShowUnitModal] = useState(false);
  const [showOfficerModal, setShowOfficerModal] = useState(false);
  const [showAutoDispatchModal, setShowAutoDispatchModal] = useState(false);

  // Forms
  const [unitForm, setUnitForm] = useState({
    call_sign: '',
    unit_type: 'CAR',
    officer_id: '',
    current_latitude: 12.9716,
    current_longitude: 77.5946,
  });

  const [officerForm, setOfficerForm] = useState({
    email: '',
    password: '',
    full_name: '',
    badge_number: '',
    rank: 'OFFICER',
    phone_number: '',
  });

  const [dispatchParams, setDispatchParams] = useState({
    shift_type: 'NIGHT',
    max_travel_distance_km: 15.0,
  });

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [patrolRes, officerRes, assignRes] = await Promise.all([
        ApiClient.get('/admin/patrols', { page_size: 100 }),
        ApiClient.get('/admin/officers', { page_size: 100 }),
        ApiClient.get('/admin/assignments', { page_size: 50 }),
      ]);

      setPatrols(patrolRes.items || []);
      setOfficers(officerRes.items || []);
      setAssignments(assignRes.items || []);
    } catch (err) {
      setError(err.message || 'Failed to load patrol resources');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpdateUnitStatus = async (unitId, newStatus) => {
    try {
      await ApiClient.patch(`/admin/patrols/${unitId}/status`, { status: newStatus });
      setSuccess(`Unit status updated to ${newStatus}`);
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to update unit status');
    }
  };

  const handleCreateUnit = async (e) => {
    e.preventDefault();
    try {
      await ApiClient.post('/admin/patrols', {
        ...unitForm,
        officer_id: unitForm.officer_id ? Number(unitForm.officer_id) : null,
        current_latitude: Number(unitForm.current_latitude),
        current_longitude: Number(unitForm.current_longitude),
      });
      setShowUnitModal(false);
      setUnitForm({ call_sign: '', unit_type: 'CAR', officer_id: '', current_latitude: 12.9716, current_longitude: 77.5946 });
      setSuccess('Patrol unit created successfully');
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to create patrol unit');
    }
  };

  const handleCreateOfficer = async (e) => {
    e.preventDefault();
    try {
      await ApiClient.post('/admin/officers', officerForm);
      setShowOfficerModal(false);
      setOfficerForm({ email: '', password: '', full_name: '', badge_number: '', rank: 'OFFICER', phone_number: '' });
      setSuccess('Police officer registered successfully');
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to create officer account');
    }
  };

  const handleAutoDispatch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await ApiClient.post('/admin/assignments/auto', {
        shift_type: dispatchParams.shift_type,
        max_travel_distance_km: Number(dispatchParams.max_travel_distance_km),
      });
      setShowAutoDispatchModal(false);
      setSuccess(`Auto-dispatch complete! ${res.assigned_count} patrol unit(s) dispatched to approved PRPs.`);
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to execute auto-dispatch');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelAssignment = async (assignmentId) => {
    if (!window.confirm('Cancel this patrol assignment and release unit back to AVAILABLE?')) return;
    try {
      await ApiClient.post(`/admin/assignments/${assignmentId}/cancel`);
      setSuccess('Assignment cancelled successfully');
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to cancel assignment');
    }
  };

  const getStatusBadge = (st) => {
    switch (st) {
      case 'AVAILABLE': return <span className="badge badge-success">Available</span>;
      case 'EN_ROUTE': return <span className="badge badge-info">En Route</span>;
      case 'ON_SCENE': return <span className="badge badge-warning">On Scene</span>;
      case 'BUSY': return <span className="badge badge-danger">Busy</span>;
      case 'OFF_DUTY': return <span className="badge" style={{ background: '#475569', color: '#cbd5e1' }}>Off Duty</span>;
      default: return <span className="badge badge-info">{st}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top operational summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Total Patrol Units</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-blue)', marginTop: '4px' }}>
            {patrols.length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Registered fleet</div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Available for Dispatch</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-emerald)', marginTop: '4px' }}>
            {patrols.filter((p) => p.status === 'AVAILABLE').length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Ready units</div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Active Deployments</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-cyan)', marginTop: '4px' }}>
            {assignments.filter((a) => ['ASSIGNED', 'ACKNOWLEDGED', 'ARRIVED'].includes(a.status)).length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Units at / en route to PRPs</div>
        </div>

        <div className="card" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>On-Duty Officers</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-purple)', marginTop: '4px' }}>
            {officers.filter((o) => o.is_on_duty).length} / {officers.length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Active roster</div>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid var(--accent-rose)', color: '#fca5a5', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      {success && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--accent-emerald)', color: '#6ee7b7', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} /> {success}
        </div>
      )}

      {/* Tabs and Actions Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className={`btn ${activeTab === 'fleet' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('fleet')}
          >
            <Car size={16} /> Patrol Units ({patrols.length})
          </button>
          <button
            className={`btn ${activeTab === 'officers' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('officers')}
          >
            <Users size={16} /> Officers Roster ({officers.length})
          </button>
          <button
            className={`btn ${activeTab === 'assignments' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('assignments')}
          >
            <Navigation size={16} /> Active Deployments ({assignments.length})
          </button>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {activeTab === 'fleet' && (
            <button className="btn btn-primary" onClick={() => setShowUnitModal(true)}>
              <Plus size={16} /> Add Patrol Unit
            </button>
          )}
          {activeTab === 'officers' && (
            <button className="btn btn-primary" onClick={() => setShowOfficerModal(true)}>
              <Plus size={16} /> Register Officer
            </button>
          )}
          {activeTab === 'assignments' && (
            <button className="btn btn-primary" onClick={() => setShowAutoDispatchModal(true)}>
              <Navigation size={16} /> Trigger Auto-Dispatch
            </button>
          )}
          <button className="btn btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* View 1: Patrol Units Fleet */}
      {activeTab === 'fleet' && (
        <div className="card">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Call Sign</th>
                  <th>Type</th>
                  <th>Assigned Officer</th>
                  <th>Current Location</th>
                  <th>Status</th>
                  <th>Change Status</th>
                </tr>
              </thead>
              <tbody>
                {patrols.map((unit) => (
                  <tr key={unit.id}>
                    <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{unit.call_sign}</td>
                    <td><span className="badge badge-info">{unit.unit_type}</span></td>
                    <td>
                      {unit.officer ? (
                        <div>
                          <div style={{ fontWeight: 600 }}>{unit.officer.user?.full_name || 'Officer'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Badge: {unit.officer.badge_number}</div>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Unassigned</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                      {unit.current_latitude?.toFixed(4)}, {unit.current_longitude?.toFixed(4)}
                    </td>
                    <td>{getStatusBadge(unit.status)}</td>
                    <td>
                      <select
                        className="form-control"
                        style={{ padding: '4px 8px', fontSize: '11px', width: '130px' }}
                        value={unit.status}
                        onChange={(e) => handleUpdateUnitStatus(unit.id, e.target.value)}
                      >
                        <option value="AVAILABLE">AVAILABLE</option>
                        <option value="EN_ROUTE">EN_ROUTE</option>
                        <option value="ON_SCENE">ON_SCENE</option>
                        <option value="BUSY">BUSY</option>
                        <option value="OFF_DUTY">OFF_DUTY</option>
                      </select>
                    </td>
                  </tr>
                ))}
                {patrols.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                      No patrol units registered yet. Click 'Add Patrol Unit' to create one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View 2: Police Officers Roster */}
      {activeTab === 'officers' && (
        <div className="card">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Badge No</th>
                  <th>Officer Name</th>
                  <th>Email</th>
                  <th>Rank</th>
                  <th>Phone</th>
                  <th>Duty Status</th>
                  <th>Account Status</th>
                </tr>
              </thead>
              <tbody>
                {officers.map((off) => (
                  <tr key={off.id}>
                    <td style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>{off.badge_number}</td>
                    <td style={{ fontWeight: 600 }}>{off.user?.full_name || 'N/A'}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{off.user?.email || 'N/A'}</td>
                    <td><span className="badge badge-info">{off.rank}</span></td>
                    <td style={{ fontSize: '12px' }}>{off.phone_number || 'N/A'}</td>
                    <td>
                      <span className={`badge ${off.is_on_duty ? 'badge-success' : 'badge-warning'}`}>
                        {off.is_on_duty ? 'On Duty' : 'Off Duty'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${off.user?.is_active !== false ? 'badge-success' : 'badge-danger'}`}>
                        {off.user?.is_active !== false ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                  </tr>
                ))}
                {officers.length === 0 && (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                      No police officers registered yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View 3: Patrol Assignments */}
      {activeTab === 'assignments' && (
        <div className="card">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Patrol Unit</th>
                  <th>Assigned PRP</th>
                  <th>Travel Dist</th>
                  <th>Est. Duration</th>
                  <th>Assigned At</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {assignments.map((asg) => (
                  <tr key={asg.id}>
                    <td style={{ fontWeight: 700 }}>#{asg.id}</td>
                    <td style={{ fontWeight: 600 }}>{asg.patrol_unit?.call_sign || `Unit #${asg.patrol_unit_id}`}</td>
                    <td>
                      <div>
                        <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>PRP #{asg.prp_id}</span>
                        {asg.prp && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            ({asg.prp.latitude?.toFixed(3)}, {asg.prp.longitude?.toFixed(3)})
                          </div>
                        )}
                      </div>
                    </td>
                    <td>{asg.distance_meters ? `${(asg.distance_meters / 1000).toFixed(2)} km` : 'N/A'}</td>
                    <td>{asg.estimated_duration_seconds ? `${Math.round(asg.estimated_duration_seconds / 60)} min` : 'N/A'}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {new Date(asg.assigned_at).toLocaleTimeString()}
                    </td>
                    <td>
                      <span className={`badge ${asg.status === 'COMPLETED' ? 'badge-success' : asg.status === 'CANCELLED' ? 'badge-danger' : 'badge-info'}`}>
                        {asg.status}
                      </span>
                    </td>
                    <td>
                      {['ASSIGNED', 'ACKNOWLEDGED', 'ARRIVED'].includes(asg.status) && (
                        <button
                          className="btn btn-outline"
                          style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--accent-rose)', borderColor: 'var(--accent-rose)' }}
                          onClick={() => handleCancelAssignment(asg.id)}
                        >
                          <XCircle size={13} /> Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {assignments.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                      No patrol assignments recorded yet. Use 'Trigger Auto-Dispatch' to deploy units to active PRPs.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Create Patrol Unit */}
      {showUnitModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Add New Patrol Unit</h3>
            <form onSubmit={handleCreateUnit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="label">Call Sign</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. PATROL-101"
                  className="form-control"
                  value={unitForm.call_sign}
                  onChange={(e) => setUnitForm({ ...unitForm, call_sign: e.target.value })}
                />
              </div>

              <div>
                <label className="label">Unit Type</label>
                <select
                  className="form-control"
                  value={unitForm.unit_type}
                  onChange={(e) => setUnitForm({ ...unitForm, unit_type: e.target.value })}
                >
                  <option value="CAR">Patrol Car</option>
                  <option value="BIKE">Motorcycle</option>
                  <option value="VAN">Tactical Van</option>
                  <option value="FOOT">Foot Patrol</option>
                </select>
              </div>

              <div>
                <label className="label">Assign Officer (Optional)</label>
                <select
                  className="form-control"
                  value={unitForm.officer_id}
                  onChange={(e) => setUnitForm({ ...unitForm, officer_id: e.target.value })}
                >
                  <option value="">-- No Officer --</option>
                  {officers.map((off) => (
                    <option key={off.id} value={off.id}>
                      {off.badge_number} - {off.user?.full_name || 'Officer'} ({off.rank})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label className="label">Start Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    className="form-control"
                    value={unitForm.current_latitude}
                    onChange={(e) => setUnitForm({ ...unitForm, current_latitude: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Start Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    className="form-control"
                    value={unitForm.current_longitude}
                    onChange={(e) => setUnitForm({ ...unitForm, current_longitude: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUnitModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Unit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Officer */}
      {showOfficerModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Register Police Officer</h3>
            <form onSubmit={handleCreateOfficer} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="label">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Officer Name"
                  className="form-control"
                  value={officerForm.full_name}
                  onChange={(e) => setOfficerForm({ ...officerForm, full_name: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label className="label">Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="officer@police.gov"
                    className="form-control"
                    value={officerForm.email}
                    onChange={(e) => setOfficerForm({ ...officerForm, email: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Password</label>
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    className="form-control"
                    value={officerForm.password}
                    onChange={(e) => setOfficerForm({ ...officerForm, password: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label className="label">Badge Number</label>
                  <input
                    type="text"
                    required
                    placeholder="B-4029"
                    className="form-control"
                    value={officerForm.badge_number}
                    onChange={(e) => setOfficerForm({ ...officerForm, badge_number: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Rank</label>
                  <select
                    className="form-control"
                    value={officerForm.rank}
                    onChange={(e) => setOfficerForm({ ...officerForm, rank: e.target.value })}
                  >
                    <option value="CONSTABLE">Constable</option>
                    <option value="SERGEANT">Sergeant</option>
                    <option value="INSPECTOR">Inspector</option>
                    <option value="COMMISSIONER">Commissioner</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="label">Phone Number</label>
                <input
                  type="tel"
                  placeholder="+91 9876543210"
                  className="form-control"
                  value={officerForm.phone_number}
                  onChange={(e) => setOfficerForm({ ...officerForm, phone_number: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowOfficerModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Officer Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Auto Dispatch */}
      {showAutoDispatchModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>Trigger Automatic Dispatch</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Assign available patrol units to APPROVED PRPs using transparent distance-optimal bipartite matching.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="label">Shift Context</label>
                <select
                  className="form-control"
                  value={dispatchParams.shift_type}
                  onChange={(e) => setDispatchParams({ ...dispatchParams, shift_type: e.target.value })}
                >
                  <option value="MORNING">Morning (06:00 - 14:00)</option>
                  <option value="EVENING">Evening (14:00 - 22:00)</option>
                  <option value="NIGHT">Night (22:00 - 06:00)</option>
                </select>
              </div>

              <div>
                <label className="label">Max Travel Distance (km)</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  className="form-control"
                  value={dispatchParams.max_travel_distance_km}
                  onChange={(e) => setDispatchParams({ ...dispatchParams, max_travel_distance_km: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button className="btn btn-secondary" onClick={() => setShowAutoDispatchModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={handleAutoDispatch} disabled={loading}>
                  Run Auto-Dispatch
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
