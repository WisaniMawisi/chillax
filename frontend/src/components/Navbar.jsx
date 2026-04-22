import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { LogOut, User, Heart, Calendar, LayoutDashboard, Menu, X } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const handleLogout = async () => {
    await logout();
    toast.success('Logged out successfully');
    navigate('/login');
  };

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-50" data-testid="main-navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2" data-testid="logo-link">
            <div className="text-2xl font-bold text-gradient">Chillax</div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="flex items-center space-x-2 text-gray-700 hover:text-[#FF6B6B] transition-colors"
                  data-testid="dashboard-link"
                >
                  <Calendar size={18} />
                  <span>My Bookings</span>
                </Link>
                {user.is_admin && (
                  <Link
                    to="/admin"
                    className="flex items-center space-x-2 text-gray-700 hover:text-[#FF6B6B] transition-colors"
                    data-testid="admin-link"
                  >
                    <LayoutDashboard size={18} />
                    <span>Admin</span>
                  </Link>
                )}
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2" data-testid="user-info">
                    {user.picture ? (
                      <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-[#4ECDC4] flex items-center justify-center text-white">
                        {user?.name?.[0]?.toUpperCase() || "U"}
                      </div>
                    )}
                    <span className="text-sm font-medium text-gray-700">{user.name}</span>
                  </div>
                  <Button
                    onClick={handleLogout}
                    variant="ghost"
                    size="sm"
                    className="text-gray-600 hover:text-[#FF6B6B]"
                    data-testid="logout-button"
                  >
                    <LogOut size={18} />
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-3">
                <Link to="/login" data-testid="login-link">
                  <Button variant="ghost" className="text-gray-700 hover:text-[#FF6B6B]">
                    Sign In
                  </Button>
                </Link>
                <Link to="/register" data-testid="register-link">
                  <Button className="bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full px-6 shadow-lg shadow-orange-200 transition-transform hover:scale-105">
                    Sign Up
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-gray-700"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-button"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 space-y-4" data-testid="mobile-menu">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  My Bookings
                </Link>
                {user.is_admin && (
                  <Link
                    to="/admin"
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Admin Dashboard
                  </Link>
                )}
                <button
                  onClick={() => {
                    handleLogout();
                    setMobileMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="block px-4 py-2 text-white bg-[#FF6B6B] hover:bg-[#FF5252] rounded-lg text-center"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;