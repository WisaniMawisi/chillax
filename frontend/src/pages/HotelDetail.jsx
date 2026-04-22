import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Star, MapPin, Wifi, Coffee, Tv, DollarSign, Heart } from 'lucide-react';
import { toast } from 'sonner';

function HotelDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [hotel, setHotel] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHotel();
    fetchReviews();
  }, [id]);

  const fetchHotel = async () => {
    try {
      const response = await axios.get(`${API}/hotels/${id}`);
      setHotel(response.data);
    } catch (error) {
      toast.error('Hotel not found');
      navigate('/search');
    } finally {
      setLoading(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const response = await axios.get(`${API}/reviews/hotel/${id}`);
      setReviews(response.data);
    } catch (error) {
      console.error(error);
    }
  };

  const handleBook = () => {
    if (!user) {
      navigate('/login');
      return;
    }
    navigate(`/booking/hotel/${id}`);
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
      <div className="min-h-screen bg-gray-50" data-testid="hotel-detail">
        <div className="relative h-96 overflow-hidden">
          <img src={hotel.image_url} alt={hotel.name} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-20 relative">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
              <div className="flex-1">
                <h1 className="text-4xl font-bold text-gray-900 mb-3">{hotel.name}</h1>
                <div className="flex items-center text-gray-600 mb-4">
                  <MapPin size={20} className="mr-2" />
                  <span>{hotel.location}, {hotel.city}, {hotel.country}</span>
                </div>
                {hotel.rating > 0 && (
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center bg-[#FFE66D] rounded-lg px-3 py-1">
                      <Star className="rating-star" size={18} fill="#FFE66D" />
                      <span className="ml-1 font-bold">{hotel.rating}</span>
                    </div>
                    <span className="text-gray-600">({reviews.length} reviews)</span>
                  </div>
                )}
              </div>
              
              <div className="mt-6 md:mt-0">
                <div className="text-right mb-4">
                  <div className="text-4xl font-bold text-[#FF6B6B]">${hotel.price_per_night}</div>
                  <div className="text-gray-500">per night</div>
                </div>
                <Button
                  onClick={handleBook}
                  className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full px-8 py-6 text-lg font-semibold shadow-lg"
                  data-testid="book-button"
                >
                  Book Now
                </Button>
              </div>
            </div>

            <div className="border-t pt-6 mb-6">
              <h2 className="text-2xl font-bold mb-4">About</h2>
              <p className="text-gray-700">{hotel.description}</p>
            </div>

            {hotel.amenities && hotel.amenities.length > 0 && (
              <div className="border-t pt-6 mb-6">
                <h2 className="text-2xl font-bold mb-4">Amenities</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {hotel.amenities.map((amenity, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-gray-700">
                      <Wifi size={18} />
                      <span>{amenity}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {reviews.length > 0 && (
              <div className="border-t pt-6">
                <h2 className="text-2xl font-bold mb-4">Reviews</h2>
                <div className="space-y-4">
                  {reviews.map((review) => (
                    <div key={review.review_id} className="bg-gray-50 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{review.user_name}</span>
                        <div className="flex items-center">
                          <Star className="rating-star" size={16} fill="#FFE66D" />
                          <span className="ml-1">{review.rating}</span>
                        </div>
                      </div>
                      <p className="text-gray-700">{review.comment}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default HotelDetail;