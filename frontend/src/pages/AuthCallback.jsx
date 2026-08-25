import React, { useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import { setStoredToken } from '../App';

function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        const hash = location.hash;
        const params = new URLSearchParams(hash.substring(1));
        const session_id = params.get('session_id');

        if (!session_id) {
          navigate('/login');
          return;
        }

        const response = await axios.post(
          `${API}/auth/session`,
          { session_id },
          { withCredentials: true }
        );

        setStoredToken(response.data.access_token);
        setUser(response.data);
        navigate('/dashboard', { replace: true, state: { user: response.data } });
      } catch (error) {
        console.error('Auth callback error:', error);
        navigate('/login');
      }
    };

    processAuth();
  }, [location, navigate, setUser]);

  return (
    <div className="flex items-center justify-center min-h-screen" data-testid="auth-callback">
      <div className="text-center">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-[#FF6B6B] border-r-transparent"></div>
        <p className="mt-4 text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
}

export default AuthCallback;