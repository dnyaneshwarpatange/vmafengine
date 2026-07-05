import { BrowserRouter as Router, Routes, Route, Link, useLocation } from "react-router-dom"
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider } from './context/AuthContext'
import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import Landing from "./pages/Landing"
import Dashboard from "./pages/Dashboard"
import Docs from "./pages/Docs"
import Auth from "./pages/Auth"

function Navbar() {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  
  return (
    <nav className="flex items-center justify-between px-6 py-4 lg:px-12 backdrop-blur-xl bg-slate-900/50 border-b border-border sticky top-0 z-50">
      <Link to="/" className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
        VMAF Engine
      </Link>
      
      {/* Mobile hamburger */}
      <button className="md:hidden text-white" onClick={() => setMobileOpen(!mobileOpen)}>
        {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>
      
      {/* Desktop nav */}
      <div className="hidden md:flex items-center space-x-6">
        <Link to="/docs" className={`text-sm font-medium transition-colors ${location.pathname === '/docs' ? 'text-white' : 'text-muted-foreground hover:text-white'}`}>API Docs</Link>
        <Link to="/dashboard" className={`text-sm font-medium transition-colors ${location.pathname === '/dashboard' ? 'text-white' : 'text-muted-foreground hover:text-white'}`}>Dashboard</Link>
        <Link to="/dashboard" className="bg-primary text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-primary/90 transition-transform active:scale-95 shadow-lg shadow-primary/20">
          Get Started
        </Link>
      </div>
      
      {/* Mobile nav dropdown */}
      {mobileOpen && (
        <div className="absolute top-full left-0 right-0 bg-slate-900/95 backdrop-blur-xl border-b border-border p-6 flex flex-col space-y-4 md:hidden z-50">
          <Link to="/docs" onClick={() => setMobileOpen(false)} className="text-sm font-medium text-muted-foreground hover:text-white transition-colors">API Docs</Link>
          <Link to="/dashboard" onClick={() => setMobileOpen(false)} className="text-sm font-medium text-muted-foreground hover:text-white transition-colors">Dashboard</Link>
          <Link to="/auth" onClick={() => setMobileOpen(false)} className="bg-primary text-white text-sm font-semibold px-4 py-2 rounded-lg text-center hover:bg-primary/90">Get Started</Link>
        </div>
      )}
    </nav>
  )
}

function App() {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '123-placeholder.apps.googleusercontent.com'

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <AuthProvider>
        <Router>
          <div className="min-h-screen flex flex-col bg-background font-sans antialiased text-foreground bg-gradient-radial">
            <Navbar />
            <main className="flex-1 flex flex-col">
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/auth" element={<Auth />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/docs" element={<Docs />} />
              </Routes>
            </main>
          </div>
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  )
}

export default App
