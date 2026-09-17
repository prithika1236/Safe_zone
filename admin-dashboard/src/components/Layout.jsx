import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ activeTab, onSelectTab, title, onRefresh, isRefreshing, children }) {
  return (
    <div className="app-container">
      <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
      <div className="main-content">
        <Header title={title} onRefresh={onRefresh} isRefreshing={isRefreshing} />
        <main className="page-container">{children}</main>
      </div>
    </div>
  );
}
