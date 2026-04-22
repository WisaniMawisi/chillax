import React from 'react';
import Navbar from './Navbar';

function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <footer className="bg-gray-900 text-white py-8" data-testid="footer">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="text-2xl font-bold mb-2">Chillax</div>
            <p className="text-gray-400 text-sm">Your relaxed travel companion</p>
            <p className="text-gray-500 text-xs mt-4">&copy; 2026 Chillax. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Layout;