import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from scraper import LinkedInScraper
from processor import DataProcessor
from models import ProfileData, User, Token
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_jwt_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize FastAPI
app = FastAPI()

# CORS Configuration
origins = [
    "http://localhost:3000",
    # Add other allowed origins
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client.linkedin_scraper

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Authentication Dependencies
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_user(email: str):
    user = await db.users.find_one({"email": email})
    return User(**user) if user else None

async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None

async def get_current_user(token: str = Depends()):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user(email)
    if user is None:
        raise credentials_exception
    return user

# Models
class SearchCriteria(BaseModel):
    skills: List[str]
    location: str
    experience_level: str  # "fresher" or "experienced"
    job_title: Optional[str] = None
    education: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str

class TokenRequest(BaseModel):
    email: str
    password: str

# Initialize Scraper and Processor
scraper = LinkedInScraper()
processor = DataProcessor()

# Routes

@app.post("/register", response_model=User)
async def register(user: UserCreate):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = {"email": user.email, "hashed_password": hashed_password}
    result = await db.users.insert_one(new_user)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return User(**created_user)

@app.post("/login", response_model=Token)
async def login(form_data: TokenRequest):
    user = await authenticate_user(form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/search-profiles", response_model=List[ProfileData])
async def search_profiles(criteria: SearchCriteria, current_user: User = Depends(get_current_user)):
    try:
        raw_profiles = scraper.search_profiles(criteria)
        processed_profiles = processor.process_profiles(raw_profiles)
        # Optionally, integrate OpenAI API processing here
        # Save to MongoDB
        await db.profiles.insert_many([profile.dict() for profile in processed_profiles])
        return processed_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profile/{profile_id}", response_model=ProfileData)
async def get_profile_details(profile_id: str, current_user: User = Depends(get_current_user)):
    profile = await db.profiles.find_one({"_id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileData(**profile)

