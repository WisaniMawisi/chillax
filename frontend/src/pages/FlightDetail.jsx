import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Plane, Calendar, Users, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

function FlightDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [flight, setFlight] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFlight();
  }, [id]);

  const fetchFlight = async () => {
    try {
      const response = await axios.get(`${API}/flights/${id}`);
      setFlight(response.data);
    } catch (error) {
      toast.error('Flight not found');
      navigate('/search');
    } finally {
      setLoading(false);
    }
  };

  const handleBook = () => {
    if (!user) {
      navigate('/login');
      return;
    }
    navigate(`/booking/flight/${id}`);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-screen">
          <div className="text-xl text-gray-600">Loading...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50" data-testid="flight-detail">
        <div className="relative h-80 overflow-hidden">
          <img src={flight.image_url} alt="Flight" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent"></div>
          <div className="absolute bottom-8 left-0 right-0 text-center text-white">
            <h1 className="text-4xl font-bold">{flight.airline}</h1>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="flex items-center justify-between mb-8">
              <div>
                <div className="text-3xl font-bold text-gray-900">{flight.from_city}</div>
                <div className="text-gray-500">Departure</div>
              </div>
              <Plane size={48} className="text-[#4ECDC4]" />
              <div className="text-right">
                <div className="text-3xl font-bold text-gray-900">{flight.to_city}</div>
                <div className="text-gray-500">Arrival</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6 mb-8">
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-gray-500 text-sm mb-1">Departure Time</div>
                <div className="text-lg font-bold">{new Date(flight.departure_time).toLocaleString()}</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-gray-500 text-sm mb-1">Arrival Time</div>
                <div className="text-lg font-bold">{new Date(flight.arrival_time).toLocaleString()}</div>
              </div>
            </div>

            <div className="flex items-center justify-between p-6 bg-[#FFE66D]/20 rounded-xl mb-6">
              <div>
                <div className="text-gray-700 mb-1">Available Seats</div>
                <div className="text-2xl font-bold">{flight.available_seats}</div>
              </div>
              <div className="text-right">
                <div className="text-gray-700 mb-1">Price per person</div>
                <div className="text-3xl font-bold text-[#FF6B6B]">${flight.price}</div>
              </div>
            </div>

            <Button
              onClick={handleBook}
              className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full px-8 py-6 text-lg font-semibold shadow-lg"
              data-testid="book-button"
            >
              Book Flight
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default FlightDetail;