import React from 'react'
import { Dashboard } from './components/Dashboard'
import { Toaster } from './components/ui/toaster'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Dashboard />
      <Toaster />
    </div>
  )
}

export default App