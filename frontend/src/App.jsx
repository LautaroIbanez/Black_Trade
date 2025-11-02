import React, { useState } from 'react'
import Dashboard from './components/Dashboard'
import Strategies from './components/Strategies'
import TradingDashboard from './components/TradingDashboard'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('trading')
  // In production, this would come from authentication
  const [token] = useState(null)

  return (
    <div className="app">
      <header className="header">
        <h1>Black Trade</h1>
        <nav className="tabs">
          <button 
            className={activeTab === 'trading' ? 'active' : ''}
            onClick={() => setActiveTab('trading')}
          >
            Trading
          </button>
          <button 
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            Análisis
          </button>
          <button 
            className={activeTab === 'strategies' ? 'active' : ''}
            onClick={() => setActiveTab('strategies')}
          >
            Estrategias
          </button>
        </nav>
      </header>
      <main className="main-content">
        {activeTab === 'trading' && <TradingDashboard token={token} />}
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'strategies' && <Strategies />}
      </main>
    </div>
  )
}

export default App








