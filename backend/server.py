"""Chillax Travel — FastAPI backend.

All routes are prefixed with /api. Structured to match the Gigs
Marketplace backend: JWT access/refresh tokens via auth_utils,
Depends()-based auth instead of manually threading a session token
through every route, and a permissive CORS fallback when no explicit
origins are configured.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

<<<<<<< HEAD
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict

from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, extract_token,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("chillax")

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]
=======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="Chillax Travel API")
api = APIRouter(prefix="/api")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Pydantic models
# ============================================================

BookingType = Literal["hotel", "flight", "car", "experience"]


class UserRegister(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str


class SessionData(BaseModel):
    session_id: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    is_admin: bool = False

    model_config = ConfigDict(extra="ignore")


class Hotel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hotel_id: str
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float
<<<<<<< HEAD
    total_rooms: int = 1
=======
    total_rooms: int = 1  # FIX: this field was missing, so availability checks always assumed 1 room
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    rating: float = 0.0
    image_url: str
    amenities: List[str] = []
    available: bool = True
    created_at: str


class HotelCreate(BaseModel):
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float
<<<<<<< HEAD
    total_rooms: int = 1
=======
    total_rooms: int = 1  # FIX: allow admin to set real room inventory
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    image_url: str
    amenities: List[str] = []


class Flight(BaseModel):
    model_config = ConfigDict(extra="ignore")
    flight_id: str
    airline: str
    from_city: str
    to_city: str
    departure_time: str
    arrival_time: str
    price: float
    available_seats: int
    image_url: str
    created_at: str


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
<<<<<<< HEAD
    total_cars: int = 1
=======
    total_cars: int = 1  # FIX: needed for the same overlap-checking logic as hotels
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    available: bool = True
    image_url: str
    features: List[str] = []
    created_at: str


class CarCreate(BaseModel):
    brand: str
    model: str
    location: str
    city: str
    price_per_day: float
    total_cars: int = 1
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
    created_at: str


class ExperienceCreate(BaseModel):
    title: str
    location: str
    city: str
    description: str
    price: float
    duration: str
    image_url: str


class BookingCreate(BaseModel):
    booking_type: BookingType
    item_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    guests: int = 1


class ReviewCreate(BaseModel):
    item_type: BookingType
    item_id: str
    rating: float
    comment: str


class FavoriteCreate(BaseModel):
    item_type: BookingType
    item_id: str


# ============================================================
# Auth helpers
# ============================================================

<<<<<<< HEAD
async def get_user_or_none(request: Request) -> Optional[dict]:
    token = extract_token(request)
=======

# ===== AUTH HELPERS =====

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    token = session_token
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user = await db.users.find_one({"user_id": payload["sub"]})
        if user:
            user.pop("password_hash", None)
            user.pop("_id", None)
        return user
    except Exception:
        return None


async def require_user(request: Request) -> dict:
    user = await get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
<<<<<<< HEAD
    return user


async def require_admin(request: Request) -> dict:
    user = await require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def public_user(user: dict) -> dict:
    return {
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "is_admin": user.get("is_admin", False),
    }


def _set_auth_cookies(response: Response, access: str, refresh: str):
    """Bearer-token auth (returned in the JSON body) is the primary path —
    the frontend should store the token and send
    'Authorization: Bearer <token>'. Cookies are kept as a fallback.
    Cross-site cookies with samesite=none require BOTH frontend and
    backend to be served over HTTPS, which is the recurring cause of
    silent 401s across your other projects (TaxApp, The Gigs)."""
    response.set_cookie(
        key="access_token", value=access, httponly=True, secure=True,
        samesite="none", max_age=60 * 60 * 24, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=refresh, httponly=True, secure=True,
        samesite="none", max_age=60 * 60 * 24 * 30, path="/",
    )


# ============================================================
# Auth routes
# ============================================================

@api.post("/auth/register")
async def register(payload: UserRegister, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
=======

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])

    return User(**user_doc)


def _set_session_cookie(response: JSONResponse, session_token: str):
    """Cookie is kept as a fallback, but the token is also returned in the JSON
    body (see callers) so the frontend can store it and send it as
    'Authorization: Bearer <token>' instead. Cross-site cookies with
    samesite=none require BOTH frontend and backend to be served over HTTPS,
    which is the recurring cause of silent 401s across your other projects
    (TaxApp, The Gigs) — Bearer-token auth avoids that entirely."""
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )

# ===== AUTH ROUTES =====

@api_router.post("/auth/register")
async def register(data: UserRegister):
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

    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
        "user_id": user_id,
        "email": email,
        "name": payload.name,
        "picture": None,
        "password_hash": hash_password(payload.password),
        "is_admin": False,
        "created_at": now_iso(),
    }
<<<<<<< HEAD
    await db.users.insert_one(doc)

    access = create_access_token(user_id, email, is_admin=False)
    refresh = create_refresh_token(user_id)
    _set_auth_cookies(response, access, refresh)
=======
    await db.user_sessions.insert_one(session_doc)

    response = JSONResponse(content={
        "user_id": user_id, "email": user.email, "name": user.name,
        "is_admin": user.is_admin, "session_token": session_token  # FIX: expose token for Bearer-auth frontends
    })
    _set_session_cookie(response, session_token)
    return response

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user_doc or not user_doc.get('password_hash'):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(data.password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_token = f"session_{uuid.uuid4().hex}"
    session_doc = {
        "user_id": user_doc['user_id'],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)

    response = JSONResponse(content={
        "user_id": user_doc['user_id'], "email": user_doc['email'], "name": user_doc['name'],
        "is_admin": user_doc.get('is_admin', False), "session_token": session_token
    })
    _set_session_cookie(response, session_token)
    return response
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

    return {"user": public_user(doc), "access_token": access}


@api.post("/auth/login")
async def login(payload: UserLogin, response: Response):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user["user_id"], email, is_admin=user.get("is_admin", False))
    refresh = create_refresh_token(user["user_id"])
    _set_auth_cookies(response, access, refresh)

    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"user": public_user(user), "access_token": access}


@api.post("/auth/session")
async def exchange_session(payload: SessionData, response: Response):
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    async with httpx.AsyncClient() as http_client:
        res = await http_client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": payload.session_id},
        )
        if res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
<<<<<<< HEAD
        oauth_data = res.json()

    email = oauth_data["email"]
    user = await db.users.find_one({"email": email})

    if user:
        user_id = user["user_id"]
=======

        oauth_data = res.json()

    user_doc = await db.users.find_one({"email": oauth_data['email']}, {"_id": 0})

    if user_doc:
        user_id = user_doc['user_id']
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": oauth_data["name"], "picture": oauth_data.get("picture")}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
<<<<<<< HEAD
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": oauth_data["name"],
            "picture": oauth_data.get("picture"),
            "password_hash": None,
            "is_admin": False,
            "created_at": now_iso(),
        })
=======
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

    session_token = oauth_data['session_token']
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})

    response = JSONResponse(content={
        "user_id": user_id, "email": user_doc['email'], "name": user_doc['name'],
        "picture": user_doc.get('picture'), "is_admin": user_doc.get('is_admin', False),
        "session_token": session_token
    })
    _set_session_cookie(response, session_token)
    return response
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

    user = await db.users.find_one({"user_id": user_id})
    user.pop("password_hash", None)
    user.pop("_id", None)

    # Issue our own JWT pair rather than relying on the external OAuth
    # session token, so every subsequent request is validated the same
    # way regardless of how the user originally signed in.
    access = create_access_token(user_id, email, is_admin=user.get("is_admin", False))
    refresh = create_refresh_token(user_id)
    _set_auth_cookies(response, access, refresh)

    return {"user": public_user(user), "access_token": access}


@api.get("/auth/me")
async def auth_me(user: dict = Depends(require_user)):
    return {"user": public_user(user)}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


<<<<<<< HEAD
# ============================================================
# Hotels
# ============================================================

@api.post("/hotels", response_model=Hotel)
async def create_hotel(payload: HotelCreate, admin: dict = Depends(require_admin)):
    hotel_id = f"hotel_{uuid.uuid4().hex[:12]}"
    doc = {
        "hotel_id": hotel_id,
        **payload.model_dump(),
        "rating": 0.0,
        "available": True,
        "created_at": now_iso(),
    }
    await db.hotels.insert_one(doc)
    doc.pop("_id", None)
    return doc
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/hotels", response_model=List[Hotel])
async def get_hotels(city: Optional[str] = None, min_price: Optional[float] = None,
                     max_price: Optional[float] = None):
    query: dict = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
<<<<<<< HEAD
    if min_price is not None or max_price is not None:
        price_q: dict = {}
        if min_price is not None:
            price_q["$gte"] = min_price
        if max_price is not None:
            price_q["$lte"] = max_price
        query["price_per_night"] = price_q
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

    cursor = db.hotels.find(query, {"_id": 0})
    return [h async for h in cursor]


@api.get("/hotels/{hotel_id}", response_model=Hotel)
async def get_hotel(hotel_id: str):
    hotel = await db.hotels.find_one({"hotel_id": hotel_id}, {"_id": 0})
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return hotel

<<<<<<< HEAD

@api.delete("/hotels/{hotel_id}")
async def delete_hotel(hotel_id: str, admin: dict = Depends(require_admin)):
=======
@api_router.delete("/hotels/{hotel_id}")
async def delete_hotel(hotel_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    result = await db.hotels.delete_one({"hotel_id": hotel_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"message": "Hotel deleted"}


<<<<<<< HEAD
# ============================================================
# Flights
# ============================================================

@api.post("/flights", response_model=Flight)
async def create_flight(payload: FlightCreate, admin: dict = Depends(require_admin)):
    flight_id = f"flight_{uuid.uuid4().hex[:12]}"
    doc = payload.model_dump()
    doc["departure_time"] = doc["departure_time"].isoformat()
    doc["arrival_time"] = doc["arrival_time"].isoformat()
    doc = {"flight_id": flight_id, **doc, "created_at": now_iso()}
    await db.flights.insert_one(doc)
    doc.pop("_id", None)
    return doc
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/flights", response_model=List[Flight])
async def get_flights(from_city: Optional[str] = None, to_city: Optional[str] = None):
    query: dict = {"available_seats": {"$gt": 0}}
    if from_city:
        query["from_city"] = {"$regex": from_city, "$options": "i"}
    if to_city:
        query["to_city"] = {"$regex": to_city, "$options": "i"}
<<<<<<< HEAD
    cursor = db.flights.find(query, {"_id": 0})
    return [f async for f in cursor]
=======

    flights = await db.flights.find(query, {"_id": 0}).to_list(1000)
    for flight in flights:
        if isinstance(flight['departure_time'], str):
            flight['departure_time'] = datetime.fromisoformat(flight['departure_time'])
        if isinstance(flight['arrival_time'], str):
            flight['arrival_time'] = datetime.fromisoformat(flight['arrival_time'])
        if isinstance(flight['created_at'], str):
            flight['created_at'] = datetime.fromisoformat(flight['created_at'])
    return flights
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/flights/{flight_id}", response_model=Flight)
async def get_flight(flight_id: str):
    flight = await db.flights.find_one({"flight_id": flight_id}, {"_id": 0})
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight

<<<<<<< HEAD

@api.delete("/flights/{flight_id}")
async def delete_flight(flight_id: str, admin: dict = Depends(require_admin)):
=======
@api_router.delete("/flights/{flight_id}")
async def delete_flight(flight_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    result = await db.flights.delete_one({"flight_id": flight_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Flight not found")
    return {"message": "Flight deleted"}


<<<<<<< HEAD
# ============================================================
# Cars
# ============================================================

@api.post("/cars", response_model=Car)
async def create_car(payload: CarCreate, admin: dict = Depends(require_admin)):
    car_id = f"car_{uuid.uuid4().hex[:12]}"
    doc = {"car_id": car_id, **payload.model_dump(), "available": True, "created_at": now_iso()}
    await db.cars.insert_one(doc)
    doc.pop("_id", None)
    return doc
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/cars", response_model=List[Car])
async def get_cars(city: Optional[str] = None):
    query: dict = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
<<<<<<< HEAD
    cursor = db.cars.find(query, {"_id": 0})
    return [c async for c in cursor]
=======

    cars = await db.cars.find(query, {"_id": 0}).to_list(1000)
    for car in cars:
        if isinstance(car['created_at'], str):
            car['created_at'] = datetime.fromisoformat(car['created_at'])
    return cars
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/cars/{car_id}", response_model=Car)
async def get_car(car_id: str):
    car = await db.cars.find_one({"car_id": car_id}, {"_id": 0})
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car

<<<<<<< HEAD

@api.delete("/cars/{car_id}")
async def delete_car(car_id: str, admin: dict = Depends(require_admin)):
=======
@api_router.delete("/cars/{car_id}")
async def delete_car(car_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    result = await db.cars.delete_one({"car_id": car_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"message": "Car deleted"}


<<<<<<< HEAD
# ============================================================
# Experiences
# ============================================================

@api.post("/experiences", response_model=Experience)
async def create_experience(payload: ExperienceCreate, admin: dict = Depends(require_admin)):
    experience_id = f"exp_{uuid.uuid4().hex[:12]}"
    doc = {"experience_id": experience_id, **payload.model_dump(), "rating": 0.0,
           "available": True, "created_at": now_iso()}
    await db.experiences.insert_one(doc)
    doc.pop("_id", None)
    return doc
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/experiences", response_model=List[Experience])
async def get_experiences(city: Optional[str] = None):
    query: dict = {"available": True}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
<<<<<<< HEAD
    cursor = db.experiences.find(query, {"_id": 0})
    return [e async for e in cursor]
=======

    experiences = await db.experiences.find(query, {"_id": 0}).to_list(1000)
    for exp in experiences:
        if isinstance(exp['created_at'], str):
            exp['created_at'] = datetime.fromisoformat(exp['created_at'])
    return experiences
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add


@api.get("/experiences/{experience_id}", response_model=Experience)
async def get_experience(experience_id: str):
    experience = await db.experiences.find_one({"experience_id": experience_id}, {"_id": 0})
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    return experience

<<<<<<< HEAD

@api.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: str, admin: dict = Depends(require_admin)):
=======
@api_router.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    result = await db.experiences.delete_one({"experience_id": experience_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Experience not found")
    return {"message": "Experience deleted"}


<<<<<<< HEAD
# ============================================================
# Bookings
# ============================================================

async def _overlap_count(item_id: str, booking_type: str, start_iso: str, end_iso: str) -> int:
    """Dates are stored as ISO strings (see now_iso()/isoformat() usage
    throughout), so the overlap check must query with the same ISO-string
    representation — comparing a BSON date to a string field never
    matches, which previously let every item get overbooked."""
    existing = await db.bookings.find({
=======
async def _check_overlap_and_get_capacity(collection, id_field: str, item_id: str,
                                           booking_type: str, capacity_field: str,
                                           start_date: datetime, end_date: datetime) -> int:
    """FIX: dates are stored in Mongo as ISO strings (see *_dict['created_at'] = ...isoformat()
    pattern used everywhere in this file), but the old code queried using raw datetime
    objects. Comparing a BSON date to a string field never matches, so the overlap
    check silently always returned zero results -> unlimited overbooking. We now
    query using the same ISO-string representation that's actually stored."""
    item = await collection.find_one({id_field: item_id}, {"_id": 0})
    if not item:
        return -1  # signal "not found" to caller

    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    existing_bookings = await db.bookings.find({
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
        "item_id": item_id,
        "booking_type": booking_type,
        "status": {"$ne": "cancelled"},
        "start_date": {"$lte": end_iso},
<<<<<<< HEAD
        "end_date": {"$gte": start_iso},
    }).to_list(1000)
    return len(existing)


@api.post("/bookings")
async def create_booking(payload: BookingCreate, user: dict = Depends(require_user)):
    item_name = ""
    total_price = 0.0
=======
        "end_date": {"$gte": start_iso}
    }).to_list(1000)

    booked_count = len(existing_bookings)
    capacity = item.get(capacity_field, 1)
    return capacity - booked_count  # remaining units; item is attached by caller separately


@api_router.post("/bookings", response_model=Booking)
async def create_booking(data: BookingCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)

    item_name = ""
    total_price = 0.0

    if data.booking_type == "hotel":
        if not data.end_date:
            raise HTTPException(status_code=400, detail="end_date is required for hotel bookings")
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

    if payload.booking_type == "hotel":
        if not payload.end_date:
            raise HTTPException(status_code=400, detail="end_date is required for hotel bookings")
        item = await db.hotels.find_one({"hotel_id": payload.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Hotel not found")
<<<<<<< HEAD
=======

        start_iso = data.start_date.isoformat()
        end_iso = data.end_date.isoformat()
        existing_bookings = await db.bookings.find({
            "item_id": data.item_id,
            "booking_type": "hotel",
            "status": {"$ne": "cancelled"},
            "start_date": {"$lte": end_iso},
            "end_date": {"$gte": start_iso}
        }).to_list(1000)
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

        booked = await _overlap_count(payload.item_id, "hotel",
                                       payload.start_date.isoformat(), payload.end_date.isoformat())
        if booked >= item.get("total_rooms", 1):
            raise HTTPException(status_code=400, detail="No rooms available for selected dates")

<<<<<<< HEAD
        item_name = item["name"]
        days = max((payload.end_date - payload.start_date).days, 1)
        total_price = item["price_per_night"] * days

    elif payload.booking_type == "flight":
        item = await db.flights.find_one({"flight_id": payload.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Flight not found")
        if item.get("available_seats", 0) < payload.guests:
            raise HTTPException(status_code=400, detail="Not enough seats available")
        item_name = f"{item['from_city']} to {item['to_city']}"
        total_price = item["price"] * payload.guests

    elif payload.booking_type == "car":
        if not payload.end_date:
            raise HTTPException(status_code=400, detail="end_date is required for car bookings")
        item = await db.cars.find_one({"car_id": payload.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Car not found")

        booked = await _overlap_count(payload.item_id, "car",
                                       payload.start_date.isoformat(), payload.end_date.isoformat())
        if booked >= item.get("total_cars", 1):
            raise HTTPException(status_code=400, detail="No cars available for selected dates")

        item_name = f"{item['brand']} {item['model']}"
        days = max((payload.end_date - payload.start_date).days, 1)
        total_price = item["price_per_day"] * days

    elif payload.booking_type == "experience":
        item = await db.experiences.find_one({"experience_id": payload.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Experience not found")
        item_name = item["title"]
        total_price = item["price"] * payload.guests

    booking_id = f"booking_{uuid.uuid4().hex[:12]}"
    doc = {
        "booking_id": booking_id,
        "user_id": user["user_id"],
        "booking_type": payload.booking_type,
        "item_id": payload.item_id,
        "item_name": item_name,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat() if payload.end_date else None,
        "total_price": total_price,
        "status": "pending",
        "payment_status": "pending",
        "guests": payload.guests,
        "created_at": now_iso(),
    }
    await db.bookings.insert_one(doc)

    if payload.booking_type == "flight":
        await db.flights.update_one(
            {"flight_id": payload.item_id},
            {"$inc": {"available_seats": -payload.guests}},
        )

    doc.pop("_id", None)
    return doc


@api.get("/bookings")
async def get_bookings(user: dict = Depends(require_user)):
    query = {} if user.get("is_admin") else {"user_id": user["user_id"]}
    cursor = db.bookings.find(query, {"_id": 0})
    return [b async for b in cursor]


@api.patch("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str, user: dict = Depends(require_user)):
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking["user_id"] != user["user_id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.bookings.update_one({"booking_id": booking_id}, {"$set": {"status": "cancelled"}})

    if booking["booking_type"] == "flight":
        await db.flights.update_one(
            {"flight_id": booking["item_id"]},
            {"$inc": {"available_seats": booking.get("guests", 1)}},
=======
        item_name = item['name']
        days = max((data.end_date - data.start_date).days, 1)
        total_price = item['price_per_night'] * days

    elif data.booking_type == "flight":
        item = await db.flights.find_one({"flight_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Flight not found")
        if item.get('available_seats', 0) < data.guests:
            raise HTTPException(status_code=400, detail="Not enough seats available")
        item_name = f"{item['from_city']} to {item['to_city']}"
        total_price = item['price'] * data.guests

    elif data.booking_type == "car":
        if not data.end_date:
            raise HTTPException(status_code=400, detail="end_date is required for car bookings")

        item = await db.cars.find_one({"car_id": data.item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Car not found")

        start_iso = data.start_date.isoformat()
        end_iso = data.end_date.isoformat()
        existing_bookings = await db.bookings.find({
            "item_id": data.item_id,
            "booking_type": "car",
            "status": {"$ne": "cancelled"},
            "start_date": {"$lte": end_iso},
            "end_date": {"$gte": start_iso}
        }).to_list(1000)

        booked_cars = len(existing_bookings)
        if booked_cars >= item.get("total_cars", 1):
            raise HTTPException(status_code=400, detail="No cars available for selected dates")

        item_name = f"{item['brand']} {item['model']}"
        days = max((data.end_date - data.start_date).days, 1)
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

    # FIX: flight seat count was never decremented after booking
    if data.booking_type == "flight":
        await db.flights.update_one(
            {"flight_id": data.item_id},
            {"$inc": {"available_seats": -data.guests}}
        )

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

    # FIX: restore flight seats when a flight booking is cancelled
    if booking['booking_type'] == "flight":
        await db.flights.update_one(
            {"flight_id": booking['item_id']},
            {"$inc": {"available_seats": booking.get('guests', 1)}}
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
        )

    return {"message": "Booking cancelled"}


<<<<<<< HEAD
# ============================================================
# Reviews
# ============================================================

@api.post("/reviews")
async def create_review(payload: ReviewCreate, user: dict = Depends(require_user)):
    review_id = f"review_{uuid.uuid4().hex[:12]}"
    doc = {
        "review_id": review_id,
        "user_id": user["user_id"],
        "user_name": user["name"],
        "item_type": payload.item_type,
        "item_id": payload.item_id,
        "rating": payload.rating,
        "comment": payload.comment,
        "created_at": now_iso(),
    }
    await db.reviews.insert_one(doc)

    collection_map = {"hotel": "hotels", "flight": "flights", "car": "cars", "experience": "experiences"}
    collection = db[collection_map[payload.item_type]]
=======
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

    collection_map = {"hotel": "hotels", "flight": "flights", "car": "cars", "experience": "experiences"}
    collection = db[collection_map[data.item_type]]

    reviews = await db.reviews.find({"item_type": data.item_type, "item_id": data.item_id}, {"_id": 0}).to_list(1000)
    avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0.0

    id_field = f"{data.item_type}_id"
    await collection.update_one({id_field: data.item_id}, {"$set": {"rating": round(avg_rating, 1)}})

    return review
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

    reviews = await db.reviews.find(
        {"item_type": payload.item_type, "item_id": payload.item_id}, {"_id": 0}
    ).to_list(1000)
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0.0

    id_field = f"{payload.item_type}_id"
    await collection.update_one({id_field: payload.item_id}, {"$set": {"rating": round(avg_rating, 1)}})

    doc.pop("_id", None)
    return doc


@api.get("/reviews/{item_type}/{item_id}")
async def get_reviews(item_type: str, item_id: str):
    cursor = db.reviews.find({"item_type": item_type, "item_id": item_id}, {"_id": 0})
    return [r async for r in cursor]


<<<<<<< HEAD
# ============================================================
# Favorites
# ============================================================

@api.post("/favorites")
async def add_favorite(payload: FavoriteCreate, user: dict = Depends(require_user)):
    existing = await db.favorites.find_one({
        "user_id": user["user_id"], "item_type": payload.item_type, "item_id": payload.item_id,
    }, {"_id": 0})
=======
@api_router.post("/favorites", response_model=Favorite)
async def add_favorite(data: FavoriteCreate, request: Request, session_token: Optional[str] = Cookie(None)):
    user = await get_current_user(request, session_token)

    existing = await db.favorites.find_one({"user_id": user.user_id, "item_type": data.item_type, "item_id": data.item_id}, {"_id": 0})
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")

    favorite_id = f"fav_{uuid.uuid4().hex[:12]}"
<<<<<<< HEAD
    doc = {
        "favorite_id": favorite_id,
        "user_id": user["user_id"],
        "item_type": payload.item_type,
        "item_id": payload.item_id,
        "created_at": now_iso(),
    }
    await db.favorites.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/favorites")
async def get_favorites(user: dict = Depends(require_user)):
    cursor = db.favorites.find({"user_id": user["user_id"]}, {"_id": 0})
    return [f async for f in cursor]


@api.delete("/favorites/{favorite_id}")
async def remove_favorite(favorite_id: str, user: dict = Depends(require_user)):
    result = await db.favorites.delete_one({"favorite_id": favorite_id, "user_id": user["user_id"]})
=======
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
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Removed from favorites"}

<<<<<<< HEAD
=======
app.include_router(api_router)
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

# ============================================================
# Health
# ============================================================

<<<<<<< HEAD
@api.get("/")
async def root():
    return {"app": "Chillax Travel", "status": "ok"}

=======
if not cors_origins:
    cors_origins = ["https://chillaxs.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add

app.include_router(api)


# ============================================================
# CORS — reflected origin for cookies/credentials
# ============================================================

CORS_RAW = os.environ.get("CORS_ORIGINS", "").strip()

if not CORS_RAW:
    # No explicit origins configured — reflect any origin (with credentials).
    # This avoids the "No 'Access-Control-Allow-Origin' header" failure that
    # happens with a strict allow_origins list when the env var isn't set
    # exactly right on the deploy target.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    cors_origins = [o.strip() for o in CORS_RAW.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

logger.info(f"CORS mode: {'regex-any' if not CORS_RAW else cors_origins}")


# ============================================================
# Startup / shutdown
# ============================================================

@app.on_event("startup")
async def on_startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.hotels.create_index("city")
        await db.flights.create_index([("from_city", 1), ("to_city", 1)])
        await db.cars.create_index("city")
        await db.experiences.create_index("city")
        await db.bookings.create_index([("user_id", 1), ("created_at", -1)])
        await db.bookings.create_index([("item_id", 1), ("booking_type", 1)])
        await db.reviews.create_index([("item_type", 1), ("item_id", 1)])
        await db.favorites.create_index([("user_id", 1)])
    except Exception as e:
        logger.warning(f"Index setup: {e}")

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@chillax.app")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": admin_email,
            "name": "Admin",
            "picture": None,
            "password_hash": hash_password(admin_password),
            "is_admin": True,
            "created_at": now_iso(),
        })
    elif existing.get("password_hash") and not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_password)}})

<<<<<<< HEAD

@app.on_event("shutdown")
async def on_shutdown():
=======
@app.on_event("shutdown")
async def shutdown_db_client():
>>>>>>> 5e18f901db9c7c3be61c0cbfba2356dbd87d9add
    client.close()
