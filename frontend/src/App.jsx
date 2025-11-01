import React, { useState } from 'react'
import Dashboard from './components/Dashboard'
import Strategies from './components/Strategies'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <div className="app">
      <header className="header">
        <h1>Black Trade</h1>
        <nav className="tabs">
          <button 
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button 
            className={activeTab === 'strategies' ? 'active' : ''}
            onClick={() => setActiveTab('strategies')}
          >
            Strategies
          </button>
        </nav>
      </header>
      <main className="main-content">
        {activeTab === 'dashboard' ? <Dashboard /> : <Strategies />}
      </main>
    </div>
  )
}

export default App







