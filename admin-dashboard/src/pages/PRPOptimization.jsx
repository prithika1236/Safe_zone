import React, { useState, useEffect } from 'react';
import ApiClient from '../api/client';
import {
  Cpu,
  Play,
  Eye,
  CheckCircle2,
  AlertTriangle,
  History,
  ShieldAlert,
  Radio,
  Check,
} from 'lucide-react';

export default function PRPOptimization() {
  const [activeView, setActiveView] = useState('optimizer'); // 'optimizer' | 'history'
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Optimizer Inputs
  const [params, setParams] = useState({
    shift_type: 'NIGHT',
    patrol_count: 5,
    coverage_radius_meters: 1500,
    candidate_cluster_radius_meters: 500,
    time_decay_lambda: 0.05,
    min_severity: 1,
  });

  // Current Optimization Result
  const [result, setResult] = useState(null);
  const [isPersisted, setIsPersisted] = useState(false);

  // Historical Runs
  const [historyRuns, setHistoryRuns] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await ApiClient.get('/admin/optimization/runs', { page: 1, page_size: 20 });
      setHistoryRuns(res.items || []);
    } catch (err) {
      console.error('Failed to load history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (activeView === 'history') {
      fetchHistory();
    }
  }, [activeView]);

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await ApiClient.post('/admin/optimization/preview', {
        ...params,
        patrol_count: Number(params.patrol_count),
        coverage_radius_meters: Number(params.coverage_radius_meters),
        candidate_cluster_radius_meters: Number(params.candidate_cluster_radius_meters),
        time_decay_lambda: Number(params.time_decay_lambda),
        min_severity: Number(params.min_severity),
      });
      setResult(data);
      setIsPersisted(false);
      setSuccessMsg('Preview generated successfully! Check covered risk and PRPs below.');
    } catch (err) {
      setError(err.message || 'Failed to preview optimization');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = await ApiClient.post('/admin/optimization/run', {
        ...params,
        patrol_count: Number(params.patrol_count),
        coverage_radius_meters: Number(params.coverage_radius_meters),
        candidate_cluster_radius_meters: Number(params.candidate_cluster_radius_meters),
        time_decay_lambda: Number(params.time_decay_lambda),
        min_severity: Number(params.min_severity),
      });
      setResult(data);
      setIsPersisted(true);
      setSuccessMsg(`Optimization Run #${data.run_id} executed and saved! Click 'Approve & Activate' to dispatch.`);
    } catch (err) {
      setError(err.message || 'Failed to execute optimization run');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (runId) => {
    const targetId = runId || result?.run_id;
    if (!targetId) return;

    setApproving(true);
    setError(null);
    try {
      const updated = await ApiClient.post(`/admin/optimization/runs/${targetId}/approve`);
      setResult(updated);
      setSuccessMsg(`Optimization Run #${targetId} and PRPs are now APPROVED & ACTIVE!`);
      if (activeView === 'history') {
        fetchHistory();
      }
    } catch (err) {
      setError(err.message || 'Failed to approve optimization run');
    } finally {
      setApproving(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Navigation sub-tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        <button
          className={`btn ${activeView === 'optimizer' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveView('optimizer')}
        >
          <Cpu size={16} /> Maximum Coverage PRP Optimizer (MCLP)
        </button>
        <button
          className={`btn ${activeView === 'history' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveView('history')}
        >
          <History size={16} /> Optimization Run History
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid var(--accent-rose)', color: '#fca5a5', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      {successMsg && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--accent-emerald)', color: '#6ee7b7', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} /> {successMsg}
        </div>
      )}

      {activeView === 'optimizer' && (
        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '20px' }}>
          {/* Configuration Form Card */}
          <div className="card">
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} color="var(--accent-cyan)" /> OR-Tools MCLP Parameters
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="label">Operational Shift Context</label>
                <select
                  className="form-control"
                  value={params.shift_type}
                  onChange={(e) => setParams({ ...params, shift_type: e.target.value })}
                >
                  <option value="MORNING">Morning (06:00 - 14:00)</option>
                  <option value="EVENING">Evening (14:00 - 22:00)</option>
                  <option value="NIGHT">Night (22:00 - 06:00)</option>
                </select>
              </div>

              <div>
                <label className="label">Available Patrol Units (P)</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  className="form-control"
                  value={params.patrol_count}
                  onChange={(e) => setParams({ ...params, patrol_count: e.target.value })}
                />
                <small style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                  Max PRPs selected &le; Patrol Units (Zero double-counting)
                </small>
              </div>

              <div>
                <label className="label">Patrol Coverage Radius (R in meters)</label>
                <input
                  type="number"
                  min="200"
                  max="10000"
                  step="100"
                  className="form-control"
                  value={params.coverage_radius_meters}
                  onChange={(e) => setParams({ ...params, coverage_radius_meters: e.target.value })}
                />
                <small style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                  Standard urban radius: 1500m (1.5 km)
                </small>
              </div>

              <div>
                <label className="label">Candidate Cluster Radius (meters)</label>
                <input
                  type="number"
                  min="100"
                  max="3000"
                  step="50"
                  className="form-control"
                  value={params.candidate_cluster_radius_meters}
                  onChange={(e) => setParams({ ...params, candidate_cluster_radius_meters: e.target.value })}
                />
              </div>

              <div>
                <label className="label">Time Decay Factor (&lambda;)</label>
                <input
                  type="number"
                  min="0.001"
                  max="1.0"
                  step="0.01"
                  className="form-control"
                  value={params.time_decay_lambda}
                  onChange={(e) => setParams({ ...params, time_decay_lambda: e.target.value })}
                />
                <small style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                  Recency weight formula: exp(-&lambda; &middot; age_in_days)
                </small>
              </div>

              <div>
                <label className="label">Minimum Crime Severity</label>
                <select
                  className="form-control"
                  value={params.min_severity}
                  onChange={(e) => setParams({ ...params, min_severity: e.target.value })}
                >
                  <option value="1">1+ (All incidents)</option>
                  <option value="2">2+ (Minor to Severe)</option>
                  <option value="3">3+ (Moderate to Severe)</option>
                  <option value="4">4+ (High & Critical)</option>
                  <option value="5">5 (Critical only)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={handlePreview}
                  disabled={loading}
                >
                  <Eye size={16} /> Preview
                </button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1.2 }}
                  onClick={handleRun}
                  disabled={loading}
                >
                  <Play size={16} /> Run & Save
                </button>
              </div>
            </div>
          </div>

          {/* Results & Inspection Panel */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {result ? (
              <>
                {/* Result KPI Metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  <div className="card" style={{ padding: '16px', background: 'var(--card-bg)' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Coverage Rate</div>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-emerald)', marginTop: '4px' }}>
                      {result.coverage_percentage?.toFixed(1)}%
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Unique risk covered</div>
                  </div>

                  <div className="card" style={{ padding: '16px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Covered / Total Risk</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--accent-cyan)', marginTop: '4px' }}>
                      {result.covered_risk?.toFixed(1)} / {result.total_risk?.toFixed(1)}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>MCLP Objective</div>
                  </div>

                  <div className="card" style={{ padding: '16px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Selected PRPs</div>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-blue)', marginTop: '4px' }}>
                      {result.selected_prps?.length || 0} / {params.patrol_count}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Patrol constraint</div>
                  </div>

                  <div className="card" style={{ padding: '16px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 600 }}>Solver Status</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: result.solver_status === 'OPTIMAL' ? 'var(--accent-emerald)' : 'var(--accent-amber)', marginTop: '4px' }}>
                      {result.solver_status}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>OR-Tools CP-SAT</div>
                  </div>
                </div>

                {/* Approve Action Banner if persisted and unapproved */}
                {isPersisted && result.run_id && result.status !== 'APPROVED' && (
                  <div className="card" style={{ background: 'rgba(6, 182, 212, 0.1)', borderColor: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
                    <div>
                      <h4 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                        Optimization Run #{result.run_id} is in PROPOSED status
                      </h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                        Approving will activate these PRPs and make them available for automated patrol assignment.
                      </p>
                    </div>
                    <button
                      className="btn btn-primary"
                      onClick={() => handleApprove(result.run_id)}
                      disabled={approving}
                      style={{ padding: '10px 20px', fontSize: '13px' }}
                    >
                      <Check size={16} /> {approving ? 'Activating...' : 'Approve & Activate Run'}
                    </button>
                  </div>
                )}

                {/* Selected PRPs Table */}
                <div className="card">
                  <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Radio size={16} color="var(--accent-cyan)" /> Selected Patrol Priority Points ({result.selected_prps?.length || 0})
                  </h4>

                  <div className="table-responsive">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>PRP Point</th>
                          <th>Coordinates</th>
                          <th>Shift</th>
                          <th>Priority Score</th>
                          <th>Radius</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.selected_prps?.map((prp, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: 600 }}>PRP #{prp.id || idx + 1}</td>
                            <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                              {prp.latitude.toFixed(4)}, {prp.longitude.toFixed(4)}
                            </td>
                            <td>
                              <span className="badge badge-info">{prp.shift_type || params.shift_type}</span>
                            </td>
                            <td style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>
                              {prp.priority_score?.toFixed(2)}
                            </td>
                            <td>{prp.coverage_radius_meters || params.coverage_radius_meters}m</td>
                            <td>
                              <span className={`badge ${prp.status === 'APPROVED' ? 'badge-success' : 'badge-warning'}`}>
                                {prp.status || 'RECOMMENDED'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Uncovered High-Risk Points */}
                {result.uncovered_demand_points && result.uncovered_demand_points.length > 0 && (
                  <div className="card">
                    <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShieldAlert size={16} /> Uncovered Demand Points ({result.uncovered_demand_points.length})
                    </h4>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>
                      These demand points could not be covered given the current limit of {params.patrol_count} patrol units and {params.coverage_radius_meters}m radius.
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {result.uncovered_demand_points.slice(0, 10).map((dp, idx) => (
                        <div key={idx} style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px 10px', fontSize: '11px' }}>
                          Demand #{dp.id || idx + 1}: ({dp.latitude?.toFixed(3)}, {dp.longitude?.toFixed(3)}) - Risk: {dp.weight?.toFixed(1) || dp.risk_score?.toFixed(1)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '380px', color: 'var(--text-muted)', textAlign: 'center' }}>
                <Cpu size={48} strokeWidth={1} style={{ marginBottom: '16px', opacity: 0.5 }} />
                <h4 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>No Optimization Executed Yet</h4>
                <p style={{ fontSize: '13px', maxWidth: '400px', marginTop: '6px' }}>
                  Configure shift and patrol parameters on the left and click <strong>Preview</strong> or <strong>Run & Save</strong> to solve the Maximum Coverage Location Problem.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Historical Runs View */}
      {activeView === 'history' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Historical Optimization Runs</h3>
            <button className="btn btn-secondary" onClick={fetchHistory} disabled={historyLoading}>
              Refresh Runs
            </button>
          </div>

          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Date & Time</th>
                  <th>Shift</th>
                  <th>Patrols (P)</th>
                  <th>Coverage %</th>
                  <th>Covered Risk</th>
                  <th>Solver Status</th>
                  <th>Approval State</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {historyRuns.map((run) => (
                  <tr key={run.id}>
                    <td style={{ fontWeight: 700 }}>#{run.id}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td><span className="badge badge-info">{run.shift_type}</span></td>
                    <td>{run.patrol_count}</td>
                    <td style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>
                      {run.coverage_percentage?.toFixed(1)}%
                    </td>
                    <td>{run.covered_risk?.toFixed(1)} / {run.total_risk?.toFixed(1)}</td>
                    <td>
                      <span className={`badge ${run.solver_status === 'OPTIMAL' ? 'badge-success' : 'badge-warning'}`}>
                        {run.solver_status}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${run.status === 'APPROVED' ? 'badge-success' : 'badge-warning'}`}>
                        {run.status}
                      </span>
                    </td>
                    <td>
                      {run.status !== 'APPROVED' ? (
                        <button
                          className="btn btn-primary"
                          style={{ padding: '4px 10px', fontSize: '11px' }}
                          onClick={() => handleApprove(run.id)}
                          disabled={approving}
                        >
                          Approve
                        </button>
                      ) : (
                        <span style={{ fontSize: '12px', color: 'var(--accent-emerald)', fontWeight: 600 }}>Active</span>
                      )}
                    </td>
                  </tr>
                ))}
                {historyRuns.length === 0 && !historyLoading && (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                      No optimization runs recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
