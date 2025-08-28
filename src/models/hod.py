from pydantic import BaseModel
from typing import List

from pydantic import BaseModel, EmailStr, validator, constr, Field
from typing import List


class HOD(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the HOD")
    email: EmailStr
    contact_number: str = Field(..., pattern=r'^\d{10}$', description="10 digit phone number")
    university_name: str = Field(..., min_length=1, description="University name")
    departments: List[str] = Field(..., min_items=1, description="List of departments")

    registration_year: str = Field(..., pattern=r'^(19|20)\d{2}$', description="4-digit registration year")

    from pydantic import field_validator

    @field_validator('departments')
    @classmethod
    def departments_not_empty(cls, v):
        if not v or not isinstance(v, list) or not all(v):
            raise ValueError('departments must be a non-empty list of non-empty strings')
        return v

    @field_validator('registration_year')
    @classmethod
    def registration_year_valid(cls, v):
        import datetime
        current_year = datetime.datetime.now().year
        try:
            year = int(v)
        except ValueError:
            raise ValueError('registration_year must be a 4-digit year')
        if year < 1900 or year > current_year:
            raise ValueError(f'registration_year must be between 1900 and {current_year}')
        return v