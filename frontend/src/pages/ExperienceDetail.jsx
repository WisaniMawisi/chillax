import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Compass, MapPin, Clock, Star, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

function ExperienceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [experience, setExperience] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExperience();
    fetchReviews();
  }, [id]);

  const fetchExperience = async () => {
    try {
      const response = await axios.get(`${API}/experiences/${id}`);
      setExperience(response.data);
    } catch (error) {
      toast.error('Experience not found');
      navigate('/search');
    } finally {
      setLoading(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const response = await axios.get(`${API}/reviews/experience/${id}`);
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
    navigate(`/booking/experience/${id}`);
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
      <div className="min-h-screen bg-gray-50" data-testid="experience-detail">
        <div className="relative h-96 overflow-hidden">
          <img src={experience.image_url} alt={experience.title} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-20 relative">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
              <div className="flex-1">
                <h1 className="text-4xl font-bold text-gray-900 mb-3">{experience.title}</h1>
                <div className="flex items-center text-gray-600 mb-3">
                  <MapPin size={20} className="mr-2" />
                  <span>{experience.location}, {experience.city}</span>
                </div>
                <div className="flex items-center text-gray-600 mb-4">
                  <Clock size={20} className="mr-2" />
                  <span>Duration: {experience.duration}</span>
                </div>
                {experience.rating > 0 && (
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center bg-[#FFE66D] rounded-lg px-3 py-1">
                      <Star className="rating-star" size={18} fill="#FFE66D" />
                      <span className="ml-1 font-bold">{experience.rating}</span>
                    </div>
                    <span className="text-gray-600">({reviews.length} reviews)</span>
                  </div>
                )}
              </div>
              
              <div className="mt-6 md:mt-0">
                <div className="text-right mb-4">
                  <div className="text-4xl font-bold text-[#FF6B6B]">${experience.price}</div>
                  <div className="text-gray-500">per person</div>
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
              <h2 className="text-2xl font-bold mb-4">About this Experience</h2>
              <p className="text-gray-700">{experience.description}</p>
            </div>

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

export default ExperienceDetail;