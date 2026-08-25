from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Cookie,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

import os
import logging
import uuid
import hashlib
import httpx

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict
from passlib.context import CryptContext
from pymongo import ReturnDocument


# ============================================================
# ENVIRONMENT
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
).lower()

IS_PRODUCTION = ENVIRONMENT == "production"

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
# NOTE: not read anywhere else in this file yet. Sessions
# are currently authenticated by a random opaque token
# (hashed with SHA-256 before storage), which doesn't need
# a signing key. SECRET_KEY is reserved/required so that a
# future move to signed tokens (e.g. JWTs) or CSRF-token
# signing doesn't require an env/deploy change on top of a
# code change. If you don't anticipate needing that, it's
# safe to drop the production requirement below.

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is not set")

if not DB_NAME:
    raise RuntimeError("DB_NAME is not set")

if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set")


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
    ),
)

logger = logging.getLogger("chillax")


# ============================================================
# DATABASE
# ============================================================

client = AsyncIOMotorClient(
    MONGO_URL,
    serverSelectionTimeoutMS=10000,
    # By default PyMongo/Motor decode BSON dates as naive
    # datetimes (no tzinfo), even though they're stored as
    # UTC. Since now_utc() and the rest of this file work in
    # timezone-aware datetimes (timezone.utc), and we now
    # store start_date/end_date/expires_at/created_at as
    # native BSON dates rather than ISO strings, comparisons
    # like `expires_at < now_utc()` would raise
    # "can't compare offset-naive and offset-aware datetimes"
    # without this. tz_aware=True + tzinfo=utc makes every
    # datetime read back from Mongo timezone-aware UTC.
    tz_aware=True,
    tzinfo=timezone.utc,
)

db = client[DB_NAME]


# ============================================================
# SECURITY
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_session_token() -> str:
    return f"session_{uuid.uuid4().hex}"


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Chillax Travel API",
    version="1.0.0",
)

api_router = APIRouter(
    prefix="/api",
)


# ============================================================
# CORS
# ============================================================

allowed_origins = [
    "https://chillaxs.netlify.app",
    "https://chillax-po8w.onrender.com",
    "http://localhost:3000",
    "http://localhost:5173",
]

extra_origins = os.getenv(
    "CORS_ORIGINS",
    "",
)

if extra_origins:
    allowed_origins.extend(
        [
            origin.strip().rstrip("/")
            for origin in extra_origins.split(",")
            if origin.strip()
        ]
    )

# Remove duplicates while preserving order.
allowed_origins = list(
    dict.fromkeys(allowed_origins)
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def cookie_settings() -> dict:
    return {
        "httponly": True,
        "secure": IS_PRODUCTION,
        "samesite": (
            "none"
            if IS_PRODUCTION
            else "lax"
        ),
        "max_age": 7 * 24 * 60 * 60,
        "path": "/",
    }


def parse_datetime(value):
    if not value:
        return value

    if isinstance(value, datetime):
        return value

    try:
        parsed = datetime.fromisoformat(
            str(value)
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    except Exception:
        return value


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(timezone.utc)


# ============================================================
# USER MODELS
# ============================================================

class User(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    password_hash: Optional[str] = None
    is_admin: bool = False
    created_at: datetime


class UserRegister(BaseModel):
    email: str = Field(
        min_length=3
    )

    password: str = Field(
        min_length=6
    )

    name: str = Field(
        min_length=1
    )


class UserLogin(BaseModel):
    email: str
    password: str


class SessionData(BaseModel):
    session_id: str


# ============================================================
# HOTEL MODELS
# ============================================================

class Hotel(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    hotel_id: str
    name: str
    location: str
    city: str
    country: str
    description: str

    price_per_night: float = Field(
        gt=0
    )

    total_units: int = Field(
        default=1,
        gt=0,
        description=(
            "Number of interchangeable "
            "rooms this listing "
            "represents. Overlapping "
            "bookings are allowed up to "
            "this count."
        ),
    )

    rating: float = Field(
        default=0.0,
        ge=0,
        le=5,
    )

    image_url: str

    amenities: List[str] = Field(
        default_factory=list
    )

    available: bool = True
    created_at: datetime


class HotelCreate(BaseModel):
    name: str
    location: str
    city: str
    country: str
    description: str

    price_per_night: float = Field(
        gt=0
    )

    total_units: int = Field(
        default=1,
        gt=0,
    )

    image_url: str

    amenities: List[str] = Field(
        default_factory=list
    )


# ============================================================
# FLIGHT MODELS
# ============================================================

class Flight(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    flight_id: str
    airline: str
    from_city: str
    to_city: str

    departure_time: datetime
    arrival_time: datetime

    price: float = Field(
        gt=0
    )

    available_seats: int = Field(
        ge=0
    )

    image_url: str
    created_at: datetime


class FlightCreate(BaseModel):
    airline: str
    from_city: str
    to_city: str

    departure_time: datetime
    arrival_time: datetime

    price: float = Field(
        gt=0
    )

    available_seats: int = Field(
        gt=0
    )

    image_url: str


# ============================================================
# CAR MODELS
# ============================================================

class Car(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    car_id: str
    brand: str
    model: str
    location: str
    city: str

    price_per_day: float = Field(
        gt=0
    )

    total_units: int = Field(
        default=1,
        gt=0,
        description=(
            "Number of interchangeable "
            "vehicles this listing "
            "represents. Overlapping "
            "bookings are allowed up to "
            "this count."
        ),
    )

    available: bool = True
    image_url: str

    features: List[str] = Field(
        default_factory=list
    )

    created_at: datetime


class CarCreate(BaseModel):
    brand: str
    model: str
    location: str
    city: str

    price_per_day: float = Field(
        gt=0
    )

    total_units: int = Field(
        default=1,
        gt=0,
    )

    image_url: str

    features: List[str] = Field(
        default_factory=list
    )


# ============================================================
# EXPERIENCE MODELS
# ============================================================

class Experience(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    experience_id: str
    title: str
    location: str
    city: str
    description: str

    price: float = Field(
        gt=0
    )

    duration: str

    rating: float = Field(
        default=0.0,
        ge=0,
        le=5,
    )

    image_url: str

    capacity: int = Field(
        default=20,
        gt=0,
    )

    booked_guests: int = Field(
        default=0,
        ge=0,
    )

    available: bool = True
    created_at: datetime


class ExperienceCreate(BaseModel):
    title: str
    location: str
    city: str
    description: str

    price: float = Field(
        gt=0
    )

    duration: str
    image_url: str

    capacity: int = Field(
        default=20,
        gt=0,
    )


# ============================================================
# BOOKING MODELS
# ============================================================

BookingType = Literal[
    "hotel",
    "flight",
    "car",
    "experience",
]


class Booking(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    booking_id: str
    user_id: str

    booking_type: BookingType

    item_id: str
    item_name: str

    start_date: datetime
    end_date: Optional[datetime] = None

    total_price: float

    status: Literal[
        "pending",
        "confirmed",
        "cancelled",
    ] = "pending"

    payment_status: Literal[
        "pending",
        "paid",
        "refunded",
    ] = "pending"

    guests: int = Field(
        default=1,
        gt=0,
    )

    created_at: datetime


class BookingCreate(BaseModel):
    booking_type: BookingType

    item_id: str

    start_date: datetime

    end_date: Optional[datetime] = None

    guests: int = Field(
        default=1,
        gt=0,
    )


# ============================================================
# REVIEW MODELS
# ============================================================

class Review(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    review_id: str
    user_id: str
    user_name: str

    item_type: BookingType
    item_id: str

    rating: float = Field(
        ge=1,
        le=5,
    )

    comment: str

    created_at: datetime


class ReviewCreate(BaseModel):
    item_type: BookingType
    item_id: str

    rating: float = Field(
        ge=1,
        le=5,
    )

    comment: str = Field(
        min_length=1
    )


# ============================================================
# FAVORITE MODELS
# ============================================================

class Favorite(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )

    favorite_id: str
    user_id: str

    item_type: BookingType
    item_id: str

    created_at: datetime


class FavoriteCreate(BaseModel):
    item_type: BookingType
    item_id: str


# ============================================================
# AUTH HELPER
# ============================================================

async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
) -> User:

    token = session_token

    if not token:
        authorization = request.headers.get(
            "Authorization",
            "",
        )

        if authorization.startswith(
            "Bearer "
        ):
            token = authorization.split(
                " ",
                1,
            )[1].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    token_hash = hash_session_token(
        token
    )

    session = await db.user_sessions.find_one(
        {
            "session_token_hash": token_hash
        },
        {"_id": 0},
    )

    # Backwards compatibility with older
    # sessions stored as plain tokens.
    if not session:
        session = await db.user_sessions.find_one(
            {
                "session_token": token
            },
            {"_id": 0},
        )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    expires_at = parse_datetime(
        session.get("expires_at")
    )

    if (
        isinstance(expires_at, datetime)
        and expires_at < now_utc()
    ):
        # Delete by the fields we actually
        # queried on. The earlier find_one
        # calls excluded "_id" from the
        # projection, so session.get("_id")
        # is always None and can't be used
        # as a delete filter.
        await db.user_sessions.delete_one(
            {
                "session_token_hash":
                    token_hash
            }
        )

        # Remove old-format plain-token
        # sessions too, in case this was a
        # backwards-compatibility match.
        await db.user_sessions.delete_one(
            {
                "session_token": token
            }
        )

        raise HTTPException(
            status_code=401,
            detail="Session expired",
        )

    user_doc = await db.users.find_one(
        {
            "user_id":
                session["user_id"]
        },
        {"_id": 0},
    )

    if not user_doc:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if isinstance(
        user_doc.get("created_at"),
        str,
    ):
        user_doc["created_at"] = (
            parse_datetime(
                user_doc["created_at"]
            )
        )

    return User(**user_doc)


# ============================================================
# ADMIN BOOTSTRAP
# ============================================================

async def bootstrap_admin():
    admin_email = os.getenv(
        "ADMIN_EMAIL"
    )
    admin_password = os.getenv(
        "ADMIN_PASSWORD"
    )

    if not admin_email or not admin_password:
        return

    email = admin_email.lower().strip()

    existing = await db.users.find_one(
        {
            "email": email
        }
    )

    if existing:
        await db.users.update_one(
            {
                "email": email
            },
            {
                "$set": {
                    "is_admin": True
                }
            },
        )

        logger.info(
            "Admin account verified: %s",
            email,
        )

        return

    user = User(
        user_id=(
            f"user_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        email=email,
        name=os.getenv(
            "ADMIN_NAME",
            "Administrator",
        ),
        password_hash=pwd_context.hash(
            admin_password
        ),
        is_admin=True,
        created_at=now_utc(),
    )

    document = user.model_dump()

    await db.users.insert_one(
        document
    )

    logger.info(
        "Admin account created: %s",
        email,
    )


# ============================================================
# ITEM HELPER
# ============================================================

async def get_item(
    item_type: str,
    item_id: str,
):
    collection_map = {
        "hotel": (
            "hotels",
            "hotel_id",
        ),
        "flight": (
            "flights",
            "flight_id",
        ),
        "car": (
            "cars",
            "car_id",
        ),
        "experience": (
            "experiences",
            "experience_id",
        ),
    }

    if item_type not in collection_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid item type",
        )

    collection_name, id_field = (
        collection_map[item_type]
    )

    item = await db[
        collection_name
    ].find_one(
        {
            id_field: item_id
        },
        {"_id": 0},
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{item_type.capitalize()} "
                "not found"
            ),
        )

    return item


# ============================================================
# BOOKING OVERLAP HELPER
# ============================================================

async def count_overlapping_bookings(
    item_type: str,
    item_id: str,
    start_date: datetime,
    end_date: datetime,
    session=None,
) -> int:
    """
    Counts active (pending/confirmed) bookings for this
    listing whose date range overlaps [start_date, end_date).

    This is evaluated entirely inside MongoDB rather than
    pulling every booking into Python and comparing there —
    both faster at scale and correct regardless of how the
    stored datetimes format as strings, since Mongo compares
    the underlying BSON Date values directly rather than
    lexicographically comparing ISO strings (which is unsafe:
    Python's datetime.isoformat() drops the microsecond
    component when it's zero, so two ISO strings of different
    lengths don't always sort the way their datetimes do).
    """

    start_date = normalize_datetime(
        start_date
    )

    end_date = normalize_datetime(
        end_date
    )

    return await db.bookings.count_documents(
        {
            "booking_type": item_type,
            "item_id": item_id,
            "status": {
                "$in": [
                    "pending",
                    "confirmed",
                ]
            },
            "start_date": {
                "$lt": end_date
            },
            "end_date": {
                "$gt": start_date
            },
        },
        session=session,
    )


# ============================================================
# FLIGHT SEAT RESTORATION
# ============================================================

async def restore_flight_seats(
    booking: dict,
) -> None:

    if booking.get(
        "booking_type"
    ) != "flight":
        return

    guests = int(
        booking.get(
            "guests",
            0,
        )
    )

    if guests <= 0:
        return

    await db.flights.update_one(
        {
            "flight_id":
                booking["item_id"]
        },
        {
            "$inc": {
                "available_seats":
                    guests
            }
        },
    )


async def restore_experience_capacity(
    booking: dict,
) -> None:

    if booking.get(
        "booking_type"
    ) != "experience":
        return

    guests = int(
        booking.get(
            "guests",
            0,
        )
    )

    if guests <= 0:
        return

    await db.experiences.update_one(
        {
            "experience_id":
                booking["item_id"]
        },
        {
            "$inc": {
                "booked_guests":
                    -guests
            }
        },
    )


# ============================================================
# AUTH ROUTES
# ============================================================

@api_router.post(
    "/auth/register"
)
async def register(
    data: UserRegister,
):

    email = data.email.lower().strip()

    existing = await db.users.find_one(
        {
            "email": email
        },
        {"_id": 0},
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )
    
    user_id = (
        f"user_"
        f"{uuid.uuid4().hex[:12]}"
    )

    try:
        password_hash = pwd_context.hash(
            data.password
        )
    except Exception:
        logger.exception(
            "Password hashing failed"
        )
        raise HTTPException(
            status_code=500,
            detail="Registration failed",
        )

    user = User(
        user_id=user_id,
        email=email,
        name=data.name.strip(),
        password_hash=password_hash,
        is_admin=False,
        created_at=now_utc(),
    )

    document = user.model_dump()

    try:
        await db.users.insert_one(
            document
        )

    except Exception as exc:
        logger.exception(
            "Registration failed"
        )

        if "duplicate" in str(
            exc
        ).lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Email already registered"
                ),
            )

        raise HTTPException(
            status_code=500,
            detail="Registration failed",
        )

    token = create_session_token()

    session_document = {
        "user_id": user_id,
        "session_token_hash":
            hash_session_token(token),
        "expires_at": (
            now_utc()
            + timedelta(days=7)
        ),
        "created_at": now_utc(),
    }

    await db.user_sessions.insert_one(
        session_document
    )

    response = JSONResponse(
        content={
            "user_id":
                user.user_id,
            "email":
                user.email,
            "name":
                user.name,
            "is_admin":
                user.is_admin,
            "access_token":
                token,
            "token_type":
                "bearer",
        }
    )

    response.set_cookie(
        key="session_token",
        value=token,
        **cookie_settings(),
    )

    return response


@api_router.post(
    "/auth/login"
)
async def login(
    data: UserLogin,
):

    email = data.email.lower().strip()

    user_doc = await db.users.find_one(
        {
            "email": email
        },
        {"_id": 0},
    )

    if (
        not user_doc
        or not user_doc.get(
            "password_hash"
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    try:
        valid_password = (
            pwd_context.verify(
                data.password,
                user_doc[
                    "password_hash"
                ],
            )
        )

    except Exception:
        valid_password = False

    if not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    # Remove old sessions for this user.
    await db.user_sessions.delete_many(
        {
            "user_id":
                user_doc["user_id"]
        }
    )

    token = create_session_token()

    await db.user_sessions.insert_one(
        {
            "user_id":
                user_doc["user_id"],
            "session_token_hash":
                hash_session_token(token),
            "expires_at": (
                now_utc()
                + timedelta(days=7)
            ),
            "created_at":
                now_utc(),
        }
    )

    response = JSONResponse(
        content={
            "user_id":
                user_doc["user_id"],
            "email":
                user_doc["email"],
            "name":
                user_doc["name"],
            "picture":
                user_doc.get("picture"),
            "is_admin":
                user_doc.get(
                    "is_admin",
                    False,
                ),
            "access_token":
                token,
            "token_type":
                "bearer",
        }
    )

    response.set_cookie(
        key="session_token",
        value=token,
        **cookie_settings(),
    )

    return response


@api_router.post(
    "/auth/session"
)
async def exchange_session(
    data: SessionData,
):

    async with httpx.AsyncClient(
        timeout=20.0
    ) as http_client:

        try:
            response = await http_client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={
                    "X-Session-ID":
                        data.session_id,
                },
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Authentication "
                    "service unavailable"
                ),
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid session_id",
        )

    try:
        oauth_data = response.json()
    except Exception:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid authentication "
                "response"
            ),
        )

    email = oauth_data.get(
        "email",
        "",
    ).lower().strip()

    if not email:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid authentication "
                "data"
            ),
        )

    user_doc = await db.users.find_one(
        {
            "email": email
        },
        {"_id": 0},
    )

    if user_doc:

        user_id = user_doc[
            "user_id"
        ]

        await db.users.update_one(
            {
                "user_id": user_id
            },
            {
                "$set": {
                    "name":
                        oauth_data.get(
                            "name",
                            user_doc.get(
                                "name",
                                "User",
                            ),
                        ),
                    "picture":
                        oauth_data.get(
                            "picture"
                        ),
                }
            },
        )

    else:

        user_id = (
            f"user_"
            f"{uuid.uuid4().hex[:12]}"
        )

        user = User(
            user_id=user_id,
            email=email,
            name=oauth_data.get(
                "name",
                "User",
            ),
            picture=oauth_data.get(
                "picture"
            ),
            is_admin=False,
            created_at=now_utc(),
        )

        document = user.model_dump()

        await db.users.insert_one(
            document
        )

    token = create_session_token()

    await db.user_sessions.delete_many(
        {
            "user_id": user_id
        }
    )

    await db.user_sessions.insert_one(
        {
            "user_id": user_id,
            "session_token_hash":
                hash_session_token(token),
            "expires_at": (
                now_utc()
                + timedelta(days=7)
            ),
            "created_at":
                now_utc(),
        }
    )

    updated_user = (
        await db.users.find_one(
            {
                "user_id": user_id
            },
            {"_id": 0},
        )
    )

    response = JSONResponse(
        content={
            "user_id":
                user_id,
            "email":
                updated_user["email"],
            "name":
                updated_user["name"],
            "picture":
                updated_user.get(
                    "picture"
                ),
            "is_admin":
                updated_user.get(
                    "is_admin",
                    False,
                ),
            "access_token":
                token,
            "token_type":
                "bearer",
        }
    )

    response.set_cookie(
        key="session_token",
        value=token,
        **cookie_settings(),
    )

    return response


@api_router.get(
    "/auth/me"
)
async def get_me(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    return {
        "user_id":
            user.user_id,
        "email":
            user.email,
        "name":
            user.name,
        "picture":
            user.picture,
        "is_admin":
            user.is_admin,
    }


@api_router.post(
    "/auth/logout"
)
async def logout(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    token = session_token

    if not token:

        authorization = request.headers.get(
            "Authorization",
            "",
        )

        if authorization.startswith(
            "Bearer "
        ):
            token = authorization.split(
                " ",
                1,
            )[1].strip()

    if token:

        await db.user_sessions.delete_one(
            {
                "session_token_hash":
                    hash_session_token(token)
            }
        )

        # Remove old-format sessions too.
        await db.user_sessions.delete_one(
            {
                "session_token":
                    token
            }
        )

    response = JSONResponse(
        {
            "message":
                "Logged out"
        }
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
        ),
    )

    return response


# ============================================================
# HOTEL ROUTES
# ============================================================

@api_router.post(
    "/hotels",
    response_model=Hotel,
)
async def create_hotel(
    data: HotelCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    hotel = Hotel(
        hotel_id=(
            f"hotel_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = hotel.model_dump()

    await db.hotels.insert_one(
        document
    )

    return hotel


@api_router.get(
    "/hotels",
    response_model=List[Hotel],
)
async def get_hotels(
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Minimum price cannot "
                "exceed maximum price"
            ),
        )

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i",
        }

    price_query = {}

    if min_price is not None:
        price_query["$gte"] = min_price

    if max_price is not None:
        price_query["$lte"] = max_price

    if price_query:
        query[
            "price_per_night"
        ] = price_query

    hotels = await db.hotels.find(
        query,
        {"_id": 0},
    ).to_list(1000)

    for hotel in hotels:
        hotel["created_at"] = (
            parse_datetime(
                hotel.get("created_at")
            )
        )

    return hotels


@api_router.get(
    "/hotels/{hotel_id}",
    response_model=Hotel,
)
async def get_hotel(
    hotel_id: str,
):

    hotel = await db.hotels.find_one(
        {
            "hotel_id":
                hotel_id
        },
        {"_id": 0},
    )

    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found",
        )

    hotel["created_at"] = (
        parse_datetime(
            hotel.get("created_at")
        )
    )

    return hotel


@api_router.delete(
    "/hotels/{hotel_id}"
)
async def delete_hotel(
    hotel_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    result = await db.hotels.delete_one(
        {
            "hotel_id":
                hotel_id
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found",
        )

    return {
        "message":
            "Hotel deleted"
    }


# ============================================================
# FLIGHT ROUTES
# ============================================================

@api_router.post(
    "/flights",
    response_model=Flight,
)
async def create_flight(
    data: FlightCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    if (
        data.arrival_time
        <= data.departure_time
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Arrival time must be "
                "after departure time"
            ),
        )

    flight = Flight(
        flight_id=(
            f"flight_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = flight.model_dump()

    await db.flights.insert_one(
        document
    )

    return flight


@api_router.get(
    "/flights",
    response_model=List[Flight],
)
async def get_flights(
    from_city: Optional[str] = None,
    to_city: Optional[str] = None,
):

    query = {
        "available_seats": {
            "$gt": 0
        }
    }

    if from_city:
        query["from_city"] = {
            "$regex": from_city,
            "$options": "i",
        }

    if to_city:
        query["to_city"] = {
            "$regex": to_city,
            "$options": "i",
        }

    flights = await db.flights.find(
        query,
        {"_id": 0},
    ).to_list(1000)

    for flight in flights:

        flight["departure_time"] = (
            parse_datetime(
                flight.get(
                    "departure_time"
                )
            )
        )

        flight["arrival_time"] = (
            parse_datetime(
                flight.get(
                    "arrival_time"
                )
            )
        )

        flight["created_at"] = (
            parse_datetime(
                flight.get(
                    "created_at"
                )
            )
        )

    return flights


@api_router.get(
    "/flights/{flight_id}",
    response_model=Flight,
)
async def get_flight(
    flight_id: str,
):

    flight = await db.flights.find_one(
        {
            "flight_id":
                flight_id
        },
        {"_id": 0},
    )

    if not flight:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    flight["departure_time"] = (
        parse_datetime(
            flight.get(
                "departure_time"
            )
        )
    )

    flight["arrival_time"] = (
        parse_datetime(
            flight.get(
                "arrival_time"
            )
        )
    )

    flight["created_at"] = (
        parse_datetime(
            flight.get(
                "created_at"
            )
        )
    )

    return flight


@api_router.delete(
    "/flights/{flight_id}"
)
async def delete_flight(
    flight_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    result = await db.flights.delete_one(
        {
            "flight_id":
                flight_id
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    return {
        "message":
            "Flight deleted"
    }


# ============================================================
# CAR ROUTES
# ============================================================

@api_router.post(
    "/cars",
    response_model=Car,
)
async def create_car(
    data: CarCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    car = Car(
        car_id=(
            f"car_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = car.model_dump()

    await db.cars.insert_one(
        document
    )

    return car


@api_router.get(
    "/cars",
    response_model=List[Car],
)
async def get_cars(
    city: Optional[str] = None,
):

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i",
        }

    cars = await db.cars.find(
        query,
        {"_id": 0},
    ).to_list(1000)

    for car in cars:
        car["created_at"] = (
            parse_datetime(
                car.get(
                    "created_at"
                )
            )
        )

    return cars


@api_router.get(
    "/cars/{car_id}",
    response_model=Car,
)
async def get_car(
    car_id: str,
):

    car = await db.cars.find_one(
        {
            "car_id":
                car_id
        },
        {"_id": 0},
    )

    if not car:
        raise HTTPException(
            status_code=404,
            detail="Car not found",
        )

    car["created_at"] = (
        parse_datetime(
            car.get(
                "created_at"
            )
        )
    )

    return car


@api_router.delete(
    "/cars/{car_id}"
)
async def delete_car(
    car_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    result = await db.cars.delete_one(
        {
            "car_id":
                car_id
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Car not found",
        )

    return {
        "message":
            "Car deleted"
    }


# ============================================================
# EXPERIENCE ROUTES
# ============================================================

@api_router.post(
    "/experiences",
    response_model=Experience,
)
async def create_experience(
    data: ExperienceCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    experience = Experience(
        experience_id=(
            f"exp_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = experience.model_dump()

    await db.experiences.insert_one(
        document
    )

    return experience


@api_router.get(
    "/experiences",
    response_model=List[Experience],
)
async def get_experiences(
    city: Optional[str] = None,
):

    query = {
        "available": True
    }

    if city:
        query["city"] = {
            "$regex": city,
            "$options": "i",
        }

    experiences = (
        await db.experiences.find(
            query,
            {"_id": 0},
        ).to_list(1000)
    )

    for experience in experiences:

        # Old records may not have capacity.
        experience["capacity"] = int(
            experience.get(
                "capacity",
                20,
            )
        )

        experience["created_at"] = (
            parse_datetime(
                experience.get(
                    "created_at"
                )
            )
        )

    return experiences


@api_router.get(
    "/experiences/{experience_id}",
    response_model=Experience,
)
async def get_experience(
    experience_id: str,
):

    experience = (
        await db.experiences.find_one(
            {
                "experience_id":
                    experience_id
            },
            {"_id": 0},
        )
    )

    if not experience:
        raise HTTPException(
            status_code=404,
            detail="Experience not found",
        )

    experience["capacity"] = int(
        experience.get(
            "capacity",
            20,
        )
    )

    experience["created_at"] = (
        parse_datetime(
            experience.get(
                "created_at"
            )
        )
    )

    return experience


@api_router.delete(
    "/experiences/{experience_id}"
)
async def delete_experience(
    experience_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    result = (
        await db.experiences.delete_one(
            {
                "experience_id":
                    experience_id
            }
        )
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Experience not found",
        )

    return {
        "message":
            "Experience deleted"
    }


# ============================================================
# BOOKING ROUTES
# ============================================================

@api_router.post(
    "/bookings",
    response_model=Booking,
)
async def create_booking(
    data: BookingCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    data.start_date = normalize_datetime(
        data.start_date
    )

    if data.end_date:
        data.end_date = normalize_datetime(
            data.end_date
        )

    if data.booking_type in [
        "hotel",
        "car",
    ]:

        if not data.end_date:
            raise HTTPException(
                status_code=400,
                detail=(
                    "End date required for "
                    "hotel and car bookings"
                ),
            )

        days = (
            data.end_date
            - data.start_date
        ).days

        if days <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid booking dates",
            )

    else:
        days = 1

    if data.start_date < now_utc() - timedelta(
        minutes=1
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Booking start date cannot "
                "be in the past"
            ),
        )

    item_name = ""
    total_price = 0.0
    experience_capacity_reserved = False

    # --------------------------------------------------------
    # HOTEL / CAR
    #
    # The "check for overlap, then insert" sequence is a
    # classic check-then-act race: two concurrent requests can
    # both see no conflict and both insert. We close that
    # window by running the check, the pricing lookup, and the
    # booking insert inside a single MongoDB transaction, which
    # requires the deployment to be a replica set (Atlas is by
    # default; a standalone dev mongod is not). If transactions
    # aren't available we fall back to the previous
    # best-effort behavior rather than hard-failing dev setups.
    # --------------------------------------------------------

    async def _build_hotel_or_car_booking(session=None):
        nonlocal item_name, total_price

        if data.booking_type == "hotel":

            item = await db.hotels.find_one(
                {
                    "hotel_id":
                        data.item_id,
                    "available": True,
                },
                {"_id": 0},
                session=session,
            )

            if not item:
                raise HTTPException(
                    status_code=404,
                    detail="Hotel unavailable",
                )

            total_units = int(
                item.get(
                    "total_units",
                    1,
                )
            )

            overlapping = await count_overlapping_bookings(
                "hotel",
                data.item_id,
                data.start_date,
                data.end_date,
                session=session,
            )

            if overlapping >= total_units:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Hotel has no rooms "
                        "available for the "
                        "selected dates"
                    ),
                )

            item_name = item["name"]

            total_price = (
                float(
                    item["price_per_night"]
                )
                * days
                * data.guests
            )

        else:

            item = await db.cars.find_one(
                {
                    "car_id":
                        data.item_id,
                    "available": True,
                },
                {"_id": 0},
                session=session,
            )

            if not item:
                raise HTTPException(
                    status_code=404,
                    detail="Car unavailable",
                )

            total_units = int(
                item.get(
                    "total_units",
                    1,
                )
            )

            overlapping = await count_overlapping_bookings(
                "car",
                data.item_id,
                data.start_date,
                data.end_date,
                session=session,
            )

            if overlapping >= total_units:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No vehicles of this "
                        "type are available "
                        "for the selected "
                        "dates"
                    ),
                )

            item_name = (
                f"{item['brand']} "
                f"{item['model']}"
            )

            total_price = (
                float(
                    item["price_per_day"]
                )
                * days
            )

        booking_inner = Booking(
            booking_id=(
                f"booking_"
                f"{uuid.uuid4().hex[:12]}"
            ),
            user_id=user.user_id,
            booking_type=data.booking_type,
            item_id=data.item_id,
            item_name=item_name,
            start_date=data.start_date,
            end_date=data.end_date,
            total_price=round(
                total_price,
                2,
            ),
            status="pending",
            payment_status="pending",
            guests=data.guests,
            created_at=now_utc(),
        )

        document_inner = booking_inner.model_dump()

        # All timestamps (start_date, end_date, created_at)
        # are kept as native datetime objects — motor/pymongo
        # serialize these to BSON Date automatically — rather
        # than ISO strings. This lets count_overlapping_bookings()
        # compare them directly in MongoDB and keeps every
        # timestamp field consistently typed.
        await db.bookings.insert_one(
            document_inner,
            session=session,
        )

        return booking_inner

    if data.booking_type in (
        "hotel",
        "car",
    ):

        try:
            async with await client.start_session() as txn_session:
                async with txn_session.start_transaction():
                    booking = await _build_hotel_or_car_booking(
                        session=txn_session
                    )

        except HTTPException:
            raise

        except Exception:
            logger.warning(
                "MongoDB transactions unavailable "
                "(likely a standalone, non-replica-set "
                "deployment). Falling back to a "
                "best-effort, NON-ATOMIC check for %s "
                "booking %s — the overlap/inventory "
                "guarantee does not hold under "
                "concurrent requests on this "
                "deployment. Use a replica set (e.g. "
                "MongoDB Atlas) in production to close "
                "this window.",
                data.booking_type,
                data.item_id,
            )

            booking = await _build_hotel_or_car_booking(
                session=None
            )

        return booking

    # --------------------------------------------------------
    # FLIGHT
    # --------------------------------------------------------

    elif data.booking_type == "flight":

        flight = await db.flights.find_one(
            {
                "flight_id":
                    data.item_id,
                "available_seats": {
                    "$gte":
                        data.guests
                },
            },
            {"_id": 0},
        )

        if not flight:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Flight unavailable "
                    "or not enough seats"
                ),
            )

        result = (
            await db.flights.update_one(
                {
                    "flight_id":
                        data.item_id,
                    "available_seats": {
                        "$gte":
                            data.guests
                    },
                },
                {
                    "$inc": {
                        "available_seats":
                            -data.guests
                    }
                },
            )
        )

        if result.modified_count != 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Flight seats are "
                    "no longer available"
                ),
            )

        item_name = (
            f"{flight['from_city']} "
            f"to "
            f"{flight['to_city']}"
        )

        total_price = (
            float(
                flight["price"]
            )
            * data.guests
        )

    # --------------------------------------------------------
    # EXPERIENCE
    #
    # Capacity is enforced atomically with a single
    # find_one_and_update: the filter's $expr guard only
    # matches (and therefore only increments booked_guests)
    # when there's still room, so two concurrent requests can
    # never both succeed past capacity. No read-then-write
    # window, no transaction needed.
    # --------------------------------------------------------

    elif data.booking_type == "experience":

        item = await db.experiences.find_one_and_update(
            {
                "experience_id":
                    data.item_id,
                "available": True,
                "$expr": {
                    "$lte": [
                        {
                            "$add": [
                                "$booked_guests",
                                data.guests,
                            ]
                        },
                        "$capacity",
                    ]
                },
            },
            {
                "$inc": {
                    "booked_guests":
                        data.guests
                }
            },
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER,
        )

        if not item:

            exists = await db.experiences.find_one(
                {
                    "experience_id":
                        data.item_id,
                    "available": True,
                },
                {"_id": 0},
            )

            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Experience unavailable"
                    ),
                )

            raise HTTPException(
                status_code=409,
                detail=(
                    "Not enough experience "
                    "capacity available"
                ),
            )

        experience_capacity_reserved = True

        item_name = item["title"]

        total_price = (
            float(
                item["price"]
            )
            * data.guests
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid booking type",
        )

    booking = Booking(
        booking_id=(
            f"booking_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        booking_type=data.booking_type,
        item_id=data.item_id,
        item_name=item_name,
        start_date=data.start_date,
        end_date=data.end_date,
        total_price=round(
            total_price,
            2,
        ),
        status="pending",
        payment_status="pending",
        guests=data.guests,
        created_at=now_utc(),
    )

    document = booking.model_dump()

    # Kept as native datetimes (not ISO strings) for
    # the same reason as the hotel/car path above.
    try:

        await db.bookings.insert_one(
            document
        )

    except Exception:

        # If flight seats were already
        # reserved, restore them.
        if data.booking_type == "flight":
            await db.flights.update_one(
                {
                    "flight_id":
                        data.item_id
                },
                {
                    "$inc": {
                        "available_seats":
                            data.guests
                    }
                },
            )

        # If experience capacity was already
        # reserved, restore it.
        if experience_capacity_reserved:
            await db.experiences.update_one(
                {
                    "experience_id":
                        data.item_id
                },
                {
                    "$inc": {
                        "booked_guests":
                            -data.guests
                    }
                },
            )

        raise HTTPException(
            status_code=500,
            detail="Could not create booking",
        )

    return booking


@api_router.get(
    "/bookings",
    response_model=List[Booking],
)
async def get_bookings(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    query = (
        {}
        if user.is_admin
        else {
            "user_id":
                user.user_id
        }
    )

    bookings = await db.bookings.find(
        query,
        {"_id": 0},
    ).to_list(1000)

    for booking in bookings:

        booking["start_date"] = (
            parse_datetime(
                booking.get(
                    "start_date"
                )
            )
        )

        if booking.get(
            "end_date"
        ):
            booking["end_date"] = (
                parse_datetime(
                    booking["end_date"]
                )
            )

        booking["created_at"] = (
            parse_datetime(
                booking.get(
                    "created_at"
                )
            )
        )

    return bookings


@api_router.get(
    "/bookings/{booking_id}",
    response_model=Booking,
)
async def get_booking(
    booking_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    booking = await db.bookings.find_one(
        {
            "booking_id":
                booking_id
        },
        {"_id": 0},
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if (
        booking["user_id"]
        != user.user_id
        and not user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    booking["start_date"] = (
        parse_datetime(
            booking.get(
                "start_date"
            )
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
            booking.get(
                "created_at"
            )
        )
    )

    return booking


@api_router.post(
    "/bookings/{booking_id}/confirm"
)
async def confirm_booking(
    booking_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only an admin or the "
                "payment workflow can "
                "confirm a booking"
            ),
        )

    booking = await db.bookings.find_one(
        {
            "booking_id":
                booking_id
        },
        {"_id": 0},
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if booking.get(
        "status"
    ) == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cancelled booking",
        )

    await db.bookings.update_one(
        {
            "booking_id":
                booking_id
        },
        {
            "$set": {
                "status":
                    "confirmed"
            }
        },
    )

    return {
        "message":
            "Booking confirmed"
    }


@api_router.post(
    "/bookings/{booking_id}/cancel"
)
async def cancel_booking(
    booking_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    booking = await db.bookings.find_one(
        {
            "booking_id":
                booking_id
        },
        {"_id": 0},
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if (
        booking["user_id"]
        != user.user_id
        and not user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized",
        )

    if booking.get(
        "status"
    ) == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Booking already cancelled",
        )

    await db.bookings.update_one(
        {
            "booking_id":
                booking_id
        },
        {
            "$set": {
                "status":
                    "cancelled"
            }
        },
    )

    if booking.get(
        "booking_type"
    ) == "flight":
        await restore_flight_seats(
            booking
        )

    if booking.get(
        "booking_type"
    ) == "experience":
        await restore_experience_capacity(
            booking
        )

    return {
        "message":
            "Booking cancelled"
    }


# ============================================================
# REVIEW ROUTES
# ============================================================

@api_router.post(
    "/reviews",
    response_model=Review,
)
async def create_review(
    data: ReviewCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    await get_item(
        data.item_type,
        data.item_id,
    )

    # Only users with a confirmed booking,
    # where the stay/flight/experience has
    # actually happened, can leave a review.
    # Hotel/car use end_date (checkout/
    # return); flight/experience have no
    # end_date, so start_date (departure /
    # experience date) is the relevant one.
    date_field = (
        "end_date"
        if data.item_type in (
            "hotel",
            "car",
        )
        else "start_date"
    )

    completed_booking = (
        await db.bookings.find_one(
            {
                "user_id":
                    user.user_id,
                "booking_type":
                    data.item_type,
                "item_id":
                    data.item_id,
                "status":
                    "confirmed",
                date_field: {
                    "$lte":
                        now_utc()
                },
            },
            {"_id": 0},
        )
    )

    if not completed_booking:
        raise HTTPException(
            status_code=403,
            detail=(
                "You can only review "
                "items you have booked, "
                "that are confirmed, and "
                "whose stay, flight, or "
                "experience date has "
                "already passed"
            ),
        )

    existing_review = (
        await db.reviews.find_one(
            {
                "user_id":
                    user.user_id,
                "item_type":
                    data.item_type,
                "item_id":
                    data.item_id,
            },
            {"_id": 0},
        )
    )

    if existing_review:
        raise HTTPException(
            status_code=400,
            detail=(
                "You have already "
                "reviewed this item"
            ),
        )

    review = Review(
        review_id=(
            f"review_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        user_name=user.name,
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = review.model_dump()

    await db.reviews.insert_one(
        document
    )

    # Hotels and experiences carry a stored
    # `rating` field for cheap list/search
    # sorting. Keep it in sync so it doesn't
    # drift from the reviews collection.
    if data.item_type in (
        "hotel",
        "experience",
    ):

        collection = (
            db.hotels
            if data.item_type == "hotel"
            else db.experiences
        )

        id_field = (
            "hotel_id"
            if data.item_type == "hotel"
            else "experience_id"
        )

        pipeline = [
            {
                "$match": {
                    "item_type":
                        data.item_type,
                    "item_id":
                        data.item_id,
                }
            },
            {
                "$group": {
                    "_id": None,
                    "average_rating": {
                        "$avg":
                            "$rating"
                    },
                }
            },
        ]

        results = (
            await db.reviews.aggregate(
                pipeline
            ).to_list(1)
        )

        if results:
            await collection.update_one(
                {
                    id_field:
                        data.item_id
                },
                {
                    "$set": {
                        "rating": round(
                            float(
                                results[0].get(
                                    "average_rating",
                                    0,
                                )
                            ),
                            2,
                        )
                    }
                },
            )

    return review


@api_router.get(
    "/reviews/{item_type}/{item_id}",
    response_model=List[Review],
)
async def get_reviews(
    item_type: str,
    item_id: str,
):

    if item_type not in [
        "hotel",
        "flight",
        "car",
        "experience",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid item type",
        )

    reviews = await db.reviews.find(
        {
            "item_type":
                item_type,
            "item_id":
                item_id,
        },
        {"_id": 0},
    ).to_list(1000)

    for review in reviews:
        review["created_at"] = (
            parse_datetime(
                review.get(
                    "created_at"
                )
            )
        )

    return reviews


@api_router.get(
    "/reviews/{item_type}/{item_id}/summary"
)
async def review_summary(
    item_type: str,
    item_id: str,
):

    if item_type not in [
        "hotel",
        "flight",
        "car",
        "experience",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid item type",
        )

    pipeline = [
        {
            "$match": {
                "item_type":
                    item_type,
                "item_id":
                    item_id,
            }
        },
        {
            "$group": {
                "_id": None,
                "average_rating": {
                    "$avg":
                        "$rating"
                },
                "review_count": {
                    "$sum": 1
                },
            }
        },
    ]

    results = (
        await db.reviews.aggregate(
            pipeline
        ).to_list(1)
    )

    if not results:
        return {
            "average_rating": 0,
            "review_count": 0,
        }

    return {
        "average_rating": round(
            float(
                results[0].get(
                    "average_rating",
                    0,
                )
            ),
            2,
        ),
        "review_count": int(
            results[0].get(
                "review_count",
                0,
            )
        ),
    }


# ============================================================
# FAVORITE ROUTES
# ============================================================

@api_router.post(
    "/favorites",
    response_model=Favorite,
)
async def add_favorite(
    data: FavoriteCreate,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    await get_item(
        data.item_type,
        data.item_id,
    )

    existing = (
        await db.favorites.find_one(
            {
                "user_id":
                    user.user_id,
                "item_type":
                    data.item_type,
                "item_id":
                    data.item_id,
            },
            {"_id": 0},
        )
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Already favorite",
        )

    favorite = Favorite(
        favorite_id=(
            f"fav_"
            f"{uuid.uuid4().hex[:12]}"
        ),
        user_id=user.user_id,
        **data.model_dump(),
        created_at=now_utc(),
    )

    document = favorite.model_dump()

    try:
        await db.favorites.insert_one(
            document
        )
    except Exception as exc:

        if "duplicate" in str(
            exc
        ).lower():
            raise HTTPException(
                status_code=400,
                detail="Already favorite",
            )

        raise

    return favorite


@api_router.get(
    "/favorites",
    response_model=List[Favorite],
)
async def get_favorites(
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    favorites = (
        await db.favorites.find(
            {
                "user_id":
                    user.user_id
            },
            {"_id": 0},
        ).to_list(1000)
    )

    for favorite in favorites:
        favorite["created_at"] = (
            parse_datetime(
                favorite.get(
                    "created_at"
                )
            )
        )

    return favorites


@api_router.delete(
    "/favorites/{favorite_id}"
)
async def remove_favorite(
    favorite_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
):

    user = await get_current_user(
        request,
        session_token,
    )

    result = (
        await db.favorites.delete_one(
            {
                "favorite_id":
                    favorite_id,
                "user_id":
                    user.user_id,
            }
        )
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Favorite not found",
        )

    return {
        "message":
            "Favorite removed"
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "service":
            "Chillax Travel API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():

    try:
        await db.command(
            "ping"
        )

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:

        return JSONResponse(
            status_code=503,
            content={
                "status":
                    "unhealthy",
                "database":
                    "disconnected",
            },
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():

    logger.info(
        "Starting Chillax Travel API"
    )

    try:
        await db.command(
            "ping"
        )

        logger.info(
            "MongoDB connection successful"
        )

    except Exception:

        logger.exception(
            "MongoDB connection failed"
        )

        raise

    # --------------------------------------------------------
    # User indexes
    # --------------------------------------------------------

    await db.users.create_index(
        "email",
        unique=True,
    )

    # --------------------------------------------------------
    # Session indexes
    # --------------------------------------------------------

    await db.user_sessions.create_index(
        "session_token_hash",
        unique=True,
        sparse=True,
    )

    await db.user_sessions.create_index(
        "session_token",
        unique=True,
        sparse=True,
    )

    await db.user_sessions.create_index(
        "expires_at",
        expireAfterSeconds=0,
    )

    # --------------------------------------------------------
    # Booking indexes
    # --------------------------------------------------------

    await db.bookings.create_index(
        "booking_id",
        unique=True,
    )

    await db.bookings.create_index(
        [
            ("user_id", 1),
            ("created_at", -1),
        ]
    )

    await db.bookings.create_index(
        [
            ("booking_type", 1),
            ("item_id", 1),
            ("status", 1),
        ]
    )

    await db.bookings.create_index(
        [
            ("booking_type", 1),
            ("item_id", 1),
            ("status", 1),
            ("start_date", 1),
            ("end_date", 1),
        ]
    )

    # --------------------------------------------------------
    # Hotel
    # --------------------------------------------------------

    await db.hotels.create_index(
        "hotel_id",
        unique=True,
    )

    await db.hotels.create_index(
        [
            ("city", 1),
            ("available", 1),
        ]
    )

    # --------------------------------------------------------
    # Flights
    # --------------------------------------------------------

    await db.flights.create_index(
        "flight_id",
        unique=True,
    )

    await db.flights.create_index(
        [
            ("from_city", 1),
            ("to_city", 1),
        ]
    )

    # --------------------------------------------------------
    # Cars
    # --------------------------------------------------------

    await db.cars.create_index(
        "car_id",
        unique=True,
    )

    await db.cars.create_index(
        [
            ("city", 1),
            ("available", 1),
        ]
    )

    # --------------------------------------------------------
    # Experiences
    # --------------------------------------------------------

    await db.experiences.create_index(
        "experience_id",
        unique=True,
    )

    await db.experiences.create_index(
        [
            ("city", 1),
            ("available", 1),
        ]
    )

    # --------------------------------------------------------
    # Reviews
    # --------------------------------------------------------

    await db.reviews.create_index(
        [
            ("item_type", 1),
            ("item_id", 1),
        ]
    )

    await db.reviews.create_index(
        [
            ("user_id", 1),
            ("item_type", 1),
            ("item_id", 1),
        ],
        unique=True,
    )

    # --------------------------------------------------------
    # Favorites
    # --------------------------------------------------------

    await db.favorites.create_index(
        "favorite_id",
        unique=True,
    )

    await db.favorites.create_index(
        [
            ("user_id", 1),
            ("item_type", 1),
            ("item_id", 1),
        ],
        unique=True,
    )

    await bootstrap_admin()

    logger.info(
        "Chillax Travel API started"
    )


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def shutdown_db_client():

    logger.info(
        "Closing MongoDB connection"
    )

    client.close()


# ============================================================
# ROUTER
# ============================================================

app.include_router(
    api_router
)