from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import httpx
from jose import jwt, JWTError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ===== MODELS =====

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_admin: bool = False
    created_at: datetime

class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class SessionData(BaseModel):
    session_id: str

class Hotel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hotel_id: str
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float
    rating: float = 0.0
    image_url: str
    amenities: List[str] = []
    available: bool = True
    created_at: datetime

class HotelCreate(BaseModel):
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float
    image_url: str
    amenities: List[str] = []

class Flight(BaseModel):
    model_config = ConfigDict(extra="ignore")
    flight_id: str
    airline: str
    from_city: str
    to_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    available_seats: int
    image_url: str
    created_at: datetime

class FlightCreate(BaseModel):
    airline: str
    from_city: str
    to_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    available_seats: int
    image_url: str

class Car(BaseModel):
    model_config = ConfigDict(extra="ignore")
    car_id: str
    brand: str
    model: str
    location: str
    city: str
    price_per_day: float
    available: bool = True
    image_url: str
    features: List[str] = []
    created_at: datetime

class CarCreate(BaseModel):
    brand: str
    model: str
    location: str
    city: str
    price_per_day: float
    image_url: str
    features: List[str] = []

class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    experience_id: str
    title: str
    location: str
    city: str
    description: str
    price: float
    duration: str
    rating: float = 0.0
    image_url: str
    available: bool = True
    created_at: datetime

class ExperienceCreate(BaseModel):
    title: str
    location: str
    city: str
    description: str
    price: float
    duration: str
    image_url: str

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    booking_id: str
    user_id: str
    booking_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str
    item_name: str
    start_date: datetime
    end_date: Optional[datetime] = None
    total_price: float
    status: Literal["pending", "confirmed", "cancelled"] = "pending"
    payment_status: Literal["pending", "paid", "refunded"] = "pending"
    guests: int = 1
    created_at: datetime

class BookingCreate(BaseModel):
    booking_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    guests: int = 1

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    review_id: str
    user_id: str
    user_name: str
    item_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str
    rating: float
    comment: str
    created_at: datetime

class ReviewCreate(BaseModel):
    item_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str
    rating: float
    comment: str

class Favorite(BaseModel):
    model_config = ConfigDict(extra="ignore")
    favorite_id: str
    user_id: str
    item_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str
    created_at: datetime

class FavoriteCreate(BaseModel):
    item_type: Literal["hotel", "flight", "car", "experience"]
    item_id: str

# ===== AUTH HELPERS =====

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    token = session_token
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check session in database
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

# ===== AUTH ROUTES =====

@api_router.post("/auth/register")
async def register(data: UserRegister):
    # Check if user exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user = User(
        user_id=user_id,
        email=data.email,
        name=data.name,
        password_hash=pwd_context.hash(data.password),
        is_admin=False,
        created_at=datetime.now(timezone.utc)
    )
    
    user_dict = user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    # Create session
    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    response = JSONResponse(content={"user_id": user_id, "email": user.email, "name": user.name, "is_admin": user.is_admin})
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    return response

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user_doc or not user_doc.get('password_hash'):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not pwd_context.verify(data.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_doc['user_id'],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    response = JSONResponse(content={"user_id": user_doc['user_id'], "email": user_doc['email'], "name": user_doc['name'], "is_admin": user_doc.get('is_admin', False)})
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    return response

@api_router.post("/auth/session")
async def exchange_session(data: SessionData, response: Response):
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": data.session_id}
        )
        if res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        oauth_data = res.json()
    
    # Check if user exists
    user_doc = await db.users.find_one({"email": oauth_data['email']}, {"_id": 0})
    
    if user_doc:
        user_id = user_doc['user_id']
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": oauth_data['name'], "picture": oauth_data['picture']}}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = User(
            user_id=user_id,
            email=oauth_data['email'],
            name=oauth_data['name'],
            picture=oauth_data.get('picture'),
            is_admin=False,
            created_at=datetime.now(timezone.utc)
        )
        user_dict = user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        await db.users.insert_one(user_dict)
    
    # Create session
    session_token = oauth_data['session_token']
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Get updated user
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    response = JSONResponse(content={"user_id": user_id, "email": user_doc['email'], "name": user_doc['name'], "picture": user_doc.get('picture'), "is_admin": user_doc.get('is_admin', False)})
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    return response

@api_router.get("/auth/me")
async def get_me(request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    return {"user_id": user.user_id, "email": user.email, "name": user.name, "picture": user.picture, "is_admin": user.is_admin}

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out"}

# ===== HOTEL ROUTES =====

@api_router.post("/hotels", response_model=Hotel)
async def create_hotel(data: HotelCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    hotel_id = f"hotel_{uuid.uuid4().hex[:12]}"
    hotel = Hotel(
        hotel_id=hotel_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    hotel_dict = hotel.model_dump()
    hotel_dict['created_at'] = hotel_dict['created_at'].isoformat()
    await db.hotels.insert_one(hotel_dict)
    return hotel

@api_router.get("/hotels", response_model=List[Hotel])
async def get_hotels(city: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None):
    query = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if min_price is not None:
        query["price_per_night"] = query.get("price_per_night", {})
        query["price_per_night"]["$gte"] = min_price
    if max_price is not None:
        query["price_per_night"] = query.get("price_per_night", {})
        query["price_per_night"]["$lte"] = max_price
    
    hotels = await db.hotels.find(query, {"_id": 0}).to_list(1000)
    for hotel in hotels:
        if isinstance(hotel['created_at'], str):
            hotel['created_at'] = datetime.fromisoformat(hotel['created_at'])
    return hotels

@api_router.get("/hotels/{hotel_id}", response_model=Hotel)
async def get_hotel(hotel_id: str):
    hotel = await db.hotels.find_one({"hotel_id": hotel_id}, {"_id": 0})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    if isinstance(hotel['created_at'], str):
        hotel['created_at'] = datetime.fromisoformat(hotel['created_at'])
    return hotel

@api_router.delete("/hotels/{hotel_id}")
async def delete_hotel(hotel_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.hotels.delete_one({"hotel_id": hotel_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Hotel deleted"}

# ===== FLIGHT ROUTES =====

@api_router.post("/flights", response_model=Flight)
async def create_flight(data: FlightCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    flight_id = f"flight_{uuid.uuid4().hex[:12]}"
    flight = Flight(
        flight_id=flight_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    flight_dict = flight.model_dump()
    flight_dict['departure_time'] = flight_dict['departure_time'].isoformat()
    flight_dict['arrival_time'] = flight_dict['arrival_time'].isoformat()
    flight_dict['created_at'] = flight_dict['created_at'].isoformat()
    await db.flights.insert_one(flight_dict)
    return flight

@api_router.get("/flights", response_model=List[Flight])
async def get_flights(from_city: Optional[str] = None, to_city: Optional[str] = None):
    query = {"available_seats": {"$gt": 0}}
    if from_city:
        query["from_city"] = {"$regex": from_city, "$options": "i"}
    if to_city:
        query["to_city"] = {"$regex": to_city, "$options": "i"}
    
    flights = await db.flights.find(query, {"_id": 0}).to_list(1000)
    for flight in flights:
        if isinstance(flight['departure_time'], str):
            flight['departure_time'] = datetime.fromisoformat(flight['departure_time'])
        if isinstance(flight['arrival_time'], str):
            flight['arrival_time'] = datetime.fromisoformat(flight['arrival_time'])
        if isinstance(flight['created_at'], str):
            flight['created_at'] = datetime.fromisoformat(flight['created_at'])
    return flights

@api_router.get("/flights/{flight_id}", response_model=Flight)
async def get_flight(flight_id: str):
    flight = await db.flights.find_one({"flight_id": flight_id}, {"_id": 0})
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if isinstance(flight['departure_time'], str):
        flight['departure_time'] = datetime.fromisoformat(flight['departure_time'])
    if isinstance(flight['arrival_time'], str):
        flight['arrival_time'] = datetime.fromisoformat(flight['arrival_time'])
    if isinstance(flight['created_at'], str):
        flight['created_at'] = datetime.fromisoformat(flight['created_at'])
    return flight

@api_router.delete("/flights/{flight_id}")
async def delete_flight(flight_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.flights.delete_one({"flight_id": flight_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Flight not found")
    return {"message": "Flight deleted"}

# ===== CAR ROUTES =====

@api_router.post("/cars", response_model=Car)
async def create_car(data: CarCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    car_id = f"car_{uuid.uuid4().hex[:12]}"
    car = Car(
        car_id=car_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    car_dict = car.model_dump()
    car_dict['created_at'] = car_dict['created_at'].isoformat()
    await db.cars.insert_one(car_dict)
    return car

@api_router.get("/cars", response_model=List[Car])
async def get_cars(city: Optional[str] = None):
    query = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    
    cars = await db.cars.find(query, {"_id": 0}).to_list(1000)
    for car in cars:
        if isinstance(car['created_at'], str):
            car['created_at'] = datetime.fromisoformat(car['created_at'])
    return cars

@api_router.get("/cars/{car_id}", response_model=Car)
async def get_car(car_id: str):
    car = await db.cars.find_one({"car_id": car_id}, {"_id": 0})
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    if isinstance(car['created_at'], str):
        car['created_at'] = datetime.fromisoformat(car['created_at'])
    return car

@api_router.delete("/cars/{car_id}")
async def delete_car(car_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.cars.delete_one({"car_id": car_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"message": "Car deleted"}

# ===== EXPERIENCE ROUTES =====

@api_router.post("/experiences", response_model=Experience)
async def create_experience(data: ExperienceCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    experience_id = f"exp_{uuid.uuid4().hex[:12]}"
    experience = Experience(
        experience_id=experience_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    exp_dict = experience.model_dump()
    exp_dict['created_at'] = exp_dict['created_at'].isoformat()
    await db.experiences.insert_one(exp_dict)
    return experience

@api_router.get("/experiences", response_model=List[Experience])
async def get_experiences(city: Optional[str] = None):
    query = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    
    experiences = await db.experiences.find(query, {"_id": 0}).to_list(1000)
    for exp in experiences:
        if isinstance(exp['created_at'], str):
            exp['created_at'] = datetime.fromisoformat(exp['created_at'])
    return experiences

@api_router.get("/experiences/{experience_id}", response_model=Experience)
async def get_experience(experience_id: str):
    experience = await db.experiences.find_one({"experience_id": experience_id}, {"_id": 0})
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    if isinstance(experience['created_at'], str):
        experience['created_at'] = datetime.fromisoformat(experience['created_at'])
    return experience

@api_router.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.experiences.delete_one({"experience_id": experience_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Experience not found")
    return {"message": "Experience deleted"}

# ===== BOOKING ROUTES =====

@api_router.post("/bookings", response_model=Booking)
async def create_booking(data: BookingCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    # Get item details
    item_name = ""
    total_price = 0.0
    
    if data.booking_type == "hotel":
        item = await db.hotels.find_one({"hotel_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Hotel not found")
        item_name = item['name']
        days = (data.end_date - data.start_date).days if data.end_date else 1
        total_price = item['price_per_night'] * days
    elif data.booking_type == "flight":
        item = await db.flights.find_one({"flight_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Flight not found")
        item_name = f"{item['from_city']} to {item['to_city']}"
        total_price = item['price'] * data.guests
    elif data.booking_type == "car":
        item = await db.cars.find_one({"car_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Car not found")
        item_name = f"{item['brand']} {item['model']}"
        days = (data.end_date - data.start_date).days if data.end_date else 1
        total_price = item['price_per_day'] * days
    elif data.booking_type == "experience":
        item = await db.experiences.find_one({"experience_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Experience not found")
        item_name = item['title']
        total_price = item['price'] * data.guests
    
    booking_id = f"booking_{uuid.uuid4().hex[:12]}"
    booking = Booking(
        booking_id=booking_id,
        user_id=user.user_id,
        item_name=item_name,
        total_price=total_price,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    booking_dict = booking.model_dump()
    booking_dict['start_date'] = booking_dict['start_date'].isoformat()
    if booking_dict.get('end_date'):
        booking_dict['end_date'] = booking_dict['end_date'].isoformat()
    booking_dict['created_at'] = booking_dict['created_at'].isoformat()
    await db.bookings.insert_one(booking_dict)
    return booking

@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    query = {"user_id": user.user_id} if not user.is_admin else {}
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(1000)
    
    for booking in bookings:
        if isinstance(booking['start_date'], str):
            booking['start_date'] = datetime.fromisoformat(booking['start_date'])
        if booking.get('end_date') and isinstance(booking['end_date'], str):
            booking['end_date'] = datetime.fromisoformat(booking['end_date'])
        if isinstance(booking['created_at'], str):
            booking['created_at'] = datetime.fromisoformat(booking['created_at'])
    return bookings

@api_router.patch("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking['user_id'] != user.user_id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.bookings.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "cancelled"}}
    )
    return {"message": "Booking cancelled"}

# ===== REVIEW ROUTES =====

@api_router.post("/reviews", response_model=Review)
async def create_review(data: ReviewCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    review_id = f"review_{uuid.uuid4().hex[:12]}"
    review = Review(
        review_id=review_id,
        user_id=user.user_id,
        user_name=user.name,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    review_dict = review.model_dump()
    review_dict['created_at'] = review_dict['created_at'].isoformat()
    await db.reviews.insert_one(review_dict)
    
    # Update item rating
    collection_map = {"hotel": "hotels", "flight": "flights", "car": "cars", "experience": "experiences"}
    collection = db[collection_map[data.item_type]]
    
    # Calculate average rating
    reviews = await db.reviews.find({"item_type": data.item_type, "item_id": data.item_id}, {"_id": 0}).to_list(1000)
    avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0.0
    
    id_field = f"{data.item_type}_id"
    await collection.update_one({id_field: data.item_id}, {"$set": {"rating": round(avg_rating, 1)}})
    
    return review

@api_router.get("/reviews/{item_type}/{item_id}", response_model=List[Review])
async def get_reviews(item_type: str, item_id: str):
    reviews = await db.reviews.find({"item_type": item_type, "item_id": item_id}, {"_id": 0}).to_list(1000)
    for review in reviews:
        if isinstance(review['created_at'], str):
            review['created_at'] = datetime.fromisoformat(review['created_at'])
    return reviews

# ===== FAVORITE ROUTES =====

@api_router.post("/favorites", response_model=Favorite)
async def add_favorite(data: FavoriteCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    # Check if already favorited
    existing = await db.favorites.find_one({"user_id": user.user_id, "item_type": data.item_type, "item_id": data.item_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")
    
    favorite_id = f"fav_{uuid.uuid4().hex[:12]}"
    favorite = Favorite(
        favorite_id=favorite_id,
        user_id=user.user_id,
        **data.model_dump(),
        created_at=datetime.now(timezone.utc)
    )
    
    fav_dict = favorite.model_dump()
    fav_dict['created_at'] = fav_dict['created_at'].isoformat()
    await db.favorites.insert_one(fav_dict)
    return favorite

@api_router.get("/favorites", response_model=List[Favorite])
async def get_favorites(request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    favorites = await db.favorites.find({"user_id": user.user_id}, {"_id": 0}).to_list(1000)
    for fav in favorites:
        if isinstance(fav['created_at'], str):
            fav['created_at'] = datetime.fromisoformat(fav['created_at'])
    return favorites

@api_router.delete("/favorites/{favorite_id}")
async def remove_favorite(favorite_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    
    result = await db.favorites.delete_one({"favorite_id": favorite_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Removed from favorites"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()