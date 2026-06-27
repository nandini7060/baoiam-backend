from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import razorpay
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv

from app.db.database import get_db
from app.models.models import Course, Payment
from app.core.auth import get_current_user
from app.schemas.payment import PaymentOrderResponse, PaymentStatusResponse

load_dotenv()

router = APIRouter(tags=["Payments"])

# Razorpay client — keys loaded from .env, never hardcoded
client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET"),
))


# ──────────────────────────────────────────────
# 1. CREATE RAZORPAY ORDER
# ──────────────────────────────────────────────
@router.post("/payment/create-order", response_model=PaymentOrderResponse)
def create_order(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a Razorpay payment order for a course purchase."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Razorpay requires amount in paise (₹499 = 49900)
    amount_in_paise = int(course.price * 100)

    razorpay_order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"receipt_user{current_user.id}_course{course.id}",
        "payment_capture": 1,
    })

    # Save as pending — will update to success/failed via webhook
    new_payment = Payment(
        user_id=current_user.id,
        course_id=course.id,
        razorpay_order_id=razorpay_order["id"],
        amount=course.price,
        status="pending",
    )
    db.add(new_payment)
    db.commit()

    return {
        "order_id": razorpay_order["id"],
        "amount": amount_in_paise,
        "currency": "INR",
        "course_name": course.title,
    }


# ──────────────────────────────────────────────
# 2. RAZORPAY WEBHOOK
# ──────────────────────────────────────────────
@router.post("/payment/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive and verify Razorpay webhook events (payment.captured / payment.failed)."""
    # Read raw bytes — needed for HMAC verification
    body = await request.body()
    razorpay_signature = request.headers.get("x-razorpay-signature")

    if not razorpay_signature:
        raise HTTPException(status_code=400, detail="Signature missing")

    # HMAC verification — confirms request is genuinely from Razorpay
    secret = os.getenv("RAZORPAY_KEY_SECRET")
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # compare_digest prevents timing attacks
    if not hmac.compare_digest(expected_signature, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid signature — possible fraud attempt")

    payload = json.loads(body)
    event = payload.get("event")
    order_id = payload["payload"]["payment"]["entity"]["order_id"]

    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == order_id
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if event == "payment.captured":
        payment.status = "success"
    elif event == "payment.failed":
        payment.status = "failed"

    db.commit()

    # Return 200 so Razorpay stops retrying the webhook
    return {"status": "ok"}


# ──────────────────────────────────────────────
# 3. CHECK PAYMENT STATUS
# ──────────────────────────────────────────────
@router.get("/payment/status/{order_id}", response_model=PaymentStatusResponse)
def get_payment_status(
    order_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the current status of a payment order for the authenticated user."""
    # user_id check prevents one user seeing another's payment
    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == order_id,
        Payment.user_id == current_user.id,
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "order_id": order_id,
        "status": payment.status,
        "course_id": payment.course_id,
        "user_id": payment.user_id,
    }
