from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    """Schema for creating a new course (admin only)."""
    title: str
    description: str
    price: float


class CourseResponse(BaseModel):
    """Schema for returning course data."""
    id: int
    title: str
    description: str
    price: float
    instructor_id: Optional[int] = None

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    """Schema for marking a lesson as completed."""
    lesson_id: int


class ProgressResponse(BaseModel):
    """Schema for returning course progress percentage."""
    course_id: int
    percent_complete: float
