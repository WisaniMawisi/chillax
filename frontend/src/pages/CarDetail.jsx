import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Car as CarIcon, MapPin, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

function CarDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [car, setCar] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCar();
  }, [id]);

  const fetchCar = async () => {
    try {
      const response = await axios.get(`${API}/cars/${id}`);
      setCar(response.data);
    } catch (error) {
      toast.error('Car not found');
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
    navigate(`/booking/car/${id}`);
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
      <div className="min-h-screen bg-gray-50" data-testid="car-detail">
        <div className="relative h-96 overflow-hidden">
          <img src={car.image_url} alt={`${car.brand} ${car.model}`} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        </div>

        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 -mt-20 relative">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
              <div className="flex-1">
                <h1 className="text-4xl font-bold text-gray-900 mb-3">{car.brand} {car.model}</h1>
                <div className="flex items-center text-gray-600 mb-4">
                  <MapPin size={20} className="mr-2" />
                  <span>{car.location}, {car.city}</span>
                </div>
              </div>
              
              <div className="mt-6 md:mt-0">
                <div className="text-right mb-4">
                  <div className="text-4xl font-bold text-[#FF6B6B]">${car.price_per_day}</div>
                  <div className="text-gray-500">per day</div>
                </div>
                <Button
                  onClick={handleBook}
                  className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full px-8 py-6 text-lg font-semibold shadow-lg"
                  data-testid="book-button"
                >
                  Rent Now
                </Button>
              </div>
            </div>

            {car.features && car.features.length > 0 && (
              <div className="border-t pt-6">
                <h2 className="text-2xl font-bold mb-4">Features</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {car.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-gray-700">
                      <CarIcon size={18} />
                      <span>{feature}</span>
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

export default CarDetail;