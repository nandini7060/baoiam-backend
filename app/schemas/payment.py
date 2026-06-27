from pydantic import BaseModel
from typing import Optional


class PaymentOrderResponse(BaseModel):
    """Schema for the response after creating a Razorpay order."""
    order_id: str
    amount: int
    currency: str
    course_name: str


class PaymentStatusResponse(BaseModel):
    """Schema for checking payment status."""
    order_id: str
    status: str
    course_id: int
    user_id: int
