import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Calendar, MapPin, DollarSign, X } from 'lucide-react';
import { toast } from 'sonner';

function UserDashboard() {
  const { user } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
  try {
    const response = await axios.get(`${API}/bookings`, {
      withCredentials: true,
    });

    const list =
      response.data?.bookings ||
      response.data?.data?.bookings ||
      response.data?.result ||
      [];

    setBookings(Array.isArray(list) ? list : []);
  } catch (error) {
    toast.error('Failed to load bookings');
    setBookings([]);
  } finally {
    setLoading(false);
  }
};

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;

    try {
      await axios.patch(
        `${API}/bookings/${bookingId}/cancel`,
        {},
        { withCredentials: true }
      );
      toast.success('Booking cancelled');
      fetchBookings();
    } catch (error) {
      toast.error('Failed to cancel booking');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 py-12" data-testid="user-dashboard">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900">My Bookings</h1>
            <p className="text-gray-600 mt-2">Welcome back, {user?.name}!</p>
          </div>

          {loading ? (
            <div className="flex justify-center py-20">
              <div className="text-xl text-gray-600">Loading bookings...</div>
            </div>
          ) : bookings.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl shadow-sm">
              <Calendar size={64} className="mx-auto text-gray-300 mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">No bookings yet</h2>
              <p className="text-gray-600 mb-6">Start planning your next adventure!</p>
              <Button
                onClick={() => window.location.href = '/'}
                className="bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full px-8 py-3"
              >
                Explore Now
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {bookings.map((booking) => (
                <div
                  key={booking.booking_id}
                  className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition-shadow"
                  data-testid={`booking-${booking.booking_id}`}
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="text-xs text-gray-500 uppercase mb-1">
                          {booking.booking_type}
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">{booking.item_name}</h3>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(booking.status)}`}>
                        {booking.status}
                      </span>
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center text-gray-600 text-sm">
                        <Calendar size={16} className="mr-2" />
                        <span>
                          {new Date(booking.start_date).toLocaleDateString()}
                          {booking.end_date && ` - ${new Date(booking.end_date).toLocaleDateString()}`}
                        </span>
                      </div>
                      <div className="flex items-center text-[#FF6B6B] font-bold">
                        <DollarSign size={18} />
                        <span className="text-lg">{booking.total_price}</span>
                      </div>
                    </div>

                    {booking.status !== 'cancelled' && (
                      <Button
                        onClick={() => handleCancelBooking(booking.booking_id)}
                        variant="outline"
                        className="w-full text-red-600 border-red-200 hover:bg-red-50 rounded-lg"
                        data-testid="cancel-booking-button"
                      >
                        <X size={16} className="mr-2" />
                        Cancel Booking
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default UserDashboard;