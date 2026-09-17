import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, CircleMarker, useMap } from 'react-leaflet';
import L from 'leaflet';
import ApiClient from '../api/client';
import {
  Layers,
  Flame,
  LifeBuoy,
  Shield,
  Radio,
  AlertTriangle,
  RefreshCw,
  Eye,
  EyeOff,
} from 'lucide-react';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const createCustomIcon = (color, label, bg = '#1e293b') => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background: ${bg};
        border: 2px solid ${color};
        color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
      ">
        ${label}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

const prpIcon = createCustomIcon('#06b6d4', 'PRP', '#083344');
const patrolIcon = createCustomIcon('#3b82f6', 'POL', '#172554');
const helpPointIcon = createCustomIcon('#a855f7', 'SHP', '#3b0764');

function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, zoom);
    }
  }, [center, zoom, map]);
  return null;
}

export default function SafeZoneMap() {
  const [loading, setLoading] = useState(true);
  const [crimes, setCrimes] = useState([]);
  const [prps, setPrps] = useState([]);
  const [patrols, setPatrols] = useState([]);
  const [helpPoints, setHelpPoints] = useState([]);
  const [error, setError] = useState(null);

  const [layers, setLayers] = useState({
    crimes: true,
    prps: true,
    coverageCircles: true,
    patrols: true,
    helpPoints: true,
  });

  const [selectedShift, setSelectedShift] = useState('ALL');
  const [minSeverity, setMinSeverity] = useState(1);

  const fetchMapData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [crimeRes, prpRes, patrolRes, helpRes] = await Promise.all([
        ApiClient.get('/crimes', { page_size: 100 }),
        ApiClient.get('/admin/optimization/prps', { page_size: 100 }),
        ApiClient.get('/admin/patrols', { page_size: 100 }),
        ApiClient.get('/help-points', { page_size: 100 }),
      ]);

      setCrimes(crimeRes.items || []);
      setPrps(prpRes.items || []);
      setPatrols(patrolRes.items || []);
      setHelpPoints(helpRes.items || []);
    } catch (err) {
      console.error('Failed to load map data', err);
      setError('Unable to fetch live spatial layers. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData();
  }, []);

  const toggleLayer = (layerName) => {
    setLayers((prev) => ({ ...prev, [layerName]: !prev[layerName] }));
  };

  const getSeverityColor = (sev) => {
    if (sev >= 5) return '#f43f5e';
    if (sev >= 4) return '#f97316';
    if (sev >= 3) return '#eab308';
    if (sev >= 2) return '#06b6d4';
    return '#10b981';
  };

  const filteredCrimes = crimes.filter((c) => {
    if (c.severity < minSeverity) return false;
    return true;
  });

  const filteredPrps = prps.filter((p) => {
    if (selectedShift !== 'ALL' && p.shift_type !== selectedShift) return false;
    return true;
  });

  const defaultCenter = [12.9716, 77.5946];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', gap: '16px' }}>
      <div className="card" style={{ padding: '12px 18px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px', marginRight: '6px' }}>
            <Layers size={15} /> Layers:
          </span>

          <button
            className={`btn ${layers.crimes ? 'btn-secondary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px', borderColor: layers.crimes ? 'var(--accent-orange)' : 'var(--border-color)', color: layers.crimes ? 'var(--accent-orange)' : 'var(--text-muted)' }}
            onClick={() => toggleLayer('crimes')}
          >
            <Flame size={14} /> Crimes ({filteredCrimes.length})
          </button>

          <button
            className={`btn ${layers.prps ? 'btn-secondary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px', borderColor: layers.prps ? 'var(--accent-cyan)' : 'var(--border-color)', color: layers.prps ? 'var(--accent-cyan)' : 'var(--text-muted)' }}
            onClick={() => toggleLayer('prps')}
          >
            <Radio size={14} /> PRPs ({filteredPrps.length})
          </button>

          <button
            className={`btn ${layers.coverageCircles ? 'btn-secondary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px', borderColor: layers.coverageCircles ? 'var(--accent-blue)' : 'var(--border-color)', color: layers.coverageCircles ? 'var(--accent-blue)' : 'var(--text-muted)' }}
            onClick={() => toggleLayer('coverageCircles')}
          >
            {layers.coverageCircles ? <Eye size={14} /> : <EyeOff size={14} />} Coverage Radii
          </button>

          <button
            className={`btn ${layers.patrols ? 'btn-secondary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px', borderColor: layers.patrols ? 'var(--accent-blue)' : 'var(--border-color)', color: layers.patrols ? 'var(--accent-blue)' : 'var(--text-muted)' }}
            onClick={() => toggleLayer('patrols')}
          >
            <Shield size={14} /> Patrol Units ({patrols.length})
          </button>

          <button
            className={`btn ${layers.helpPoints ? 'btn-secondary' : 'btn-outline'}`}
            style={{ padding: '6px 12px', fontSize: '12px', borderColor: layers.helpPoints ? 'var(--accent-purple)' : 'var(--border-color)', color: layers.helpPoints ? 'var(--accent-purple)' : 'var(--text-muted)' }}
            onClick={() => toggleLayer('helpPoints')}
          >
            <LifeBuoy size={14} /> Safe Points ({helpPoints.length})
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Min Sev:</label>
            <select
              className="form-control"
              style={{ width: '70px', padding: '4px 8px', fontSize: '12px' }}
              value={minSeverity}
              onChange={(e) => setMinSeverity(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((s) => (
                <option key={s} value={s}>{s}+</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Shift:</label>
            <select
              className="form-control"
              style={{ width: '110px', padding: '4px 8px', fontSize: '12px' }}
              value={selectedShift}
              onChange={(e) => setSelectedShift(e.target.value)}
            >
              <option value="ALL">All Shifts</option>
              <option value="MORNING">Morning</option>
              <option value="EVENING">Evening</option>
              <option value="NIGHT">Night</option>
            </select>
          </div>

          <button
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
            onClick={fetchMapData}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      <div className="card" style={{ flex: 1, padding: 0, overflow: 'hidden', position: 'relative', borderRadius: '12px' }}>
        {error && (
          <div style={{ position: 'absolute', top: 12, left: 50, zIndex: 1000, background: 'rgba(239, 68, 68, 0.9)', color: '#fff', padding: '8px 16px', borderRadius: '6px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} /> {error}
          </div>
        )}

        <MapContainer
          center={defaultCenter}
          zoom={12}
          style={{ width: '100%', height: '100%' }}
        >
          <ChangeView center={defaultCenter} zoom={12} />

          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />

          {layers.crimes &&
            filteredCrimes.map((crime) => (
              <CircleMarker
                key={`crime-${crime.id}`}
                center={[crime.latitude, crime.longitude]}
                radius={crime.severity * 2.2 + 3}
                pathOptions={{
                  color: getSeverityColor(crime.severity),
                  fillColor: getSeverityColor(crime.severity),
                  fillOpacity: 0.7,
                  weight: 1.5,
                }}
              >
                <Popup>
                  <div style={{ minWidth: '180px', color: '#0f172a' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 700, fontSize: '13px' }}>{crime.crime_type}</span>
                      <span style={{ fontSize: '10px', background: getSeverityColor(crime.severity), color: '#fff', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        Sev {crime.severity}
                      </span>
                    </div>
                    <p style={{ margin: '2px 0', fontSize: '12px', color: '#475569' }}>{crime.description || 'No description'}</p>
                    <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: '#64748b' }}>
                      📅 {new Date(crime.occurred_at).toLocaleString()}
                    </p>
                    <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#64748b' }}>
                      📍 {crime.latitude.toFixed(4)}, {crime.longitude.toFixed(4)}
                    </p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

          {layers.prps &&
            filteredPrps.map((prp) => (
              <React.Fragment key={`prp-${prp.id}`}>
                {layers.coverageCircles && (
                  <Circle
                    center={[prp.latitude, prp.longitude]}
                    radius={prp.coverage_radius_meters || 1500}
                    pathOptions={{
                      color: prp.status === 'APPROVED' ? '#06b6d4' : '#64748b',
                      fillColor: prp.status === 'APPROVED' ? '#06b6d4' : '#64748b',
                      fillOpacity: 0.12,
                      dashArray: prp.status === 'APPROVED' ? null : '6, 6',
                      weight: 1.5,
                    }}
                  />
                )}
                <Marker position={[prp.latitude, prp.longitude]} icon={prpIcon}>
                  <Popup>
                    <div style={{ minWidth: '200px', color: '#0f172a' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontWeight: 700, fontSize: '13px' }}>Patrol Priority Point #{prp.id}</span>
                        <span style={{ fontSize: '10px', background: prp.status === 'APPROVED' ? '#06b6d4' : '#94a3b8', color: '#fff', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          {prp.status}
                        </span>
                      </div>
                      <p style={{ margin: '2px 0', fontSize: '12px' }}>
                        🎯 <strong>Priority Score:</strong> {prp.priority_score?.toFixed(2) || 'N/A'}
                      </p>
                      <p style={{ margin: '2px 0', fontSize: '12px' }}>
                        ⏰ <strong>Shift:</strong> {prp.shift_type || 'ALL'}
                      </p>
                      <p style={{ margin: '2px 0', fontSize: '12px' }}>
                        ⭕ <strong>Coverage:</strong> {prp.coverage_radius_meters}m
                      </p>
                      <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: '#64748b' }}>
                        📍 {prp.latitude.toFixed(4)}, {prp.longitude.toFixed(4)}
                      </p>
                    </div>
                  </Popup>
                </Marker>
              </React.Fragment>
            ))}

          {layers.patrols &&
            patrols
              .filter((p) => p.current_latitude && p.current_longitude)
              .map((unit) => (
                <Marker
                  key={`patrol-${unit.id}`}
                  position={[unit.current_latitude, unit.current_longitude]}
                  icon={patrolIcon}
                >
                  <Popup>
                    <div style={{ minWidth: '190px', color: '#0f172a' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontWeight: 700, fontSize: '13px' }}>{unit.call_sign}</span>
                        <span style={{ fontSize: '10px', background: '#3b82f6', color: '#fff', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          {unit.status}
                        </span>
                      </div>
                      <p style={{ margin: '2px 0', fontSize: '12px' }}>
                        🚔 <strong>Type:</strong> {unit.unit_type}
                      </p>
                      {unit.officer && (
                        <p style={{ margin: '2px 0', fontSize: '12px' }}>
                          👮 <strong>Officer:</strong> {unit.officer.badge_number} ({unit.officer.rank})
                        </p>
                      )}
                      <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: '#64748b' }}>
                        📍 {unit.current_latitude.toFixed(4)}, {unit.current_longitude.toFixed(4)}
                      </p>
                    </div>
                  </Popup>
                </Marker>
              ))}

          {layers.helpPoints &&
            helpPoints.map((hp) => (
              <Marker
                key={`hp-${hp.id}`}
                position={[hp.latitude, hp.longitude]}
                icon={helpPointIcon}
              >
                <Popup>
                  <div style={{ minWidth: '200px', color: '#0f172a' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 700, fontSize: '13px' }}>{hp.name}</span>
                      <span style={{ fontSize: '10px', background: hp.is_verified ? '#10b981' : '#f59e0b', color: '#fff', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                        {hp.is_verified ? 'Verified' : 'Unverified'}
                      </span>
                    </div>
                    <p style={{ margin: '2px 0', fontSize: '12px', color: '#475569' }}>
                      🏢 <strong>Type:</strong> {hp.point_type}
                    </p>
                    <p style={{ margin: '2px 0', fontSize: '12px', color: '#475569' }}>
                      🕒 <strong>24/7:</strong> {hp.is_24_7 ? 'Yes' : 'No'}
                    </p>
                    {hp.contact_phone && (
                      <p style={{ margin: '2px 0', fontSize: '12px', color: '#475569' }}>
                        📞 {hp.contact_phone}
                      </p>
                    )}
                    <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: '#64748b' }}>
                      📍 {hp.latitude.toFixed(4)}, {hp.longitude.toFixed(4)}
                    </p>
                  </div>
                </Popup>
              </Marker>
            ))}
        </MapContainer>
      </div>
    </div>
  );
}
