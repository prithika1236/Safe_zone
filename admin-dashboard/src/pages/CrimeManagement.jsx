import React, { useState, useEffect } from 'react';
import {
  Flame,
  Plus,
  Upload,
  Search,
  Filter,
  Trash2,
  Edit2,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  X,
  Loader2,
} from 'lucide-react';
import ApiClient from '../api/client';

export default function CrimeManagement() {
  const [crimes, setCrimes] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [minSeverity, setMinSeverity] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCrime, setEditingCrime] = useState(null);
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [csvFile, setCsvFile] = useState(null);
  const [csvResult, setCsvResult] = useState(null);
  const [isCsvUploading, setIsCsvUploading] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    incident_number: '',
    category: 'Theft',
    severity: 3,
    incident_time: new Date().toISOString().slice(0, 16),
    latitude: 12.9716,
    longitude: 77.5946,
    description: '',
    is_active: true,
  });

  const fetchCrimes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await ApiClient.get('/crimes', {
        page,
        page_size: pageSize,
        search: search || undefined,
        category: categoryFilter || undefined,
        min_severity: minSeverity ? parseInt(minSeverity) : undefined,
      });
      setCrimes(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (err) {
      setError(err.message || 'Failed to fetch crimes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCrimes();
  }, [page, categoryFilter, minSeverity]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchCrimes();
  };

  const handleCreateOrUpdate = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        severity: parseInt(formData.severity),
        latitude: parseFloat(formData.latitude),
        longitude: parseFloat(formData.longitude),
        incident_time: new Date(formData.incident_time).toISOString(),
      };

      if (editingCrime) {
        await ApiClient.put(`/crimes/${editingCrime.id}`, payload);
      } else {
        await ApiClient.post('/crimes', payload);
      }

      setShowCreateModal(false);
      setEditingCrime(null);
      fetchCrimes();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleDeactivate = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this crime incident?')) return;
    try {
      await ApiClient.delete(`/crimes/${id}`);
      fetchCrimes();
    } catch (err) {
      alert(`Failed to deactivate crime: ${err.message}`);
    }
  };

  const handleCsvUpload = async (e) => {
    e.preventDefault();
    if (!csvFile) return;

    setIsCsvUploading(true);
    setCsvResult(null);
    try {
      const form = new FormData();
      form.append('file', csvFile);
      const res = await ApiClient.post('/crimes/import-csv', form);
      setCsvResult(res);
      fetchCrimes();
    } catch (err) {
      alert(`CSV upload failed: ${err.message}`);
    } finally {
      setIsCsvUploading(false);
    }
  };

  return (
    <div>
      {/* Action Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>Crime Incidents Management</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Track, inspect, filter, and import historical crime demand data.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => {
              setCsvResult(null);
              setCsvFile(null);
              setShowCsvModal(true);
            }}
            className="btn btn-secondary"
          >
            <Upload size={16} />
            <span>Import CSV</span>
          </button>
          <button
            onClick={() => {
              setEditingCrime(null);
              setFormData({
                incident_number: `CR-${Date.now().toString().slice(-6)}`,
                category: 'Theft',
                severity: 3,
                incident_time: new Date().toISOString().slice(0, 16),
                latitude: 12.9716,
                longitude: 77.5946,
                description: '',
                is_active: true,
              });
              setShowCreateModal(true);
            }}
            className="btn btn-primary"
          >
            <Plus size={16} />
            <span>Record Crime</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '32px' }}
              placeholder="Search by incident number or category..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ width: '180px' }}>
            <select className="form-select" value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}>
              <option value="">All Categories</option>
              <option value="Homicide">Homicide</option>
              <option value="Armed Robbery">Armed Robbery</option>
              <option value="Robbery">Robbery</option>
              <option value="Assault">Assault</option>
              <option value="Burglary">Burglary</option>
              <option value="Theft">Theft</option>
              <option value="Vandalism">Vandalism</option>
            </select>
          </div>

          <div style={{ width: '160px' }}>
            <select className="form-select" value={minSeverity} onChange={(e) => { setMinSeverity(e.target.value); setPage(1); }}>
              <option value="">All Severities</option>
              <option value="4">High (4 - 5)</option>
              <option value="3">Medium+ (3 - 5)</option>
              <option value="1">All (1 - 5)</option>
            </select>
          </div>

          <button type="submit" className="btn btn-secondary">Search</button>
        </form>
      </div>

      {/* Crime Table */}
      <div className="table-container">
        {isLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px' }} />
            <p>Loading incidents...</p>
          </div>
        ) : crimes.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>No crime incidents found matching your query.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Incident #</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Location</th>
                <th>Timestamp</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {crimes.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.incident_number}</td>
                  <td>{c.category}</td>
                  <td>
                    <span className={`badge ${c.severity >= 4 ? 'badge-rose' : c.severity === 3 ? 'badge-amber' : 'badge-blue'}`}>
                      Severity {c.severity}
                    </span>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {c.latitude?.toFixed(4)}, {c.longitude?.toFixed(4)}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    {new Date(c.incident_time).toLocaleString()}
                  </td>
                  <td>
                    <span className={`badge ${c.is_active ? 'badge-emerald' : 'badge-gray'}`}>
                      {c.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '6px' }}>
                      <button
                        onClick={() => {
                          setEditingCrime(c);
                          setFormData({
                            incident_number: c.incident_number,
                            category: c.category,
                            severity: c.severity,
                            incident_time: new Date(c.incident_time).toISOString().slice(0, 16),
                            latitude: c.latitude,
                            longitude: c.longitude,
                            description: c.description || '',
                            is_active: c.is_active,
                          });
                          setShowCreateModal(true);
                        }}
                        className="btn btn-secondary btn-sm"
                        title="Edit crime"
                      >
                        <Edit2 size={12} />
                      </button>
                      {c.is_active && (
                        <button
                          onClick={() => handleDeactivate(c.id)}
                          className="btn btn-danger btn-sm"
                          title="Deactivate crime"
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
        <span>Showing {crimes.length} of {total} incidents</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="btn btn-secondary btn-sm"
          >
            <ChevronLeft size={14} />
          </button>
          <span>Page {page} of {pages}</span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page >= pages}
            className="btn btn-secondary btn-sm"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Create / Edit Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{editingCrime ? 'Edit Crime Incident' : 'Record New Crime Incident'}</h3>
              <button onClick={() => setShowCreateModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateOrUpdate}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Incident Number</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingCrime}
                    className="form-input"
                    value={formData.incident_number}
                    onChange={(e) => setFormData({ ...formData, incident_number: e.target.value })}
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Category</label>
                    <select
                      className="form-select"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    >
                      <option value="Armed Robbery">Armed Robbery</option>
                      <option value="Robbery">Robbery</option>
                      <option value="Homicide">Homicide</option>
                      <option value="Assault">Assault</option>
                      <option value="Burglary">Burglary</option>
                      <option value="Theft">Theft</option>
                      <option value="Vandalism">Vandalism</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Severity (1 to 5)</label>
                    <input
                      type="number"
                      min="1"
                      max="5"
                      required
                      className="form-input"
                      value={formData.severity}
                      onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Incident Timestamp</label>
                  <input
                    type="datetime-local"
                    required
                    className="form-input"
                    value={formData.incident_time}
                    onChange={(e) => setFormData({ ...formData, incident_time: e.target.value })}
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Latitude</label>
                    <input
                      type="number"
                      step="0.000001"
                      required
                      className="form-input"
                      value={formData.latitude}
                      onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Longitude</label>
                    <input
                      type="number"
                      step="0.000001"
                      required
                      className="form-input"
                      value={formData.longitude}
                      onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Description (Optional)</label>
                  <textarea
                    rows={2}
                    className="form-textarea"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn btn-secondary">Cancel</button>
                <button type="submit" className="btn btn-primary">{editingCrime ? 'Save Changes' : 'Create Record'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Import Modal */}
      {showCsvModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Import Crime Dataset via CSV</h3>
              <button onClick={() => setShowCsvModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCsvUpload}>
              <div className="modal-body">
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  Upload a standard CSV file with headers: <code style={{ color: 'var(--accent-blue)' }}>incident_number, category, severity, incident_time, latitude, longitude</code>.
                </p>

                <div className="form-group">
                  <input
                    type="file"
                    accept=".csv"
                    required
                    className="form-input"
                    onChange={(e) => setCsvFile(e.target.files[0])}
                  />
                </div>

                {csvResult && (
                  <div style={{ marginTop: '16px', background: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
                      <span className="badge badge-emerald">Imported: {csvResult.imported_count}</span>
                      <span className={`badge ${csvResult.failed_count > 0 ? 'badge-rose' : 'badge-gray'}`}>Failed: {csvResult.failed_count}</span>
                      <span className="badge badge-blue">Total: {csvResult.total_rows}</span>
                    </div>

                    {csvResult.errors?.length > 0 && (
                      <div style={{ maxHeight: '160px', overflowY: 'auto', fontSize: '12px', color: 'var(--accent-rose)' }}>
                        <p style={{ fontWeight: 600, marginBottom: '4px' }}>Row-level validation errors:</p>
                        <ul style={{ paddingLeft: '18px' }}>
                          {csvResult.errors.map((err, i) => (
                            <li key={i}>Row {err.row_number} ({err.incident_number || 'N/A'}): {err.error}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setShowCsvModal(false)} className="btn btn-secondary">Close</button>
                <button type="submit" disabled={isCsvUploading || !csvFile} className="btn btn-primary">
                  {isCsvUploading ? <Loader2 size={16} className="animate-spin" /> : 'Upload & Process'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
