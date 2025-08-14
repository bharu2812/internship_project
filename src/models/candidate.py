from pydantic import BaseModel, Field

class Candidate(BaseModel):
    university_registration_number: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    university_name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    semester: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    projects: str = Field(..., min_length=1)
    skills: str = Field(..., min_length=1)
    certifications: str = Field(..., min_length=1)
    achievements: str = Field(..., min_length=1)
