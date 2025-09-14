from pydantic import BaseModel, Field
from typing import Dict, List

class Candidate(BaseModel):
    university_registration_number: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    semester: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    skills_grouped: Dict[str, List[str]] = Field(default_factory=dict)
