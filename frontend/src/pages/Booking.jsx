import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Calendar, Users, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

function Booking() {
  const { type, id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [item, setItem] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [guests, setGuests] = useState(1);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    fetchItem();
  }, [type, id]);

  const fetchItem = async () => {
    try {
      let url = '';
      if (type === 'hotel') url = `${API}/hotels/${id}`;
      else if (type === 'flight') url = `${API}/flights/${id}`;
      else if (type === 'car') url = `${API}/cars/${id}`;
      else if (type === 'experience') url = `${API}/experiences/${id}`;
      
      const response = await axios.get(url);
      setItem(response.data);
    } catch (error) {
      toast.error('Item not found');
      navigate('/search');
    } finally {
      setLoading(false);
    }
  };

  const calculateTotal = () => {
    if (!item || !startDate) return 0;
    
    if (type === 'hotel' && endDate) {
      const days = Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
      return item.price_per_night * days;
    } else if (type === 'car' && endDate) {
      const days = Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
      return item.price_per_day * days;
    } else if (type === 'flight') {
      return item.price * guests;
    } else if (type === 'experience') {
      return item.price * guests;
    }
    return 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBooking(true);

    try {
      const bookingData = {
        booking_type: type,
        item_id: id,
        start_date: new Date(startDate).toISOString(),
        end_date: endDate ? new Date(endDate).toISOString() : null,
        guests
      };

      await axios.post(
        `${API}/bookings`,
        bookingData,
        { withCredentials: true }
      );

      toast.success('Booking created successfully!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Booking failed');
    } finally {
      setBooking(false);
    }
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

  const itemName = item.name || item.title || `${item.brand} ${item.model}` || `${item.from_city} to ${item.to_city}`;

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 py-12" data-testid="booking-page">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-8">Complete Your Booking</h1>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-2">
              <div className="bg-white rounded-2xl shadow-sm p-8">
                <h2 className="text-2xl font-bold mb-6">Booking Details</h2>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <Label htmlFor="start-date">
                      {type === 'flight' ? 'Departure Date' : type === 'experience' ? 'Date' : 'Check-in Date'}
                    </Label>
                    <div className="mt-2 relative">
                      <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                      <Input
                        id="start-date"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        required
                        min={new Date().toISOString().split('T')[0]}
                        className="pl-10 bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                        data-testid="start-date-input"
                      />
                    </div>
                  </div>

                  {type !== 'experience' && type !== 'flight' && (
                    <div>
                      <Label htmlFor="end-date">Check-out Date</Label>
                      <div className="mt-2 relative">
                        <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                        <Input
                          id="end-date"
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          required
                          min={startDate || new Date().toISOString().split('T')[0]}
                          className="pl-10 bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                          data-testid="end-date-input"
                        />
                      </div>
                    </div>
                  )}

                  {(type === 'flight' || type === 'experience' || type === 'hotel') && (
                    <div>
                      <Label htmlFor="guests">
                        {type === 'flight' ? 'Passengers' : 'Guests'}
                      </Label>
                      <div className="mt-2 relative">
                        <Users className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                        <Input
                          id="guests"
                          type="number"
                          min="1"
                          value={guests}
                          onChange={(e) => setGuests(parseInt(e.target.value))}
                          required
                          className="pl-10 bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                          data-testid="guests-input"
                        />
                      </div>
                    </div>
                  )}

                  <div className="pt-6 border-t">
                    <h3 className="text-lg font-bold mb-4">Payment</h3>
                    <p className="text-gray-600 text-sm mb-4">
                      Payment will be processed securely. For this demo, bookings are created with pending payment status.
                    </p>
                  </div>

                  <Button
                    type="submit"
                    disabled={booking}
                    className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full py-6 text-lg font-semibold shadow-lg"
                    data-testid="confirm-booking-button"
                  >
                    {booking ? 'Processing...' : 'Confirm Booking'}
                  </Button>
                </form>
              </div>
            </div>

            <div className="md:col-span-1">
              <div className="bg-white rounded-2xl shadow-sm p-6 sticky top-20">
                <h3 className="text-xl font-bold mb-4">Booking Summary</h3>
                
                <div className="mb-4">
                  {item.image_url && (
                    <img
                      src={item.image_url}
                      alt={itemName}
                      className="w-full h-32 object-cover rounded-xl mb-4"
                    />
                  )}
                  <div className="font-bold text-lg">{itemName}</div>
                  {item.location && (
                    <div className="text-gray-600 text-sm">{item.location}</div>
                  )}
                </div>

                <div className="border-t pt-4 space-y-3">
                  {startDate && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Start Date:</span>
                      <span className="font-medium">{new Date(startDate).toLocaleDateString()}</span>
                    </div>
                  )}
                  {endDate && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">End Date:</span>
                      <span className="font-medium">{new Date(endDate).toLocaleDateString()}</span>
                    </div>
                  )}
                  {(type === 'flight' || type === 'experience') && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Guests:</span>
                      <span className="font-medium">{guests}</span>
                    </div>
                  )}
                </div>

                <div className="border-t mt-4 pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Total:</span>
                    <div className="flex items-center text-2xl font-bold text-[#FF6B6B]">
                      <DollarSign size={24} />
                      <span>{calculateTotal()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Booking;