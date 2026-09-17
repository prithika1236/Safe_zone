import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import DashboardOverview from './pages/DashboardOverview';
import SafeZoneMap from './pages/SafeZoneMap';
import CrimeManagement from './pages/CrimeManagement';
import HelpPointsManagement from './pages/HelpPointsManagement';
import PRPOptimization from './pages/PRPOptimization';
import PatrolManagement from './pages/PatrolManagement';
import SOSMonitoring from './pages/SOSMonitoring';
import EvaluationMetrics from './pages/EvaluationMetrics';

function DashboardApp() {
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid var(--border-color)', borderTopColor: 'var(--accent-blue)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px auto' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Loading SafeZone Portal...</h3>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard': return 'Operational Command Overview';
      case 'map': return 'SafeZone Interactive Geospatial Map';
      case 'crimes': return 'Crime Incident Records & CSV Ingestion';
      case 'help-points': return 'Safe Help Points Registry';
      case 'optimization': return 'Maximum Coverage Location Problem (MCLP) Optimizer';
      case 'patrols': return 'Patrol Fleet & Police Force Management';
      case 'sos': return 'Emergency SOS Panic Monitoring';
      case 'evaluation': return 'Explainable Risk & Model Evaluation';
      default: return 'SafeZone Admin Portal';
    }
  };

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardOverview onNavigate={setActiveTab} key={refreshTrigger} />;
      case 'map':
        return <SafeZoneMap key={refreshTrigger} />;
      case 'crimes':
        return <CrimeManagement key={refreshTrigger} />;
      case 'help-points':
        return <HelpPointsManagement key={refreshTrigger} />;
      case 'optimization':
        return <PRPOptimization key={refreshTrigger} />;
      case 'patrols':
        return <PatrolManagement key={refreshTrigger} />;
      case 'sos':
        return <SOSMonitoring key={refreshTrigger} />;
      case 'evaluation':
        return <EvaluationMetrics key={refreshTrigger} />;
      default:
        return <DashboardOverview onNavigate={setActiveTab} key={refreshTrigger} />;
    }
  };

  return (
    <Layout
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      title={getPageTitle()}
      onRefresh={handleRefresh}
    >
      {renderActiveTab()}
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardApp />
    </AuthProvider>
  );
}
