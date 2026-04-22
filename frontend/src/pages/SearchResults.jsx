import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Star, MapPin, DollarSign, Plane, Car, Compass } from 'lucide-react';
import { toast } from 'sonner';

function SearchResults() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const type = searchParams.get('type') || 'hotels';
  const location = searchParams.get('location') || '';

  useEffect(() => {
    fetchResults();
  }, [searchParams]);

  const fetchResults = async () => {
    setLoading(true);
    try {
      let url = '';
      const params = {};
      
      if (type === 'hotels') {
        url = `${API}/hotels`;
        if (location) params.city = location;
      } else if (type === 'flights') {
        url = `${API}/flights`;
        if (location) params.to_city = location;
      } else if (type === 'cars') {
        url = `${API}/cars`;
        if (location) params.city = location;
      } else if (type === 'experiences') {
        url = `${API}/experiences`;
        if (location) params.city = location;
      }
      
      const response = await axios.get(url, { params });
      setResults(response.data);
    } catch (error) {
      toast.error('Failed to fetch results');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleItemClick = (item) => {
    const id = item[`${type.slice(0, -1)}_id`] || item[`${type}_id`];
    navigate(`/${type}/${id}`);
  };

  const getIcon = () => {
    switch (type) {
      case 'hotels': return MapPin;
      case 'flights': return Plane;
      case 'cars': return Car;
      case 'experiences': return Compass;
      default: return MapPin;
    }
  };

  const Icon = getIcon();

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50" data-testid="search-results">
        <div className="bg-[#FF6B6B] text-white py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center space-x-3">
              <Icon size={32} />
              <div>
                <h1 className="text-3xl font-bold capitalize">{type}</h1>
                <p className="text-sm opacity-90">in {location || 'all locations'}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {loading ? (
            <div className="flex justify-center py-20">
              <div className="text-xl text-gray-600">Loading results...</div>
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-20">
              <Icon size={64} className="mx-auto text-gray-300 mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">No results found</h2>
              <p className="text-gray-600">Try searching for a different location</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {results.map((item) => {
                const id = item[`${type.slice(0, -1)}_id`] || item[`${type}_id`];
                return (
                  <div
                    key={id}
                    onClick={() => handleItemClick(item)}
                    className="booking-card bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl cursor-pointer overflow-hidden"
                    data-testid={`result-item-${id}`}
                  >
                    <div className="relative h-48 overflow-hidden">
                      <img
                        src={item.image_url}
                        alt={item.name || item.title}
                        className="w-full h-full object-cover"
                      />
                      {item.rating > 0 && (
                        <div className="absolute top-4 right-4 bg-white rounded-full px-3 py-1 flex items-center space-x-1 shadow-lg">
                          <Star className="rating-star" size={16} fill="#FFE66D" />
                          <span className="text-sm font-bold">{item.rating}</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="p-5">
                      <h3 className="text-xl font-bold text-gray-900 mb-2">
                        {item.name || item.title || `${item.brand} ${item.model}` || `${item.from_city} to ${item.to_city}`}
                      </h3>
                      
                      <div className="flex items-center text-gray-600 mb-3">
                        <MapPin size={16} className="mr-1" />
                        <span className="text-sm">
                          {item.location || item.city || item.from_city}
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center text-[#FF6B6B] font-bold text-xl">
                          <DollarSign size={20} />
                          <span>
                            {item.price_per_night || item.price || item.price_per_day || 0}
                          </span>
                          {(item.price_per_night || item.price_per_day) && (
                            <span className="text-sm text-gray-500 font-normal ml-1">
                              {item.price_per_night ? '/night' : '/day'}
                            </span>
                          )}
                        </div>
                        <Button className="bg-[#4ECDC4] hover:bg-[#3DBDB5] text-white rounded-full px-6">
                          View
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default SearchResults;