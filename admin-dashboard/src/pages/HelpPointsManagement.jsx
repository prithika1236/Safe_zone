import React, { useState, useEffect } from 'react';
import {
  LifeBuoy,
  Plus,
  Upload,
  CheckCircle,
  XCircle,
  Edit2,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  X,
  ShieldCheck,
} from 'lucide-react';
import ApiClient from '../api/client';

export default function HelpPointsManagement() {
  const [helpPoints, setHelpPoints] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [pageSize] = useState(15);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Modals
  const [showModal, setShowModal] = useState(false);
  const [editingPoint, setEditingPoint] = useState(null);
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [csvFile, setCsvFile] = useState(null);
  const [csvResult, setCsvResult] = useState(null);
  const [isCsvUploading, setIsCsvUploading] = useState(false);

  // Form
  const [formData, setFormData] = useState({
    name: '',
    category: 'POLICE_STATION',
    latitude: 12.9716,
    longitude: 77.5946,
    address: '',
    contact_number: '',
    is_verified: true,
    is_active: true,
  });

  const fetchHelpPoints = async () => {
    setIsLoading(true);
    try {
      const data = await ApiClient.get('/admin/help-points', {
        page,
        page_size: pageSize,
        category: categoryFilter || undefined,
      });
      setHelpPoints(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (err) {
      alert(`Failed to fetch Safe Help Points: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHelpPoints();
  }, [page, categoryFilter]);

  const handleCreateOrUpdate = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        latitude: parseFloat(formData.latitude),
        longitude: parseFloat(formData.longitude),
      };

      if (editingPoint) {
        await ApiClient.put(`/admin/help-points/${editingPoint.id}`, payload);
      } else {
        await ApiClient.post('/admin/help-points', payload);
      }

      setShowModal(false);
      setEditingPoint(null);
      fetchHelpPoints();
    } catch (err) {
      alert(`Error saving help point: ${err.message}`);
    }
  };

  const handleToggleVerify = async (hp) => {
    try {
      await ApiClient.put(`/admin/help-points/${hp.id}`, { is_verified: !hp.is_verified });
      fetchHelpPoints();
    } catch (err) {
      alert(`Failed to update verification: ${err.message}`);
    }
  };

  const handleToggleActive = async (hp) => {
    try {
      await ApiClient.put(`/admin/help-points/${hp.id}`, { is_active: !hp.is_active });
      fetchHelpPoints();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
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
      const res = await ApiClient.post('/admin/help-points/import-csv', form);
      setCsvResult(res);
      fetchHelpPoints();
    } catch (err) {
      alert(`CSV upload failed: ${err.message}`);
    } finally {
      setIsCsvUploading(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>Safe Help Points Management</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Administer verified public safe shelters, police kiosks, and emergency help points for citizens.
          </p>
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
              setEditingPoint(null);
              setFormData({
                name: '',
                category: 'POLICE_STATION',
                latitude: 12.9716,
                longitude: 77.5946,
                address: '',
                contact_number: '',
                is_verified: true,
                is_active: true,
              });
              setShowModal(true);
            }}
            className="btn btn-primary"
          >
            <Plus size={16} />
            <span>Add Safe Point</span>
          </button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label className="form-label" style={{ margin: 0 }}>Filter Category:</label>
          <select className="form-select" style={{ maxWidth: '240px' }} value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}>
            <option value="">All Categories</option>
            <option value="POLICE_STATION">Police Station</option>
            <option value="HOSPITAL">Hospital</option>
            <option value="SHELTER">Shelter</option>
            <option value="FIRE_STATION">Fire Station</option>
            <option value="HELP_DESK">Help Desk</option>
            <option value="OTHER">Other</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        {isLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px' }} />
            <p>Loading Safe Help Points...</p>
          </div>
        ) : helpPoints.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>No Safe Help Points recorded.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Location</th>
                <th>Contact</th>
                <th>Verified</th>
                <th>Active</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {helpPoints.map((hp) => (
                <tr key={hp.id}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{hp.name}</td>
                  <td>
                    <span className="badge badge-purple">{hp.category}</span>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {hp.latitude?.toFixed(4)}, {hp.longitude?.toFixed(4)}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{hp.contact_number || 'N/A'}</td>
                  <td>
                    <button
                      onClick={() => handleToggleVerify(hp)}
                      className={`badge ${hp.is_verified ? 'badge-emerald' : 'badge-gray'}`}
                      style={{ border: 'none', cursor: 'pointer' }}
                      title="Click to toggle verification"
                    >
                      {hp.is_verified ? 'Verified' : 'Unverified'}
                    </button>
                  </td>
                  <td>
                    <button
                      onClick={() => handleToggleActive(hp)}
                      className={`badge ${hp.is_active ? 'badge-blue' : 'badge-rose'}`}
                      style={{ border: 'none', cursor: 'pointer' }}
                      title="Click to toggle active status"
                    >
                      {hp.is_active ? 'Active' : 'Disabled'}
                    </button>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      onClick={() => {
                        setEditingPoint(hp);
                        setFormData({
                          name: hp.name,
                          category: hp.category,
                          latitude: hp.latitude,
                          longitude: hp.longitude,
                          address: hp.address || '',
                          contact_number: hp.contact_number || '',
                          is_verified: hp.is_verified,
                          is_active: hp.is_active,
                        });
                        setShowModal(true);
                      }}
                      className="btn btn-secondary btn-sm"
                    >
                      <Edit2 size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
        <span>Showing {helpPoints.length} of {total} points</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="btn btn-secondary btn-sm">
            <ChevronLeft size={14} />
          </button>
          <span>Page {page} of {pages}</span>
          <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages} className="btn btn-secondary btn-sm">
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{editingPoint ? 'Edit Safe Help Point' : 'Add New Safe Help Point'}</h3>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateOrUpdate}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Location / Facility Name</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select
                    className="form-select"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    <option value="POLICE_STATION">Police Station</option>
                    <option value="HOSPITAL">Hospital</option>
                    <option value="SHELTER">Shelter</option>
                    <option value="FIRE_STATION">Fire Station</option>
                    <option value="HELP_DESK">Help Desk</option>
                    <option value="OTHER">Other</option>
                  </select>
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
                  <label className="form-label">Address / Landmark</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Contact Phone (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.contact_number}
                    onChange={(e) => setFormData({ ...formData, contact_number: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-secondary">Cancel</button>
                <button type="submit" className="btn btn-primary">{editingPoint ? 'Update Point' : 'Create Point'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Modal */}
      {showCsvModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Import Safe Help Points CSV</h3>
              <button onClick={() => setShowCsvModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCsvUpload}>
              <div className="modal-body">
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  Upload CSV with headers: <code style={{ color: 'var(--accent-blue)' }}>name, category, latitude, longitude, address, contact_number</code>.
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
                  <div style={{ marginTop: '16px', background: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ display: 'flex', gap: '16px' }}>
                      <span className="badge badge-emerald">Imported: {csvResult.imported_count}</span>
                      <span className="badge badge-gray">Failed: {csvResult.failed_count}</span>
                      <span className="badge badge-blue">Total: {csvResult.total_rows}</span>
                    </div>
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
