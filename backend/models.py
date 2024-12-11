# models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class ProfileData(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    name: str
    profile_url: str
    skills: List[str]
    location: str
    education: Optional[dict] = None
    experience: Optional[List[dict]] = None
    contact_info: Optional[dict] = None

    class Config:
        populate_by_name = True  # Renamed from allow_population_by_field_name
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class User(BaseModel):
    email: str
    hashed_password: str

    class Config:
        from_attributes = True  # Renamed from orm_mode

class Token(BaseModel):
    access_token: str
    token_type: str