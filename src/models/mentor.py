from pydantic import BaseModel, EmailStr, Field

class Mentor(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the Mentor")
    email: EmailStr
    contact_number: str = Field(..., pattern=r'^\d{10}$', description="10 digit phone number")
    location: str = Field(..., min_length=1, description="Location of the mentor")

    from pydantic import field_validator

    @field_validator('location')
    @classmethod
    def location_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('location must be a non-empty string')
        return v.strip()
