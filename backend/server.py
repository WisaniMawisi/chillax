from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

import os
import logging
import uuid

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict
from passlib.context import CryptContext
import httpx




# ============================================================
# ENVIRONMENT
# ============================================================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is not set")

if not DB_NAME:
    raise RuntimeError("DB_NAME is not set")

if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in production")


# ============================================================
# DATABASE
# ============================================================

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ============================================================
# SECURITY
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ============================================================
# APP
# ============================================================

app = FastAPI()

api_router = APIRouter(prefix="/api")


# ============================================================
# HELPERS
# ============================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def cookie_settings() -> dict:
    return {
        "httponly": True,
        "secure": IS_PRODUCTION,
        "samesite": "none" if IS_PRODUCTION else "lax",
        "max_age": 7 * 24 * 60 * 60,
        "path": "/"
    }


def parse_datetime(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


async def get_item(
    item_type: str,
    item_id: str
):
    collection_map = {
        "hotel": ("hotels", "hotel_id"),
        "flight": ("flights", "flight_id"),
        "car": ("cars", "car_id"),
        "experience": ("experiences", "experience_id")
    }

    if item_type not in collection_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid item type"
        )

    collection_name, id_field = collection_map[item_type]

    item = await db[collection_name].find_one(
        {id_field: item_id},
        {"_id": 0}
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"{item_type.capitalize()} not found"
        )

    return item


# ============================================================
# MODELS
# ============================================================

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
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: str
    password: str


class SessionData(BaseModel):
    session_id: str


# ================= HOTEL =================

class Hotel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hotel_id: str
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float = Field(gt=0)
    rating: float = Field(default=0.0, ge=0, le=5)
    image_url: str
    amenities: List[str] = Field(default_factory=list)
    available: bool = True
    created_at: datetime


class HotelCreate(BaseModel):
    name: str
    location: str
    city: str
    country: str
    description: str
    price_per_night: float = Field(gt=0)
    image_url: str
    amenities: List[str] = Field(default_factory=list)


# ================= FLIGHT =================

class Flight(BaseModel):
    model_config = ConfigDict(extra="ignore")

    flight_id: str
    airline: str
    from_city: str
    to_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float = Field(gt=0)
    available_seats: int = Field(ge=0)
    image_url: str
    created_at: datetime


class FlightCreate(BaseModel):
    airline: str
    from_city: str
    to_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float = Field(gt=0)
    available_seats: int = Field(gt=0)
    image_url: str


# ================= CAR =================

class Car(BaseModel):
    model_config = ConfigDict(extra="ignore")

    car_id: str
    brand: str
    model: str
    location: str
    city: str
    price_per_day: float = Field(gt=0)
    available: bool = True
    image_url: str
    features: List[str] = Field(default_factory=list)
    created_at: datetime


class CarCreate(BaseModel):
    brand: str
    model: str
    location: str
    city: str
    price_per_day: float = Field(gt=0)
    image_url: str
    features: List[str] = Field(default_factory=list)


# ================= EXPERIENCE =================

class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")

    experience_id: str
    title: str
    location: str
    city: str
    description: str
    price: float = Field(gt=0)
    duration: str
    rating: float = Field(default=0.0, ge=0, le=5)
    image_url: str
    available: bool = True
    created_at: datetime


class ExperienceCreate(BaseModel):
    title: str
    location: str
    city: str
    description: str
    price: float = Field(gt=0)
    duration: str
    image_url: str


# ================= BOOKING =================

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_id: str
    user_id: str

    booking_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str
    item_name: str

    start_date: datetime
    end_date: Optional[datetime] = None

    total_price: float

    status: Literal[
        "pending",
        "confirmed",
        "cancelled"
    ] = "pending"

    payment_status: Literal[
        "pending",
        "paid",
        "refunded"
    ] = "pending"

    guests: int = Field(default=1, gt=0)

    created_at: datetime


class BookingCreate(BaseModel):

    booking_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str

    start_date: datetime
    end_date: Optional[datetime] = None

    guests: int = Field(default=1, gt=0)


# ================= REVIEW =================

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")

    review_id: str
    user_id: str
    user_name: str

    item_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str

    rating: float = Field(ge=1, le=5)
    comment: str

    created_at: datetime


class ReviewCreate(BaseModel):

    item_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str

    rating: float = Field(ge=1, le=5)

    comment: str = Field(min_length=1)


# ================= FAVORITE =================

class Favorite(BaseModel):
    model_config = ConfigDict(extra="ignore")

    favorite_id: str
    user_id: str

    item_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str

    created_at: datetime


class FavoriteCreate(BaseModel):

    item_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ]

    item_id: str


# ============================================================
# AUTH HELPER
# ============================================================

async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None)
) -> User:

    token = session_token

    # Check Authorization header if cookie does not exist
    if not token:
        auth_header = request.headers.get(
            "Authorization",
            ""
        )

        if auth_header.startswith("Bearer "):
            token = auth_header.split(
                " ",
                1
            )[1]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    session_doc = await db.user_sessions.find_one(
        {"session_token": token},
        {"_id": 0}
    )

    if not session_doc:
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )

    expires_at = parse_datetime(
        session_doc["expires_at"]
    )

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at < now_utc():

        # Remove expired session
        await db.user_sessions.delete_one(
            {"session_token": token}
        )

        raise HTTPException(
            status_code=401,
            detail="Session expired"
        )

    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )

    if not user_doc:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    user_doc["created_at"] = parse_datetime(
        user_doc["created_at"]
    )

    return User(**user_doc)


# ============================================================
# AUTH ROUTES
# ============================================================

@api_router.post("/auth/register")
async def register(data: UserRegister):

    existing = await db.users.find_one(
        {"email": data.email.lower()},
        {"_id": 0}
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_id = f"user_{uuid.uuid4().hex[:12]}"

    user = User(
        user_id=user_id,
        email=data.email.lower(),
        name=data.name,
        password_hash=pwd_context.hash(data.password),
        is_admin=False,
        created_at=now_utc()
    )

    user_dict = user.model_dump()
    user_dict["created_at"] = (
        user_dict["created_at"].isoformat()
    )

    await db.users.insert_one(user_dict)

    session_token = (
        f"session_{uuid.uuid4().hex}"
    )

    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (
            now_utc() + timedelta(days=7)
        ).isoformat(),
        "created_at": now_utc().isoformat()
    }

    await db.user_sessions.insert_one(
        session_doc
    )

    response = JSONResponse(
        content={
            "user_id": user_id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin
        }
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        **cookie_settings()
    )

    return response


@api_router.post("/auth/login")
async def login(data: UserLogin):

    email = data.email.lower()

    user_doc = await db.users.find_one(
        {"email": email},
        {"_id": 0}
    )

    if (
        not user_doc
        or not user_doc.get("password_hash")
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not pwd_context.verify(
        data.password,
        user_doc["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    session_token = (
        f"session_{uuid.uuid4().hex}"
    )

    session_doc = {
        "user_id": user_doc["user_id"],
        "session_token": session_token,
        "expires_at": (
            now_utc() + timedelta(days=7)
        ).isoformat(),
        "created_at": now_utc().isoformat()
    }

    await db.user_sessions.insert_one(
        session_doc
    )

    response = JSONResponse(
        content={
            "user_id": user_doc["user_id"],
            "email": user_doc["email"],
            "name": user_doc["name"],
            "picture": user_doc.get("picture"),
            "is_admin": user_doc.get(
                "is_admin",
                False
            )
        }
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        **cookie_settings()
    )

    return response


@api_router.post("/auth/session")
async def exchange_session(data: SessionData):

    async with httpx.AsyncClient(
        timeout=20.0
    ) as http_client:

        try:

            res = await http_client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={
                    "X-Session-ID": data.session_id
                }
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Authentication service unavailable"
            )

    if res.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid session_id"
        )

    oauth_data = res.json()

    if not oauth_data.get("email"):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication data"
        )

    email = oauth_data["email"].lower()

    user_doc = await db.users.find_one(
        {"email": email},
        {"_id": 0}
    )

    if user_doc:

        user_id = user_doc["user_id"]

        await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "name": oauth_data.get(
                        "name",
                        user_doc["name"]
                    ),
                    "picture": oauth_data.get(
                        "picture"
                    )
                }
            }
        )

    else:

        user_id = (
            f"user_{uuid.uuid4().hex[:12]}"
        )

        user = User(
            user_id=user_id,
            email=email,
            name=oauth_data.get(
                "name",
                "User"
            ),
            picture=oauth_data.get("picture"),
            is_admin=False,
            created_at=now_utc()
        )

        user_dict = user.model_dump()

        user_dict["created_at"] = (
            user_dict["created_at"].isoformat()
        )

        await db.users.insert_one(
            user_dict
        )

    # Use OAuth session token if available
    session_token = oauth_data.get(
        "session_token"
    )

    if not session_token:
        session_token = (
            f"session_{uuid.uuid4().hex}"
        )

    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (
            now_utc() + timedelta(days=7)
        ).isoformat(),
        "created_at": now_utc().isoformat()
    }

    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": session_doc},
        upsert=True
    )

    updated_user = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )

    response = JSONResponse(
        content={
            "user_id": user_id,
            "email": updated_user["email"],
            "name": updated_user["name"],
            "picture": updated_user.get("picture"),
            "is_admin": updated_user.get(
                "is_admin",
                False
            )
        }
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        **cookie_settings()
    )

    return response


@api_router.get("/auth/me")
async def get_me(
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "is_admin": user.is_admin
    }


@api_router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session_token: Optional[str] = Cookie(None)
):

    token = session_token

    if not token:

        auth_header = request.headers.get(
            "Authorization",
            ""
        )

        if auth_header.startswith("Bearer "):
            token = auth_header.split(
                " ",
                1
            )[1]

    if token:

        await db.user_sessions.delete_one(
            {"session_token": token}
        )

    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite=(
            "none"
            if IS_PRODUCTION
            else "lax"
        )
    )

    return {
        "message": "Logged out"
    }


# ============================================================
# HOTEL ROUTES
# ============================================================

@api_router.post(
    "/hotels",
    response_model=Hotel
)
async def create_hotel(
    data: HotelCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    hotel = Hotel(
        hotel_id=f"hotel_{uuid.uuid4().hex[:12]}",
        **data.model_dump(),
        created_at=now_utc()
    )

    hotel_dict = hotel.model_dump()
    hotel_dict["created_at"] = (
        hotel_dict["created_at"].isoformat()
    )

    await db.hotels.insert_one(
        hotel_dict
    )

    return hotel


@api_router.get(
    "/hotels",
    response_model=List[Hotel]
)
async def get_hotels(
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=400,
            detail="Minimum price cannot exceed maximum price"
        )

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i"
        }

    price_query = {}

    if min_price is not None:
        price_query["$gte"] = min_price

    if max_price is not None:
        price_query["$lte"] = max_price

    if price_query:
        query["price_per_night"] = price_query

    hotels = await db.hotels.find(
        query,
        {"_id": 0}
    ).to_list(1000)

    for hotel in hotels:
        hotel["created_at"] = parse_datetime(
            hotel["created_at"]
        )

    return hotels


@api_router.get(
    "/hotels/{hotel_id}",
    response_model=Hotel
)
async def get_hotel(hotel_id: str):

    hotel = await db.hotels.find_one(
        {"hotel_id": hotel_id},
        {"_id": 0}
    )

    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found"
        )

    hotel["created_at"] = parse_datetime(
        hotel["created_at"]
    )

    return hotel


@api_router.delete("/hotels/{hotel_id}")
async def delete_hotel(
    hotel_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    result = await db.hotels.delete_one(
        {"hotel_id": hotel_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found"
        )

    return {
        "message": "Hotel deleted"
    }


# ============================================================
# FLIGHT ROUTES
# ============================================================

@api_router.post(
    "/flights",
    response_model=Flight
)
async def create_flight(
    data: FlightCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    if data.arrival_time <= data.departure_time:
        raise HTTPException(
            status_code=400,
            detail="Arrival time must be after departure time"
        )

    flight = Flight(
        flight_id=f"flight_{uuid.uuid4().hex[:12]}",
        **data.model_dump(),
        created_at=now_utc()
    )

    flight_dict = flight.model_dump()

    flight_dict["departure_time"] = (
        flight_dict["departure_time"].isoformat()
    )

    flight_dict["arrival_time"] = (
        flight_dict["arrival_time"].isoformat()
    )

    flight_dict["created_at"] = (
        flight_dict["created_at"].isoformat()
    )

    await db.flights.insert_one(
        flight_dict
    )

    return flight


@api_router.get(
    "/flights",
    response_model=List[Flight]
)
async def get_flights(
    from_city: Optional[str] = None,
    to_city: Optional[str] = None
):

    query = {
        "available_seats": {
            "$gt": 0
        }
    }

    if from_city:
        query["from_city"] = {
            "$regex": from_city,
            "$options": "i"
        }

    if to_city:
        query["to_city"] = {
            "$regex": to_city,
            "$options": "i"
        }

    flights = await db.flights.find(
        query,
        {"_id": 0}
    ).to_list(1000)

    for flight in flights:

        flight["departure_time"] = (
            parse_datetime(
                flight["departure_time"]
            )
        )

        flight["arrival_time"] = (
            parse_datetime(
                flight["arrival_time"]
            )
        )

        flight["created_at"] = (
            parse_datetime(
                flight["created_at"]
            )
        )

    return flights


@api_router.get(
    "/flights/{flight_id}",
    response_model=Flight
)
async def get_flight(flight_id: str):

    flight = await db.flights.find_one(
        {"flight_id": flight_id},
        {"_id": 0}
    )

    if not flight:
        raise HTTPException(
            status_code=404,
            detail="Flight not found"
        )

    flight["departure_time"] = parse_datetime(
        flight["departure_time"]
    )

    flight["arrival_time"] = parse_datetime(
        flight["arrival_time"]
    )

    flight["created_at"] = parse_datetime(
        flight["created_at"]
    )

    return flight


@api_router.delete("/flights/{flight_id}")
async def delete_flight(
    flight_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    result = await db.flights.delete_one(
        {"flight_id": flight_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Flight not found"
        )

    return {
        "message": "Flight deleted"
    }


# ============================================================
# CAR ROUTES
# ============================================================

@api_router.post(
    "/cars",
    response_model=Car
)
async def create_car(
    data: CarCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    car = Car(
        car_id=f"car_{uuid.uuid4().hex[:12]}",
        **data.model_dump(),
        created_at=now_utc()
    )

    car_dict = car.model_dump()

    car_dict["created_at"] = (
        car_dict["created_at"].isoformat()
    )

    await db.cars.insert_one(car_dict)

    return car


@api_router.get(
    "/cars",
    response_model=List[Car]
)
async def get_cars(
    city: Optional[str] = None
):

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i"
        }

    cars = await db.cars.find(
        query,
        {"_id": 0}
    ).to_list(1000)

    for car in cars:
        car["created_at"] = parse_datetime(
            car["created_at"]
        )

    return cars


@api_router.get(
    "/cars/{car_id}",
    response_model=Car
)
async def get_car(car_id: str):

    car = await db.cars.find_one(
        {"car_id": car_id},
        {"_id": 0}
    )

    if not car:
        raise HTTPException(
            status_code=404,
            detail="Car not found"
        )

    car["created_at"] = parse_datetime(
        car["created_at"]
    )

    return car


@api_router.delete("/cars/{car_id}")
async def delete_car(
    car_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    result = await db.cars.delete_one(
        {"car_id": car_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Car not found"
        )

    return {
        "message": "Car deleted"
    }


# ============================================================
# EXPERIENCE ROUTES
# ============================================================

@api_router.post(
    "/experiences",
    response_model=Experience
)
async def create_experience(
    data: ExperienceCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    experience = Experience(
        experience_id=f"exp_{uuid.uuid4().hex[:12]}",
        **data.model_dump(),
        created_at=now_utc()
    )

    experience_dict = experience.model_dump()

    experience_dict["created_at"] = (
        experience_dict["created_at"].isoformat()
    )

    await db.experiences.insert_one(
        experience_dict
    )

    return experience


@api_router.get(
    "/experiences",
    response_model=List[Experience]
)
async def get_experiences(
    city: Optional[str] = None
):

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i"
        }

    experiences = await db.experiences.find(
        query,
        {"_id": 0}
    ).to_list(1000)

    for experience in experiences:
        experience["created_at"] = (
            parse_datetime(
                experience["created_at"]
            )
        )

    return experiences


@api_router.get(
    "/experiences/{experience_id}",
    response_model=Experience
)
async def get_experience(
    experience_id: str
):

    experience = await db.experiences.find_one(
        {"experience_id": experience_id},
        {"_id": 0}
    )

    if not experience:
        raise HTTPException(
            status_code=404,
            detail="Experience not found"
        )

    experience["created_at"] = parse_datetime(
        experience["created_at"]
    )

    return experience


@api_router.delete(
    "/experiences/{experience_id}"
)
async def delete_experience(
    experience_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    result = await db.experiences.delete_one(
        {"experience_id": experience_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Experience not found"
        )

    return {
        "message": "Experience deleted"
    }


# ============================================================
# BOOKING ROUTES
# ============================================================

@api_router.post(
    "/bookings",
    response_model=Booking
)
async def create_booking(
    data: BookingCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    # --------------------------------------------------------
    # Validate hotel and car dates
    # --------------------------------------------------------

    days = 1

    if data.booking_type in [
        "hotel",
        "car"
    ]:

        if not data.end_date:
            raise HTTPException(
                status_code=400,
                detail=(
                    "End date is required for "
                    "hotel and car bookings"
                )
            )

        days = (
            data.end_date - data.start_date
        ).days

        if days <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "End date must be after "
                    "start date"
                )
            )

    item_name = ""
    total_price = 0.0

    # --------------------------------------------------------
    # HOTEL
    # --------------------------------------------------------

    if data.booking_type == "hotel":

        item = await db.hotels.find_one(
            {
                "hotel_id": data.item_id,
                "available": True
            },
            {"_id": 0}
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Hotel not found or unavailable"
                )
            )

        item_name = item["name"]

        total_price = (
            item["price_per_night"]
            * days
        )

    # --------------------------------------------------------
    # FLIGHT
    # --------------------------------------------------------

    elif data.booking_type == "flight":

        # Atomically reserve seats
        result = await db.flights.update_one(
            {
                "flight_id": data.item_id,
                "available_seats": {
                    "$gte": data.guests
                }
            },
            {
                "$inc": {
                    "available_seats": (
                        -data.guests
                    )
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Flight not found or "
                    "not enough seats available"
                )
            )

        item = await db.flights.find_one(
            {"flight_id": data.item_id},
            {"_id": 0}
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Flight not found"
            )

        item_name = (
            f"{item['from_city']} "
            f"to {item['to_city']}"
        )

        total_price = (
            item["price"]
            * data.guests
        )

    # --------------------------------------------------------
    # CAR
    # --------------------------------------------------------

    elif data.booking_type == "car":

        item = await db.cars.find_one(
            {
                "car_id": data.item_id,
                "available": True
            },
            {"_id": 0}
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Car not found or unavailable"
                )
            )

        item_name = (
            f"{item['brand']} "
            f"{item['model']}"
        )

        total_price = (
            item["price_per_day"]
            * days
        )

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    elif data.booking_type == "experience":

        item = await db.experiences.find_one(
            {
                "experience_id": data.item_id,
                "available": True
            },
            {"_id": 0}
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Experience not found "
                    "or unavailable"
                )
            )

        item_name = item["title"]

        total_price = (
            item["price"]
            * data.guests
        )

    # --------------------------------------------------------
    # CREATE BOOKING
    # --------------------------------------------------------

    booking = Booking(
        booking_id=(
            f"booking_{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        item_name=item_name,
        total_price=round(
            total_price,
            2
        ),
        **data.model_dump(),
        created_at=now_utc()
    )

    booking_dict = booking.model_dump()

    booking_dict["start_date"] = (
        booking_dict["start_date"].isoformat()
    )

    if booking_dict.get("end_date"):
        booking_dict["end_date"] = (
            booking_dict["end_date"].isoformat()
        )

    booking_dict["created_at"] = (
        booking_dict["created_at"].isoformat()
    )

    try:

        await db.bookings.insert_one(
            booking_dict
        )

    except Exception as error:

        # Return seats if booking creation fails
        if data.booking_type == "flight":

            await db.flights.update_one(
                {"flight_id": data.item_id},
                {
                    "$inc": {
                        "available_seats": (
                            data.guests
                        )
                    }
                }
            )

        raise HTTPException(
            status_code=500,
            detail="Failed to create booking"
        ) from error

    return booking


@api_router.get(
    "/bookings",
    response_model=List[Booking]
)
async def get_bookings(
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    query = (
        {}
        if user.is_admin
        else {
            "user_id": user.user_id
        }
    )

    bookings = await db.bookings.find(
        query,
        {"_id": 0}
    ).to_list(1000)

    for booking in bookings:

        booking["start_date"] = (
            parse_datetime(
                booking["start_date"]
            )
        )

        if booking.get("end_date"):
            booking["end_date"] = (
                parse_datetime(
                    booking["end_date"]
                )
            )

        booking["created_at"] = (
            parse_datetime(
                booking["created_at"]
            )
        )

    return bookings


@api_router.patch(
    "/bookings/{booking_id}/cancel"
)
async def cancel_booking(
    booking_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    booking = await db.bookings.find_one(
        {"booking_id": booking_id},
        {"_id": 0}
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if (
        booking["user_id"] != user.user_id
        and not user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    if booking["status"] == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Booking already cancelled"
        )

    # Return flight seats when cancelling
    if booking["booking_type"] == "flight":

        await db.flights.update_one(
            {
                "flight_id": booking["item_id"]
            },
            {
                "$inc": {
                    "available_seats": (
                        booking.get("guests", 1)
                    )
                }
            }
        )

    await db.bookings.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "status": "cancelled"
            }
        }
    )

    return {
        "message": "Booking cancelled"
    }


# ============================================================
# REVIEW ROUTES
# ============================================================

@api_router.post(
    "/reviews",
    response_model=Review
)
async def create_review(
    data: ReviewCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    # Check item exists
    await get_item(
        data.item_type,
        data.item_id
    )

    review = Review(
        review_id=(
            f"review_{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        user_name=user.name,
        **data.model_dump(),
        created_at=now_utc()
    )

    review_dict = review.model_dump()

    review_dict["created_at"] = (
        review_dict["created_at"].isoformat()
    )

    await db.reviews.insert_one(
        review_dict
    )

    collection_map = {
        "hotel": ("hotels", "hotel_id"),
        "flight": ("flights", "flight_id"),
        "car": ("cars", "car_id"),
        "experience": (
            "experiences",
            "experience_id"
        )
    }

    collection_name, id_field = (
        collection_map[data.item_type]
    )

    reviews = await db.reviews.find(
        {
            "item_type": data.item_type,
            "item_id": data.item_id
        },
        {"_id": 0}
    ).to_list(1000)

    avg_rating = (
        sum(
            review_data["rating"]
            for review_data in reviews
        )
        / len(reviews)
    )

    await db[collection_name].update_one(
        {id_field: data.item_id},
        {
            "$set": {
                "rating": round(
                    avg_rating,
                    1
                )
            }
        }
    )

    return review


@api_router.get(
    "/reviews/{item_type}/{item_id}",
    response_model=List[Review]
)
async def get_reviews(
    item_type: Literal[
        "hotel",
        "flight",
        "car",
        "experience"
    ],
    item_id: str
):

    reviews = await db.reviews.find(
        {
            "item_type": item_type,
            "item_id": item_id
        },
        {"_id": 0}
    ).to_list(1000)

    for review in reviews:
        review["created_at"] = parse_datetime(
            review["created_at"]
        )

    return reviews


# ============================================================
# FAVORITE ROUTES
# ============================================================

@api_router.post(
    "/favorites",
    response_model=Favorite
)
async def add_favorite(
    data: FavoriteCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    # Check item exists
    await get_item(
        data.item_type,
        data.item_id
    )

    existing = await db.favorites.find_one(
        {
            "user_id": user.user_id,
            "item_type": data.item_type,
            "item_id": data.item_id
        },
        {"_id": 0}
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Already in favorites"
        )

    favorite = Favorite(
        favorite_id=(
            f"fav_{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        **data.model_dump(),
        created_at=now_utc()
    )

    favorite_dict = favorite.model_dump()

    favorite_dict["created_at"] = (
        favorite_dict["created_at"].isoformat()
    )

    await db.favorites.insert_one(
        favorite_dict
    )

    return favorite


@api_router.get(
    "/favorites",
    response_model=List[Favorite]
)
async def get_favorites(
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    favorites = await db.favorites.find(
        {
            "user_id": user.user_id
        },
        {"_id": 0}
    ).to_list(1000)

    for favorite in favorites:
        favorite["created_at"] = parse_datetime(
            favorite["created_at"]
        )

    return favorites


@api_router.delete(
    "/favorites/{favorite_id}"
)
async def remove_favorite(
    favorite_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None)
):

    user = await get_current_user(
        request,
        session_token
    )

    result = await db.favorites.delete_one(
        {
            "favorite_id": favorite_id,
            "user_id": user.user_id
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Favorite not found"
        )

    return {
        "message": "Removed from favorites"
    }


# ============================================================
# CORS
# ============================================================

allowed_origins = [
    "https://chillaxs.netlify.app",
    "https://chillax-po8w.onrender.com",
    "http://localhost:3000",
    "http://localhost:5173",
]

extra_origins = os.getenv("CORS_ORIGINS", "")

if extra_origins:
    allowed_origins.extend(
        [
            origin.strip()
            for origin in extra_origins.split(",")
            if origin.strip()
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API ROUTES
# ============================================================

app.include_router(api_router)

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def shutdown_db_client():

    client.close()