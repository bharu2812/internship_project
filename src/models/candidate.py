from pydantic import BaseModel, Field

class Candidate(BaseModel):
    university_registration_number: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    semester: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    skills: list[str] = Field(default_factory=list)
