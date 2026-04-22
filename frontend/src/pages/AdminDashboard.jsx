import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../App';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Plus, Trash2, Hotel, Plane, Car, Compass } from 'lucide-react';
import { toast } from 'sonner';

function AdminDashboard() {
  const { user } = useAuth();
  const [hotels, setHotels] = useState([]);
  const [flights, setFlights] = useState([]);
  const [cars, setCars] = useState([]);
  const [experiences, setExperiences] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('hotels');

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [hotelsRes, flightsRes, carsRes, experiencesRes, bookingsRes] = await Promise.all([
        axios.get(`${API}/hotels`),
        axios.get(`${API}/flights`),
        axios.get(`${API}/cars`),
        axios.get(`${API}/experiences`),
        axios.get(`${API}/bookings`, { withCredentials: true })
      ]);
      setHotels(hotelsRes.data);
      setFlights(flightsRes.data);
      setCars(carsRes.data);
      setExperiences(experiencesRes.data);
      setBookings(bookingsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;

    try {
      await axios.delete(`${API}/${type}/${id}`, { withCredentials: true });
      toast.success('Item deleted');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to delete item');
    }
  };

  const handleCreate = async (e, type) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    // Convert arrays
    if (data.amenities) data.amenities = data.amenities.split(',').map(a => a.trim());
    if (data.features) data.features = data.features.split(',').map(f => f.trim());
    
    // Convert numbers
    const numberFields = ['price_per_night', 'price_per_day', 'price', 'available_seats'];
    numberFields.forEach(field => {
      if (data[field]) data[field] = parseFloat(data[field]);
    });
    
    // Convert dates
    if (data.departure_time) data.departure_time = new Date(data.departure_time).toISOString();
    if (data.arrival_time) data.arrival_time = new Date(data.arrival_time).toISOString();

    try {
      await axios.post(`${API}/${type}`, data, { withCredentials: true });
      toast.success('Item created');
      setCreateDialogOpen(false);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create item');
    }
  };

  const CreateForm = ({ type }) => {
    if (type === 'hotels') {
      return (
        <form onSubmit={(e) => handleCreate(e, 'hotels')} className="space-y-4">
          <div>
            <Label>Name</Label>
            <Input name="name" required className="mt-1" />
          </div>
          <div>
            <Label>Location</Label>
            <Input name="location" required className="mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>City</Label>
              <Input name="city" required className="mt-1" />
            </div>
            <div>
              <Label>Country</Label>
              <Input name="country" required className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Description</Label>
            <Textarea name="description" required className="mt-1" />
          </div>
          <div>
            <Label>Price per Night</Label>
            <Input name="price_per_night" type="number" step="0.01" required className="mt-1" />
          </div>
          <div>
            <Label>Image URL</Label>
            <Input name="image_url" type="url" required className="mt-1" />
          </div>
          <div>
            <Label>Amenities (comma-separated)</Label>
            <Input name="amenities" placeholder="WiFi, Pool, Gym" className="mt-1" />
          </div>
          <Button type="submit" className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white">Create Hotel</Button>
        </form>
      );
    } else if (type === 'flights') {
      return (
        <form onSubmit={(e) => handleCreate(e, 'flights')} className="space-y-4">
          <div>
            <Label>Airline</Label>
            <Input name="airline" required className="mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>From City</Label>
              <Input name="from_city" required className="mt-1" />
            </div>
            <div>
              <Label>To City</Label>
              <Input name="to_city" required className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Departure Time</Label>
              <Input name="departure_time" type="datetime-local" required className="mt-1" />
            </div>
            <div>
              <Label>Arrival Time</Label>
              <Input name="arrival_time" type="datetime-local" required className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Price</Label>
              <Input name="price" type="number" step="0.01" required className="mt-1" />
            </div>
            <div>
              <Label>Available Seats</Label>
              <Input name="available_seats" type="number" required className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Image URL</Label>
            <Input name="image_url" type="url" required className="mt-1" />
          </div>
          <Button type="submit" className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white">Create Flight</Button>
        </form>
      );
    } else if (type === 'cars') {
      return (
        <form onSubmit={(e) => handleCreate(e, 'cars')} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Brand</Label>
              <Input name="brand" required className="mt-1" />
            </div>
            <div>
              <Label>Model</Label>
              <Input name="model" required className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Location</Label>
              <Input name="location" required className="mt-1" />
            </div>
            <div>
              <Label>City</Label>
              <Input name="city" required className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Price per Day</Label>
            <Input name="price_per_day" type="number" step="0.01" required className="mt-1" />
          </div>
          <div>
            <Label>Image URL</Label>
            <Input name="image_url" type="url" required className="mt-1" />
          </div>
          <div>
            <Label>Features (comma-separated)</Label>
            <Input name="features" placeholder="GPS, AC, Bluetooth" className="mt-1" />
          </div>
          <Button type="submit" className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white">Create Car</Button>
        </form>
      );
    } else if (type === 'experiences') {
      return (
        <form onSubmit={(e) => handleCreate(e, 'experiences')} className="space-y-4">
          <div>
            <Label>Title</Label>
            <Input name="title" required className="mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Location</Label>
              <Input name="location" required className="mt-1" />
            </div>
            <div>
              <Label>City</Label>
              <Input name="city" required className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Description</Label>
            <Textarea name="description" required className="mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Price</Label>
              <Input name="price" type="number" step="0.01" required className="mt-1" />
            </div>
            <div>
              <Label>Duration</Label>
              <Input name="duration" placeholder="2 hours" required className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Image URL</Label>
            <Input name="image_url" type="url" required className="mt-1" />
          </div>
          <Button type="submit" className="w-full bg-[#FF6B6B] hover:bg-[#FF5252] text-white">Create Experience</Button>
        </form>
      );
    }
  };

  const renderItems = (items, type, idField) => {
    return items.map(item => (
      <div key={item[idField]} className="bg-white rounded-xl p-4 border border-gray-200 flex items-center justify-between">
        <div className="flex-1">
          <div className="font-medium">{item.name || item.title || `${item.brand} ${item.model}` || `${item.from_city} to ${item.to_city}`}</div>
          <div className="text-sm text-gray-600">{item.location || item.city || item.from_city}</div>
        </div>
        <Button
          onClick={() => handleDelete(type, item[idField])}
          variant="ghost"
          size="sm"
          className="text-red-600 hover:bg-red-50"
          data-testid="delete-button"
        >
          <Trash2 size={18} />
        </Button>
      </div>
    ));
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-screen">
          <div className="text-xl text-gray-600">Loading dashboard...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 py-12" data-testid="admin-dashboard">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-gray-600 mt-2">Manage your listings and bookings</p>
            </div>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-[#4ECDC4] hover:bg-[#3DBDB5] text-white rounded-full px-6" data-testid="create-listing-button">
                  <Plus size={20} className="mr-2" />
                  Create Listing
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Create New Listing</DialogTitle>
                </DialogHeader>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="hotels">Hotel</TabsTrigger>
                    <TabsTrigger value="flights">Flight</TabsTrigger>
                    <TabsTrigger value="cars">Car</TabsTrigger>
                    <TabsTrigger value="experiences">Experience</TabsTrigger>
                  </TabsList>
                  <TabsContent value="hotels"><CreateForm type="hotels" /></TabsContent>
                  <TabsContent value="flights"><CreateForm type="flights" /></TabsContent>
                  <TabsContent value="cars"><CreateForm type="cars" /></TabsContent>
                  <TabsContent value="experiences"><CreateForm type="experiences" /></TabsContent>
                </Tabs>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <Hotel className="text-[#FF6B6B] mb-2" size={32} />
              <div className="text-3xl font-bold">{hotels.length}</div>
              <div className="text-gray-600">Hotels</div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <Plane className="text-[#4ECDC4] mb-2" size={32} />
              <div className="text-3xl font-bold">{flights.length}</div>
              <div className="text-gray-600">Flights</div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <Car className="text-[#FFE66D] mb-2" size={32} />
              <div className="text-3xl font-bold">{cars.length}</div>
              <div className="text-gray-600">Cars</div>
            </div>
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <Compass className="text-purple-500 mb-2" size={32} />
              <div className="text-3xl font-bold">{experiences.length}</div>
              <div className="text-gray-600">Experiences</div>
            </div>
          </div>

          <Tabs defaultValue="hotels" className="w-full">
            <TabsList className="mb-6">
              <TabsTrigger value="hotels">Hotels ({hotels.length})</TabsTrigger>
              <TabsTrigger value="flights">Flights ({flights.length})</TabsTrigger>
              <TabsTrigger value="cars">Cars ({cars.length})</TabsTrigger>
              <TabsTrigger value="experiences">Experiences ({experiences.length})</TabsTrigger>
              <TabsTrigger value="bookings">Bookings ({bookings.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="hotels">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {renderItems(hotels, 'hotels', 'hotel_id')}
              </div>
            </TabsContent>

            <TabsContent value="flights">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {renderItems(flights, 'flights', 'flight_id')}
              </div>
            </TabsContent>

            <TabsContent value="cars">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {renderItems(cars, 'cars', 'car_id')}
              </div>
            </TabsContent>

            <TabsContent value="experiences">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {renderItems(experiences, 'experiences', 'experience_id')}
              </div>
            </TabsContent>

            <TabsContent value="bookings">
              <div className="bg-white rounded-2xl p-6 shadow-sm">
                <h3 className="text-xl font-bold mb-4">All Bookings</h3>
                <div className="space-y-3">
                  {bookings.map(booking => (
                    <div key={booking.booking_id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-medium">{booking.item_name}</div>
                          <div className="text-sm text-gray-600">Type: {booking.booking_type}</div>
                          <div className="text-sm text-gray-600">User ID: {booking.user_id}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-[#FF6B6B]">${booking.total_price}</div>
                          <div className="text-sm text-gray-600">{booking.status}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </Layout>
  );
}

export default AdminDashboard;