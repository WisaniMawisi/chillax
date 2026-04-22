import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Search, MapPin, Calendar, Users, Star, Plane, Car, Compass } from 'lucide-react';

function Landing() {
  const navigate = useNavigate();
  const [searchType, setSearchType] = useState('hotels');
  const [location, setLocation] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState(1);

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams({
      type: searchType,
      location,
      checkIn,
      checkOut,
      guests: guests.toString()
    });
    navigate(`/search?${params.toString()}`);
  };

  return (
    <Layout>
      {/* Hero Section */}
      <div className="hero-section relative" data-testid="hero-section">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: 'url(https://images.unsplash.com/photo-1731080647322-f9cf691d40ab?crop=entropy&cs=srgb&fm=jpg&q=85)' }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-[#FF6B6B]/90 to-[#FF8E53]/90"></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32">
          <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">
              Travel. Explore. Chillax.
            </h1>
            <p className="text-base sm:text-lg lg:text-xl opacity-90 max-w-2xl mx-auto">
              Book hotels, flights, car rentals, and unique experiences all in one place
            </p>
          </div>

          {/* Search Box */}
          <div className="search-box max-w-5xl mx-auto p-6 rounded-2xl" data-testid="search-box">
            {/* Search Type Tabs */}
            <div className="flex flex-wrap gap-3 mb-6">
              <Button
                onClick={() => setSearchType('hotels')}
                className={`rounded-full px-6 py-2 font-medium transition-colors ${
                  searchType === 'hotels'
                    ? 'bg-[#FF6B6B] text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                data-testid="search-type-hotels"
              >
                <MapPin size={18} className="mr-2" />
                Hotels
              </Button>
              <Button
                onClick={() => setSearchType('flights')}
                className={`rounded-full px-6 py-2 font-medium transition-colors ${
                  searchType === 'flights'
                    ? 'bg-[#FF6B6B] text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                data-testid="search-type-flights"
              >
                <Plane size={18} className="mr-2" />
                Flights
              </Button>
              <Button
                onClick={() => setSearchType('cars')}
                className={`rounded-full px-6 py-2 font-medium transition-colors ${
                  searchType === 'cars'
                    ? 'bg-[#FF6B6B] text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                data-testid="search-type-cars"
              >
                <Car size={18} className="mr-2" />
                Cars
              </Button>
              <Button
                onClick={() => setSearchType('experiences')}
                className={`rounded-full px-6 py-2 font-medium transition-colors ${
                  searchType === 'experiences'
                    ? 'bg-[#FF6B6B] text-white shadow-lg'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                data-testid="search-type-experiences"
              >
                <Compass size={18} className="mr-2" />
                Experiences
              </Button>
            </div>

            {/* Search Form */}
            <form onSubmit={handleSearch} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-1">
                <Label htmlFor="location" className="text-gray-700 font-medium mb-2 block">
                  Location
                </Label>
                <Input
                  id="location"
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Where to?"
                  className="bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                  required
                  data-testid="location-input"
                />
              </div>

              <div>
                <Label htmlFor="checkin" className="text-gray-700 font-medium mb-2 block">
                  {searchType === 'flights' ? 'Departure' : 'Check-in'}
                </Label>
                <Input
                  id="checkin"
                  type="date"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className="bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                  required
                  data-testid="checkin-input"
                />
              </div>

              {searchType !== 'experiences' && (
                <div>
                  <Label htmlFor="checkout" className="text-gray-700 font-medium mb-2 block">
                    {searchType === 'flights' ? 'Return' : 'Check-out'}
                  </Label>
                  <Input
                    id="checkout"
                    type="date"
                    value={checkOut}
                    onChange={(e) => setCheckOut(e.target.value)}
                    className="bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                    data-testid="checkout-input"
                  />
                </div>
              )}

              <div className={searchType === 'experiences' ? 'md:col-span-2' : ''}>
                <Label htmlFor="guests" className="text-gray-700 font-medium mb-2 block">
                  {searchType === 'flights' ? 'Passengers' : 'Guests'}
                </Label>
                <Input
                  id="guests"
                  type="number"
                  min="1"
                  value={guests}
                  onChange={(e) => setGuests(parseInt(e.target.value))}
                  className="bg-gray-50 border-transparent focus:border-[#FF6B6B] focus:ring-2 focus:ring-[#FF6B6B]/20 rounded-xl"
                  data-testid="guests-input"
                />
              </div>

              <div className="md:col-span-4">
                <Button
                  type="submit"
                  className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white rounded-full py-6 text-lg font-semibold transition-transform hover:scale-105 active:scale-95 shadow-lg shadow-orange-200\"
                  data-testid="search-submit-button"
                >
                  <Search size={20} className="mr-2" />
                  Search
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Categories Section */}
      <div className="py-16 bg-gray-50" data-testid="categories-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12 text-gray-900">
            Explore by Category
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { type: 'hotels', title: 'Hotels', icon: MapPin, img: 'https://images.unsplash.com/photo-1731080647322-f9cf691d40ab?crop=entropy&cs=srgb&fm=jpg&q=85' },
              { type: 'flights', title: 'Flights', icon: Plane, img: 'https://images.unsplash.com/photo-1710028267880-f34d75a5ead6?crop=entropy&cs=srgb&fm=jpg&q=85' },
              { type: 'cars', title: 'Car Rentals', icon: Car, img: 'https://images.unsplash.com/photo-1760162754961-ed27f26b394f?crop=entropy&cs=srgb&fm=jpg&q=85' },
              { type: 'experiences', title: 'Experiences', icon: Compass, img: 'https://images.unsplash.com/photo-1539576776193-2c07122e5fee?crop=entropy&cs=srgb&fm=jpg&q=85' }
            ].map((category) => (
              <div
                key={category.type}
                onClick={() => {
                  setSearchType(category.type);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className="category-card group cursor-pointer"
                data-testid={`category-${category.type}`}
              >
                <div className="relative h-64 overflow-hidden rounded-2xl">
                  <img
                    src={category.img}
                    alt={category.title}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                  <div className="absolute bottom-0 left-0 right-0 p-6">
                    <category.icon className="text-white mb-2" size={28} />
                    <h3 className="text-2xl font-bold text-white">{category.title}</h3>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 bg-white" data-testid="features-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12 text-gray-900">
            Why Chillax?
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8\">
            <div className="text-center p-8 rounded-2xl bg-gray-50 hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-[#FF6B6B] rounded-full flex items-center justify-center mx-auto mb-4">
                <Star className="text-white" size={28} />
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">Best Prices</h3>
              <p className="text-gray-600\">
                Find the best deals on hotels, flights, and more. We compare prices so you don't have to.
              </p>
            </div>

            <div className="text-center p-8 rounded-2xl bg-gray-50 hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-[#4ECDC4] rounded-full flex items-center justify-center mx-auto mb-4">
                <MapPin className="text-white" size={28} />
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">Global Coverage</h3>
              <p className="text-gray-600">
                Access millions of properties, flights, and experiences worldwide.
              </p>
            </div>

            <div className="text-center p-8 rounded-2xl bg-gray-50 hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-[#FFE66D] rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="text-gray-900" size={28} />
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">24/7 Support</h3>
              <p className="text-gray-600">
                Our team is here to help you anytime, anywhere. Travel with confidence.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Landing;
