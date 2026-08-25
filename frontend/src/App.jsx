import React, { createContext, useState, useEffect, useCallback, useContext, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from 'sonner';
import '@/App.css';

// Pages
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import AuthCallback from './pages/AuthCallback';
import SearchResults from './pages/SearchResults';
import HotelDetail from './pages/HotelDetail';
import FlightDetail from './pages/FlightDetail';
import CarDetail from './pages/CarDetail';
import ExperienceDetail from './pages/ExperienceDetail';
import UserDashboard from './pages/UserDashboard';
import AdminDashboard from './pages/AdminDashboard';
import Booking from './pages/Booking';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// --- Bearer-token auth ---
// The frontend (netlify.app) and backend (onrender.com) are
// different top-level domains, so this is a cross-site request.
// Modern browsers increasingly block third-party cookies by
// default, which silently drops the session cookie on requests
// like GET /auth/me even though CORS/credentials are configured
// correctly server-side. Bearer tokens in a header aren't subject
// to that blocking, so we use localStorage + an axios interceptor
// as the primary auth mechanism. The backend still also sets a
// cookie (harmless, and it's what makes same-origin/local dev
// work without any of this).
const TOKEN_STORAGE_KEY = 'chillax_access_token';

function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

// Attach the token to every outgoing request automatically, so
// individual pages don't need to remember to do it themselves.
axios.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  const checkAuth = useCallback(async () => {
    // No token stored means we're definitely logged out — skip
    // the network round-trip entirely.
    if (!getStoredToken()) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
    } catch (error) {
      // Token was invalid/expired — clear it so we don't keep
      // retrying with a dead token.
      setStoredToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip the /me check.
    // AuthCallback will exchange the session_id and establish the session first.
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout error:', error);
    }
    setStoredToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, checkAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && !user.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRouter() {
  const location = useLocation();

  // Check URL fragment for session_id during render (prevents race conditions)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/search" element={<SearchResults />} />
      <Route path="/hotels/:id" element={<HotelDetail />} />
      <Route path="/flights/:id" element={<FlightDetail />} />
      <Route path="/cars/:id" element={<CarDetail />} />
      <Route path="/experiences/:id" element={<ExperienceDetail />} />
      <Route
        path="/booking/:type/:id"
        element={
          <ProtectedRoute>
            <Booking />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <UserDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
export { API, BACKEND_URL, getStoredToken, setStoredToken };