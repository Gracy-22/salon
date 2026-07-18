from fastapi import FastAPI, APIRouter, HTTPException, Query, Form, Header, Depends, Request, UploadFile, File
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from zoneinfo import ZoneInfo
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import random
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
import requests

import storage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============================================================
# Constants
# ============================================================
SALON_OPEN_HOUR = 9   # 9:00 AM
SALON_CLOSE_HOUR = 21  # 9:00 PM
SLOT_GRANULARITY_MIN = 15  # slot start granularity
SALON_TZ = ZoneInfo("Asia/Kolkata")
OWNER_PIN = os.environ["OWNER_PIN"]
OWNER_TOKEN_SECRET = os.environ["OWNER_TOKEN_SECRET"]
OWNER_TOKEN_ALGORITHM = "HS256"
OWNER_TOKEN_EXPIRY_HOURS = 12
REMINDER_OFFSETS = {"24h": 1440, "3h": 180, "1h": 60, "15m": 15}

# ============================================================
# Seed Data
# ============================================================
SEED_SERVICES = [
    {"id": "svc-signature-cut", "name": "Signature Cut", "category": "Hair", "duration_min": 45, "price": 600, "description": "A precision haircut tailored to your face shape and style.", "icon": "Scissors"},
    {"id": "svc-beard-sculpt", "name": "Sharp Beard Sculpt", "category": "Beard", "duration_min": 30, "price": 350, "description": "Defined beard shaping with a hot towel finish.", "icon": "Wind"},
    {"id": "svc-gent-combo", "name": "The Gentleman's Combo", "category": "Hair + Beard", "duration_min": 60, "price": 850, "description": "Signature cut paired with a sharp beard sculpt.", "icon": "ScissorsLineDashed"},
    {"id": "svc-hair-spa", "name": "Botanical Hair Spa", "category": "Hair", "duration_min": 60, "price": 1200, "description": "Nourishing botanical scalp & hair therapy.", "icon": "Leaf"},
    {"id": "svc-hair-wash", "name": "Cleanse & Refresh", "category": "Hair", "duration_min": 20, "price": 250, "description": "Deep cleansing wash with a soothing scalp rinse.", "icon": "Droplets"},
    {"id": "svc-facial", "name": "Glow Facial Ritual", "category": "Skin", "duration_min": 60, "price": 1500, "description": "Brightening multi-step facial for a luminous finish.", "icon": "Sparkles"},
    {"id": "svc-face-wash", "name": "Express Face Cleanse", "category": "Skin", "duration_min": 15, "price": 200, "description": "Quick deep-clean to refresh and detoxify.", "icon": "Sun"},
    {"id": "svc-face-spa", "name": "Luxe Face Spa", "category": "Skin", "duration_min": 75, "price": 2200, "description": "Extended skin therapy with mask, massage and serum.", "icon": "Flower2"},
    {"id": "svc-head-massage", "name": "Serenity Head Massage", "category": "Wellness", "duration_min": 30, "price": 450, "description": "Pressure-point head and neck relaxation ritual.", "icon": "Hand"},
]

SEED_STYLISTS = [
    {
        "id": "stylist-elena",
        "name": "Elena Hart",
        "title": "Senior Stylist",
        "bio": "Specialising in luxury blowouts, modern color and editorial finishes.",
        "photo": "https://images.unsplash.com/photo-1582095133179-bfd08e2fc6b3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzV8MHwxfHNlYXJjaHwzfHxwb3J0cmFpdCUyMG9mJTIwZWxlZ2FudCUyMGhhaXIlMjBzdHlsaXN0JTIwc2Fsb258ZW58MHx8fHwxNzgyNjI3MjcxfDA&ixlib=rb-4.1.0&q=85",
        "services": ["svc-signature-cut", "svc-hair-spa", "svc-hair-wash", "svc-facial", "svc-face-wash", "svc-face-spa", "svc-head-massage"],
        "pin": "1234",
        "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)},
    },
    {
        "id": "stylist-sarah",
        "name": "Sarah Lin",
        "title": "Master Cutter",
        "bio": "Precision bobs, textured layers and clean architectural shapes.",
        "photo": "https://images.unsplash.com/photo-1675034741473-afed58a142e8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzV8MHwxfHNlYXJjaHw0fHxwb3J0cmFpdCUyMG9mJTIwZWxlZ2FudCUyMGhhaXIlMjBzdHlsaXN0JTIwc2Fsb258ZW58MHx8fHwxNzgyNjI3MjcxfDA&ixlib=rb-4.1.0&q=85",
        "services": ["svc-signature-cut", "svc-hair-spa", "svc-hair-wash", "svc-facial", "svc-face-wash", "svc-face-spa", "svc-head-massage"],
        "pin": "2345",
        "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)},
    },
    {
        "id": "stylist-michael",
        "name": "Michael Voss",
        "title": "Grooming Specialist",
        "bio": "Expert in men's grooming, beard architecture and head spa rituals.",
        "photo": "https://images.unsplash.com/photo-1560066984-138dadb4c035?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzV8MHwxfHNlYXJjaHwxfHxwb3J0cmFpdCUyMG9mJTIwZWxlZ2FudCUyMGhhaXIlMjBzdHlsaXN0JTIwc2Fsb258ZW58MHx8fHwxNzgyNjI3MjcxfDA&ixlib=rb-4.1.0&q=85",
        "services": ["svc-signature-cut", "svc-beard-sculpt", "svc-gent-combo", "svc-hair-wash", "svc-head-massage", "svc-face-wash"],
        "pin": "3456",
        "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)},
    },
]




def _demo_booking_docs_for_day(day) -> List[dict]:
    # Deterministic pseudo-random daily target so charts look natural while staying realistic.
    seed = day.toordinal()
    mixed = seed ^ (seed << 13)
    mixed ^= (mixed >> 17)
    mixed ^= (mixed << 5)
    random_component = abs(mixed) % 6201
    weekly_wave = [1800, -1200, 900, -650, 2100, -900, 450][day.weekday()]
    target_revenue = max(35000, min(41800, 35000 + random_component + weekly_wave))
    service_lookup = {svc["id"]: svc for svc in SEED_SERVICES}
    service_stylist_pairs = []
    for stylist in SEED_STYLISTS:
        for service_id in stylist["services"]:
            service = service_lookup[service_id]
            service_stylist_pairs.append((service, stylist))
    service_stylist_pairs.sort(key=lambda pair: pair[0]["price"], reverse=True)

    docs = []
    total = 0
    index = 0
    while total < target_revenue:
        remaining = target_revenue - total
        affordable = [pair for pair in service_stylist_pairs if pair[0]["price"] <= remaining]
        service, stylist = affordable[(day.day + index) % len(affordable)] if affordable else service_stylist_pairs[-1]
        start_min = (9 * 60) + ((index * 30) % (12 * 60))
        start_time = _minutes_to_t(start_min)
        end_time = _minutes_to_t(start_min + service["duration_min"])
        docs.append({
            "id": f"demo-historical-{day.isoformat()}-{index}",
            "service_id": service["id"],
            "stylist_id": stylist["id"],
            "date": day.isoformat(),
            "start_time": start_time,
            "end_time": end_time,
            "duration_min": service["duration_min"],
            "customer_name": f"Demo Client {day.strftime('%j')}-{index + 1}",
            "customer_phone": f"+9198{day.strftime('%j')}{index:04d}",
            "notes": "Demo historical booking for owner analytics",
            "whatsapp_optin": False,
            "whatsapp_status": "skipped",
            "whatsapp_error": "Demo data",
            "status": "done",
            "reminders_sent": [],
            "created_at": datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
            "demo_seed": True,
            "salon_id": "salon-main",
        })
        total += float(service["price"])
        index += 1
    return docs

# ============================================================
# Models
# ============================================================
class Service(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    category: str
    duration_min: int
    price: float
    description: str
    icon: str


    is_active: Optional[bool] = True
class Stylist(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    title: str
    bio: str
    photo: str
    services: List[str]
    working_hours: Optional[dict] = None
    salon_id: Optional[str] = None

    phone: Optional[str] = ""
    login_phone: Optional[str] = ""
    is_active: Optional[bool] = True

class BookingCreate(BaseModel):
    service_id: str
    stylist_id: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM (24h)
    customer_name: str
    customer_phone: str
    notes: Optional[str] = ""
    whatsapp_optin: Optional[bool] = True


class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    salon_id: Optional[str] = None
    service_id: str
    stylist_id: str
    date: str
    start_time: str
    end_time: str
    duration_min: int
    customer_name: str
    customer_phone: str
    notes: str = ""
    whatsapp_optin: bool = True
    whatsapp_status: str = "pending"  # pending | sent | failed | skipped
    whatsapp_error: Optional[str] = None
    status: str = "upcoming"  # upcoming | done | no_show | cancelled
    reminders_sent: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    manage_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    manage_url: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancellation_reason_note: Optional[str] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[str] = None



class BookingResponse(BaseModel):
    booking: Booking
    service: Service
    stylist: Stylist


# ============================================================
# Helpers
# ============================================================
def _t_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_t(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


async def _get_service(service_id: str) -> dict:
    svc = await db.services.find_one({"id": service_id}, {"_id": 0})
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc


async def _get_stylist(stylist_id: str) -> dict:
    st = await db.stylists.find_one({"id": stylist_id}, {"_id": 0})
    if not st:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return st


# ============================================================
# Twilio WhatsApp
# ============================================================
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")  # e.g. "whatsapp:+1415..."
TWILIO_CONFIRMATION_TEMPLATE_SID = os.environ.get("TWILIO_CONFIRMATION_TEMPLATE_SID")
TWILIO_REMINDER_TEMPLATE_SID = os.environ.get("TWILIO_REMINDER_TEMPLATE_SID")
TWILIO_OTP_TEMPLATE_SID = os.environ.get("TWILIO_OTP_TEMPLATE_SID")
OWNER_PHONE = os.environ.get("OWNER_PHONE", "8511111593")
SALON_NAME = os.environ.get("SALON_NAME", "Sandy Hair Saloon")

_twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    _twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def _normalize_whatsapp_to(phone: str) -> str:
    p = phone.strip().replace(" ", "").replace("-", "")
    if not p.startswith("+"):
        # Default to India country code if not provided
        p = "+91" + p.lstrip("0")
    return f"whatsapp:{p}"


def _format_date_human(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a, %d %b %Y")
    except Exception:
        return date_str


def _format_time_human(time_str: str) -> str:
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%-I:%M %p")
    except Exception:
        return time_str


def _send_whatsapp_template(to_phone: str, content_sid: str, variables: dict) -> tuple[bool, Optional[str]]:
    if not _twilio_client or not TWILIO_WHATSAPP_FROM:
        return False, "Twilio not configured"
    try:
        import json as _json
        _twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=_normalize_whatsapp_to(to_phone),
            content_sid=content_sid,
            content_variables=_json.dumps(variables),
        )
        return True, None
    except Exception as e:
        return False, str(e)


def send_whatsapp_otp(to_phone: str, otp_code: str) -> tuple[str, Optional[str]]:
    if not _twilio_client or not TWILIO_WHATSAPP_FROM:
        return "skipped", "Twilio not configured"
    if TWILIO_OTP_TEMPLATE_SID:
        ok, err = _send_whatsapp_template(to_phone, TWILIO_OTP_TEMPLATE_SID, {"1": otp_code})
        if ok:
            return "sent", None
        logger.warning(f"OTP template failed, falling back to free-text: {err}")
    body = f"Your {SALON_NAME} login OTP is {otp_code}. Valid for 5 minutes. Do not share it."
    try:
        _twilio_client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=_normalize_whatsapp_to(to_phone), body=body)
        return "sent", None
    except Exception as e:
        return "failed", str(e)


def send_whatsapp_confirmation(booking: dict, service: dict, stylist: dict) -> tuple[str, Optional[str]]:
    """Returns (status, error). status in {sent, failed, skipped}."""
    if not _twilio_client or not TWILIO_WHATSAPP_FROM:
        return "skipped", "Twilio not configured"

    first_name = booking["customer_name"].split()[0]
    date_h = _format_date_human(booking["date"])
    manage_line = f"\nManage your booking: {booking.get('manage_url')}" if booking.get("manage_url") else ""
    body = (
        f"Hi {first_name}, your Maison Aurelle booking is confirmed.\n\n"
        f"Service: {service['name']} ({service['duration_min']} min)\n"
        f"Stylist: {stylist['name']}\n"
        f"Date: {date_h}\n"
        f"Time: {booking['start_time']} - {booking['end_time']}\n"
        f"Total: \u20b9{int(service['price'])}\n"
        f"Reference: {booking['id'][:8].upper()}\n"
        f"{manage_line}\n\n"
        f"Please arrive 5 minutes early. You can reschedule or cancel from the link above."
    )

    # Try template first if configured
    if TWILIO_CONFIRMATION_TEMPLATE_SID:
        variables = {
            "first_name": first_name,
            "appointment_date": date_h,
            "appointment_time": _format_time_human(booking["start_time"]),
            "service_name": service["name"],
            "stylist_name": stylist["name"],
        }
        ok, err = _send_whatsapp_template(booking["customer_phone"], TWILIO_CONFIRMATION_TEMPLATE_SID, variables)
        if ok:
            logger.info(f"WhatsApp confirmation (template) sent to {booking['customer_phone']}")
            return "sent", None
        logger.warning(f"Template send failed, falling back to free-text: {err}")

    # Fallback to free-text (sandbox / unapproved templates)
    try:
        msg = _twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=_normalize_whatsapp_to(booking["customer_phone"]),
            body=body,
        )
        logger.info(f"WhatsApp sent sid={msg.sid}")
        return "sent", None
    except TwilioRestException as e:
        return "failed", f"{e.code}: {e.msg}"
    except Exception as e:
        return "failed", str(e)


def _base_url_from_request(request: Optional[Request] = None) -> str:
    public_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
    if public_url:
        return public_url
    if request:
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_proto = request.headers.get("x-forwarded-proto", "https")
        if forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        origin = request.headers.get("origin") or request.headers.get("referer")
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return ""


def _manage_url(token: str, request: Optional[Request] = None) -> Optional[str]:
    base = _base_url_from_request(request)
    return f"{base}/manage/{token}" if base else None


async def _ensure_manage_token(booking: dict, request: Optional[Request] = None) -> dict:
    token = booking.get("manage_token") or str(uuid.uuid4())
    url = booking.get("manage_url") or _manage_url(token, request)
    update = {"manage_token": token}
    if url:
        update["manage_url"] = url
    await db.bookings.update_one({"id": booking["id"]}, {"$set": update})
    booking.update(update)
    return booking


async def _create_owner_notification(kind: str, booking: dict, message: str) -> None:
    await db.owner_notifications.insert_one({
        "id": str(uuid.uuid4()),
        "type": kind,
        "booking_id": booking.get("id"),
        "customer_name": booking.get("customer_name"),
        "customer_phone": booking.get("customer_phone"),
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def _send_whatsapp_message(to_phone: str, body: str) -> bool:
    if not _twilio_client or not TWILIO_WHATSAPP_FROM:
        return False
    try:
        _twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=_normalize_whatsapp_to(to_phone),
            body=body,
        )
        return True
    except Exception as e:
        logger.error(f"WhatsApp reminder failed: {e}")
        return False


def send_whatsapp_no_show_followup(booking: dict, service: dict, stylist: dict) -> tuple[str, Optional[str]]:
    """Best-effort WhatsApp follow-up for no-show bookings. Returns (status, error)."""
    if not _twilio_client or not TWILIO_WHATSAPP_FROM:
        return "skipped", "Twilio not configured"
    first_name = booking.get("customer_name", "there").split()[0]
    body = (
        f"Hi {first_name}, we missed you at Maison Aurelle today.\n\n"
        f"Your appointment for {service.get('name', 'your service')} with {stylist.get('name', 'your stylist')} "
        f"on {_format_date_human(booking.get('date', ''))} at {_format_time_human(booking.get('start_time', ''))} was marked as a no-show.\n"
        f"Ref: {booking.get('id', '')[:8].upper()}\n\n"
        f"If you would like to book again, please use the booking link or reply to this message."
    )
    try:
        _twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=_normalize_whatsapp_to(booking["customer_phone"]),
            body=body,
        )
        logger.info(f"No-show WhatsApp sent for booking {booking.get('id', '')[:8]}")
        return "sent", None
    except TwilioRestException as e:
        return "failed", f"{e.code}: {e.msg}"
    except Exception as e:
        return "failed", str(e)


def _booking_local_dt(b: dict) -> datetime:
    return datetime.strptime(f"{b['date']} {b['start_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=SALON_TZ)


async def run_reminder_tick():
    """Runs every minute. Sends WhatsApp reminders at 24h, 3h, 1h, 15m before each booking."""
    try:
        now = datetime.now(SALON_TZ)
        # Pre-filter to a window of 25h ahead
        horizon = now + timedelta(minutes=1441)
        bookings = await db.bookings.find(
            {
                "status": "upcoming",
                "whatsapp_optin": True,
                "date": {"$gte": now.strftime("%Y-%m-%d"), "$lte": horizon.strftime("%Y-%m-%d")},
            },
            {"_id": 0},
        ).to_list(1000)

        services_cache: dict = {}
        stylists_cache: dict = {}

        for b in bookings:
            try:
                b_dt = _booking_local_dt(b)
            except Exception:
                continue
            minutes_until = (b_dt - now).total_seconds() / 60.0
            if minutes_until <= 0:
                continue
            sent = set(b.get("reminders_sent") or [])
            for key, offset in REMINDER_OFFSETS.items():
                if key in sent:
                    continue
                # Fire when within (offset - 0.5, offset + 0.5) minutes window
                if offset - 0.5 <= minutes_until <= offset + 0.5:
                    if b["service_id"] not in services_cache:
                        services_cache[b["service_id"]] = await db.services.find_one({"id": b["service_id"]}, {"_id": 0})
                    if b["stylist_id"] not in stylists_cache:
                        stylists_cache[b["stylist_id"]] = await db.stylists.find_one({"id": b["stylist_id"]}, {"_id": 0})
                    service = services_cache[b["service_id"]] or {}
                    stylist = stylists_cache[b["stylist_id"]] or {}
                    pretty = {"24h": "in 24 hours", "3h": "in 3 hours", "1h": "in 1 hour", "15m": "in 15 minutes"}[key]
                    date_h = _format_date_human(b['date'])
                    body = (
                        f"Reminder: your Maison Aurelle appointment is {pretty}.\n\n"
                        f"Service: {service.get('name','-')}\n"
                        f"Stylist: {stylist.get('name','-')}\n"
                        f"When: {date_h} at {b['start_time']}\n"
                        f"Ref: {b['id'][:8].upper()}\n"
                        f"Manage: {b.get('manage_url', '')}\n"
                    )
                    ok = False
                    if TWILIO_REMINDER_TEMPLATE_SID:
                        variables = {
                            "customer_name": b.get("customer_name", "Guest"),
                            "reminder_time_label": pretty,
                            "appointment_date": date_h,
                            "appointment_time": _format_time_human(b["start_time"]),
                            "service_name": service.get("name", "-"),
                            "stylist_name": stylist.get("name", "-"),
                        }
                        ok, err = _send_whatsapp_template(b["customer_phone"], TWILIO_REMINDER_TEMPLATE_SID, variables)
                        if not ok:
                            logger.warning(f"Reminder template failed ({err}); falling back to text")
                    if not ok:
                        ok = _send_whatsapp_message(b["customer_phone"], body)
                    if ok:
                        await db.bookings.update_one({"id": b["id"]}, {"$addToSet": {"reminders_sent": key}})
                        logger.info(f"Reminder {key} sent for booking {b['id'][:8]}")
    except Exception as e:
        logger.error(f"Reminder tick error: {e}")


_scheduler: Optional[AsyncIOScheduler] = None


# ============================================================
# Routes
# ============================================================
@api_router.get("/")
async def root():
    return {"message": "Salon Booking API"}


@api_router.get("/services", response_model=List[Service])
async def list_services(salon_id: Optional[str] = Query(None)):
    docs = await db.services.find({"is_active": {"$ne": False}}, {"_id": 0}).to_list(100)
    if not salon_id:
        return docs
    overrides = await db.salon_services.find({"salon_id": salon_id}, {"_id": 0}).to_list(500)
    override_by_svc = {o["service_id"]: o for o in overrides}
    result = []
    for svc in docs:
        entry = override_by_svc.get(svc["id"], {})
        if not entry.get("is_offered", True):
            continue
        price_override = entry.get("price_override")
        if price_override not in (None, ""):
            svc = {**svc, "price": float(price_override)}
        result.append(svc)
    return result


@api_router.get("/stylists", response_model=List[Stylist])
async def list_stylists(service_id: Optional[str] = Query(None), salon_id: Optional[str] = Query(None)):
    query: dict = {"is_active": {"$ne": False}}
    if service_id:
        query["services"] = service_id
    if salon_id:
        query["salon_id"] = salon_id
    docs = await db.stylists.find(query, {"_id": 0, "pin": 0}).to_list(100)
    return docs


@api_router.get("/availability")
async def get_availability(
    stylist_id: str = Query(...),
    service_id: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
):
    service = await _get_service(service_id)
    stylist = await _get_stylist(stylist_id)
    slots = await _compute_stylist_slots(stylist, service, date)
    return {
        "date": date,
        "stylist_id": stylist_id,
        "service_id": service_id,
        "duration_min": service["duration_min"],
        "slots": slots,
    }


async def _compute_stylist_slots(stylist: dict, service: dict, date: str) -> List[dict]:
    duration = service["duration_min"]
    try:
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    wh = (stylist.get("working_hours") or {}).get(str(weekday))
    if not wh:
        return []
    open_min = _t_to_minutes(wh["open"])
    close_min = _t_to_minutes(wh["close"])
    existing = await db.bookings.find(
        {"stylist_id": stylist["id"], "date": date, "status": {"$ne": "cancelled"}},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(500)
    blocked = [(_t_to_minutes(b["start_time"]), _t_to_minutes(b["end_time"])) for b in existing]
    blocks = await db.stylist_blocks.find(
        {"stylist_id": stylist["id"], "date": date},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(500)
    blocked += [(_t_to_minutes(b["start_time"]), _t_to_minutes(b["end_time"])) for b in blocks]
    recurring_blocks = await db.recurring_blocks.find(
        {"stylist_id": stylist["id"], "weekdays": weekday},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(200)
    blocked += [(_t_to_minutes(b["start_time"]), _t_to_minutes(b["end_time"])) for b in recurring_blocks]
    slots = []
    cursor = open_min
    while cursor + duration <= close_min:
        end = cursor + duration
        overlap = any(not (end <= s or cursor >= e) for (s, e) in blocked)
        slots.append({"start_time": _minutes_to_t(cursor), "end_time": _minutes_to_t(end), "available": not overlap})
        cursor += SLOT_GRANULARITY_MIN
    return slots


@api_router.get("/availability/salon-slots")
async def salon_slots(salon_id: str = Query(...), service_id: str = Query(...), date: str = Query(...)):
    """Union of available slots across all stylists at a salon offering the service."""
    salon = await db.salons.find_one({"id": salon_id, "is_active": {"$ne": False}}, {"_id": 0})
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    menu = await db.salon_services.find_one({"salon_id": salon_id, "service_id": service_id}, {"_id": 0})
    if menu and menu.get("is_offered") is False:
        return {"salon_id": salon_id, "service_id": service_id, "date": date, "slots": []}
    service = await _get_service(service_id)
    stylists = await db.stylists.find(
        {"salon_id": salon_id, "services": service_id, "is_active": {"$ne": False}},
        {"_id": 0, "pin": 0},
    ).to_list(200)
    per_slot: dict = {}
    for s in stylists:
        for slot in await _compute_stylist_slots(s, service, date):
            if slot.get("available"):
                per_slot[slot["start_time"]] = slot
    return {
        "salon_id": salon_id,
        "service_id": service_id,
        "date": date,
        "duration_min": service["duration_min"],
        "slots": sorted(per_slot.values(), key=lambda x: x["start_time"]),
    }


@api_router.get("/availability/by-slot")
async def availability_by_slot(salon_id: str = Query(...), service_id: str = Query(...), date: str = Query(...), start_time: str = Query(...)):
    """Return stylists at a salon who are free at the given date/start_time and offer the service."""
    service = await _get_service(service_id)
    duration = service["duration_min"]
    stylists = await db.stylists.find(
        {"salon_id": salon_id, "services": service_id, "is_active": {"$ne": False}},
        {"_id": 0, "pin": 0},
    ).to_list(200)
    free = []
    for s in stylists:
        slots = await _compute_stylist_slots(s, service, date)
        match = next((slot for slot in slots if slot["start_time"] == start_time), None)
        if match and match.get("available"):
            free.append(s)
    return {"salon_id": salon_id, "service_id": service_id, "date": date, "start_time": start_time, "duration_min": duration, "stylists": free}


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())[-10:]


async def _ensure_customer_profile_from_booking(booking: dict) -> None:
    phone = _normalize_phone(booking.get("customer_phone", ""))
    if not phone:
        return
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.customer_profiles.find_one({"customer_phone": phone}, {"_id": 0})
    base = {
        "customer_phone": phone,
        "customer_name": booking.get("customer_name", "").strip(),
        "updated_at": now,
    }
    if existing:
        await db.customer_profiles.update_one({"customer_phone": phone}, {"$set": base, "$setOnInsert": {"created_at": now}}, upsert=True)
    else:
        await db.customer_profiles.update_one(
            {"customer_phone": phone},
            {"$set": {**base, "birthday": "", "hair_type": "", "product_allergies": "", "preferences": "", "stylist_notes": "", "preferred_stylist_id": "", "created_at": now}},
            upsert=True,
        )


async def _build_customer_profile(phone: str) -> dict:
    normalized = _normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Valid customer phone is required")
    profile = await db.customer_profiles.find_one({"customer_phone": normalized}, {"_id": 0}) or {"customer_phone": normalized, "customer_name": "", "birthday": "", "hair_type": "", "product_allergies": "", "preferences": "", "stylist_notes": "", "preferred_stylist_id": ""}
    visits = await db.bookings.find({"customer_phone": {"$regex": f"{normalized}$"}}, {"_id": 0}).sort("date", -1).to_list(500)
    service_ids = list({v["service_id"] for v in visits})
    stylist_ids = list({v["stylist_id"] for v in visits})
    services = await _services_by_id(service_ids)
    stylists = await _stylists_by_id(stylist_ids)
    enriched = []
    lifetime_spend = 0.0
    stylist_counts = {}
    for visit in visits:
        service = services.get(visit["service_id"], {})
        stylist = stylists.get(visit["stylist_id"], {})
        amount = float(service.get("price", 0)) if visit.get("status") in {"done", "upcoming"} else 0.0
        lifetime_spend += amount
        stylist_counts[visit["stylist_id"]] = stylist_counts.get(visit["stylist_id"], 0) + 1
        enriched.append({
            "id": visit["id"],
            "date": visit["date"],
            "service_id": visit["service_id"],
            "service_name": service.get("name", visit["service_id"]),
            "stylist_id": visit["stylist_id"],
            "stylist_name": stylist.get("name", visit["stylist_id"]),
            "amount_paid": amount,
            "status": visit.get("status", "upcoming"),
        })
    auto_preferred_id = max(stylist_counts, key=stylist_counts.get) if stylist_counts else ""
    preferred_id = profile.get("preferred_stylist_id") or auto_preferred_id
    preferred_stylist = stylists.get(preferred_id, {}) if preferred_id else {}
    milestones = [25000, 50000, 100000, 200000]
    next_milestone = next((m for m in milestones if lifetime_spend < m), None)
    return {
        **profile,
        "customer_phone": normalized,
        "visit_history": enriched,
        "visit_count": len(enriched),
        "lifetime_spend": lifetime_spend,
        "loyalty_next_milestone": next_milestone,
        "loyalty_progress": 100 if next_milestone is None else min(100, round((lifetime_spend / next_milestone) * 100, 1)),
        "auto_preferred_stylist_id": auto_preferred_id,
        "preferred_stylist_id": preferred_id,
        "preferred_stylist_name": preferred_stylist.get("name", ""),
        "preferred_stylist_manual": bool(profile.get("preferred_stylist_id")),
    }


async def _search_customer_profiles(q: Optional[str] = None) -> List[dict]:
    query = (q or "").strip()
    if not query:
        rows = await db.customer_profiles.find({}, {"_id": 0}).sort("customer_name", 1).limit(200).to_list(200)
        seen = {r["customer_phone"] for r in rows}
        booking_rows = await db.bookings.find({}, {"_id": 0, "customer_phone": 1, "customer_name": 1}).sort("created_at", -1).limit(500).to_list(500)
        for booking in booking_rows:
            normalized = _normalize_phone(booking.get("customer_phone", ""))
            if normalized and normalized not in seen:
                await _ensure_customer_profile_from_booking(booking)
                rows.append(await db.customer_profiles.find_one({"customer_phone": normalized}, {"_id": 0}))
                seen.add(normalized)
            if len(rows) >= 200:
                break
        return rows
    phone = _normalize_phone(query)
    # Escape regex special characters in query to prevent regex errors
    escaped_query = re.escape(query)
    escaped_phone = re.escape(phone) if phone else ""
    filters = [{"customer_name": {"$regex": escaped_query, "$options": "i"}}]
    if phone:
        filters.append({"customer_phone": {"$regex": f"{escaped_phone}$"}})
    rows = await db.customer_profiles.find({"$or": filters}, {"_id": 0}).limit(20).to_list(20)
    seen = {r["customer_phone"] for r in rows}
    booking_filter = {"$or": [{"customer_name": {"$regex": escaped_query, "$options": "i"}}, {"customer_phone": {"$regex": f"{escaped_phone}$"}}]} if phone else {"customer_name": {"$regex": escaped_query, "$options": "i"}}
    booking_rows = await db.bookings.find(booking_filter, {"_id": 0}).limit(50).to_list(50)
    for booking in booking_rows:
        normalized = _normalize_phone(booking.get("customer_phone", ""))
        if normalized and normalized not in seen:
            await _ensure_customer_profile_from_booking(booking)
            rows.append(await db.customer_profiles.find_one({"customer_phone": normalized}, {"_id": 0}))
            seen.add(normalized)
        if len(rows) >= 20:
            break
    return rows


@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(payload: BookingCreate, request: Request):
    service = await _get_service(payload.service_id)
    stylist = await _get_stylist(payload.stylist_id)

    if payload.service_id not in stylist["services"]:
        raise HTTPException(status_code=400, detail="This stylist does not offer the selected service")

    stylist_salon_id = stylist.get("salon_id") or DEFAULT_SALON_ID
    salon_menu_doc = await db.salon_services.find_one({"salon_id": stylist_salon_id, "service_id": payload.service_id}, {"_id": 0})
    if salon_menu_doc and salon_menu_doc.get("is_offered") is False:
        raise HTTPException(status_code=400, detail="This service is not offered at that salon location")
    if salon_menu_doc and salon_menu_doc.get("price_override") not in (None, ""):
        service = {**service, "price": float(salon_menu_doc["price_override"])}

    try:
        booking_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if booking_date < datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Cannot book in the past")

    # Enforce per-salon booking window (max days in advance)
    salon_doc = await db.salons.find_one({"id": stylist_salon_id}, {"_id": 0, "booking_window_days": 1})
    window_days = int((salon_doc or {}).get("booking_window_days") or 30)
    latest_allowed = datetime.now(timezone.utc).date() + timedelta(days=window_days)
    if booking_date > latest_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"This salon accepts bookings up to {window_days} days in advance. Please pick a date on or before {latest_allowed.isoformat()}.",
        )

    try:
        start_min = _t_to_minutes(payload.start_time)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start_time. Use HH:MM")

    duration = service["duration_min"]
    end_min = start_min + duration

    if start_min < SALON_OPEN_HOUR * 60 or end_min > SALON_CLOSE_HOUR * 60:
        raise HTTPException(status_code=400, detail="Slot outside salon hours")

    # Concurrency safety: re-check overlap
    existing = await db.bookings.find(
        {"stylist_id": payload.stylist_id, "date": payload.date, "status": {"$ne": "cancelled"}},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(500)
    for b in existing:
        s, e = _t_to_minutes(b["start_time"]), _t_to_minutes(b["end_time"])
        if not (end_min <= s or start_min >= e):
            raise HTTPException(status_code=409, detail="Slot just got booked. Please pick another.")

    if not payload.customer_name.strip() or not payload.customer_phone.strip():
        raise HTTPException(status_code=400, detail="Name and phone are required")

    booking = Booking(
        salon_id=stylist.get("salon_id") or DEFAULT_SALON_ID,
        service_id=payload.service_id,
        stylist_id=payload.stylist_id,
        date=payload.date,
        start_time=_minutes_to_t(start_min),
        end_time=_minutes_to_t(end_min),
        duration_min=duration,
        customer_name=payload.customer_name.strip(),
        customer_phone=payload.customer_phone.strip(),
        notes=(payload.notes or "").strip(),
        whatsapp_optin=bool(payload.whatsapp_optin),
    )

    booking.manage_url = _manage_url(booking.manage_token, request)

    # Send WhatsApp confirmation (best-effort)
    if booking.whatsapp_optin:
        status, err = send_whatsapp_confirmation(booking.model_dump(), service, stylist)
        booking.whatsapp_status = status
        booking.whatsapp_error = err
    else:
        booking.whatsapp_status = "skipped"

    await db.bookings.insert_one(booking.model_dump())
    await _ensure_customer_profile_from_booking(booking.model_dump())
    return BookingResponse(booking=booking, service=Service(**service), stylist=Stylist(**stylist))


@api_router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: str):
    b = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    service = await _get_service(b["service_id"])
    stylist = await _get_stylist(b["stylist_id"])
    return BookingResponse(booking=Booking(**b), service=Service(**service), stylist=Stylist(**stylist))




class OwnerServiceUpsert(BaseModel):
    name: str
    category: str = "Hair"
    duration_min: int = Field(..., ge=5, le=480)
    price: float = Field(..., ge=0)
    description: str = ""
    icon: str = "Scissors"
    is_active: bool = True


class OwnerStylistUpsert(BaseModel):
    name: str
    title: str = "Stylist"
    bio: str = ""
    photo: str = ""
    phone: Optional[str] = ""
    login_phone: Optional[str] = ""
    services: List[str] = []
    salon_id: Optional[str] = None
    is_active: bool = True


class OwnerSalonUpsert(BaseModel):
    name: str
    slug: Optional[str] = None
    address: str = ""
    city: str = ""
    phone: str = ""
    timezone: str = "Asia/Kolkata"
    working_hours: Optional[dict] = None
    booking_window_days: int = Field(default=30, ge=1, le=365)
    is_active: bool = True


class OwnerSalonMenuEntry(BaseModel):
    service_id: str
    is_offered: bool = True
    price_override: Optional[float] = None


class OwnerSalonMenuBulkUpdate(BaseModel):
    entries: List[OwnerSalonMenuEntry]


class OwnerManagerUpsert(BaseModel):
    name: str
    phone: str = ""
    login_phone: str
    salon_id: str
    is_active: bool = True

# ============================================================
# Stylist portal
# ============================================================
class StylistLoginPayload(BaseModel):
    stylist_id: str
    pin: str


class BlockUpsert(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str
    end_time: str
    status: str  # busy | leave | break
    label: Optional[str] = None


class RecurringBlockUpsert(BaseModel):
    weekdays: List[int]  # 0..6, Mon..Sun
    start_time: str
    end_time: str
    status: str = "break"  # busy | break
    label: Optional[str] = "Break"


class CustomerProfileUpdate(BaseModel):
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    birthday: Optional[str] = None  # YYYY-MM-DD
    hair_type: Optional[str] = None
    product_allergies: Optional[str] = None
    preferences: Optional[str] = None
    stylist_notes: Optional[str] = None
    preferred_stylist_id: Optional[str] = None


@api_router.get("/stylist/{stylist_id}/customers/search")
async def stylist_customer_search(stylist_id: str, q: Optional[str] = Query(None)):
    await _get_stylist(stylist_id)
    rows = await _search_customer_profiles(q)
    return {"customers": rows}


@api_router.get("/stylist/{stylist_id}/customers/{phone}")
async def stylist_customer_profile(stylist_id: str, phone: str):
    await _get_stylist(stylist_id)
    return await _build_customer_profile(phone)


@api_router.patch("/stylist/{stylist_id}/customers/{phone}")
async def stylist_update_customer_profile(stylist_id: str, phone: str, payload: CustomerProfileUpdate):
    await _get_stylist(stylist_id)
    normalized = _normalize_phone(phone)
    update = payload.model_dump(exclude_unset=True)
    update["customer_phone"] = normalized
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    if update.get("preferred_stylist_id"):
        await _get_stylist(update["preferred_stylist_id"])
    await db.customer_profiles.update_one({"customer_phone": normalized}, {"$set": update, "$setOnInsert": {"created_at": update["updated_at"]}}, upsert=True)
    return await _build_customer_profile(normalized)


class WorkingHoursUpdate(BaseModel):
    weekday: int  # 0..6
    open: Optional[str] = None
    close: Optional[str] = None
    closed: bool = False


class BookingStatusUpdate(BaseModel):
    status: str  # done | no_show | upcoming | cancelled

async def _apply_booking_status(booking_id: str, status: str, extra_filter: Optional[dict] = None) -> dict:
    query = {"id": booking_id}
    if extra_filter:
        query.update(extra_filter)
    existing = await db.bookings.find_one(query, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_doc = {"status": status}
    if status == "no_show":
        update_doc["no_show_marked_at"] = datetime.now(timezone.utc).isoformat()

    await db.bookings.update_one(query, {"$set": update_doc})
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})

    if status == "no_show" and existing.get("status") != "no_show" and booking.get("whatsapp_optin", True):
        service = await db.services.find_one({"id": booking["service_id"]}, {"_id": 0})
        stylist = await db.stylists.find_one({"id": booking["stylist_id"]}, {"_id": 0, "pin": 0})
        followup_status, err = send_whatsapp_no_show_followup(booking, service or {}, stylist or {})
        await db.bookings.update_one(
            {"id": booking_id},
            {"$set": {
                "no_show_followup_status": followup_status,
                "no_show_followup_error": err,
                "no_show_followup_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})

    return booking


@api_router.post("/stylist/login")
async def stylist_login(payload: StylistLoginPayload):
    st = await db.stylists.find_one({"id": payload.stylist_id}, {"_id": 0})
    if not st or st.get("pin") != payload.pin:
        raise HTTPException(status_code=401, detail="Invalid stylist or PIN")
    st.pop("pin", None)
    return {"token": payload.stylist_id, "stylist": st}


@api_router.get("/stylist/{stylist_id}/schedule")
async def stylist_schedule(stylist_id: str, date: str = Query(..., description="YYYY-MM-DD")):
    await _get_stylist(stylist_id)
    bookings = await db.bookings.find(
        {"stylist_id": stylist_id, "date": date},
        {"_id": 0},
    ).sort("start_time", 1).to_list(500)

    # Hydrate service info
    service_ids = list({b["service_id"] for b in bookings})
    services = {s["id"]: s for s in await db.services.find({"id": {"$in": service_ids}}, {"_id": 0}).to_list(100)}
    for b in bookings:
        b["service"] = services.get(b["service_id"])
    blocks = await db.stylist_blocks.find({"stylist_id": stylist_id, "date": date}, {"_id": 0}).sort("start_time", 1).to_list(200)
    try:
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
    except ValueError:
        weekday = None
    recurring_blocks = []
    if weekday is not None:
        recurring_blocks = await db.recurring_blocks.find({"stylist_id": stylist_id, "weekdays": weekday}, {"_id": 0}).sort("start_time", 1).to_list(200)
    return {"date": date, "bookings": bookings, "blocks": blocks, "recurring_blocks": recurring_blocks}


@api_router.patch("/stylist/{stylist_id}/bookings/{booking_id}/status")
async def update_booking_status(stylist_id: str, booking_id: str, payload: BookingStatusUpdate):
    allowed = {"upcoming", "done", "no_show", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    b = await _apply_booking_status(booking_id, payload.status, {"stylist_id": stylist_id})
    return {"booking": b}


@api_router.get("/stylist/{stylist_id}/availability")
async def get_stylist_availability(stylist_id: str, week_start: str = Query(..., description="YYYY-MM-DD (Monday)")):
    stylist = await _get_stylist(stylist_id)
    try:
        start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid week_start")
    end_date = start_date + timedelta(days=6)
    end_str = end_date.isoformat()

    blocks = await db.stylist_blocks.find(
        {"stylist_id": stylist_id, "date": {"$gte": week_start, "$lte": end_str}},
        {"_id": 0},
    ).to_list(500)
    recurring_blocks = await db.recurring_blocks.find(
        {"stylist_id": stylist_id},
        {"_id": 0},
    ).to_list(200)
    bookings = await db.bookings.find(
        {"stylist_id": stylist_id, "date": {"$gte": week_start, "$lte": end_str}, "status": {"$ne": "cancelled"}},
        {"_id": 0},
    ).to_list(500)
    service_ids = list({b["service_id"] for b in bookings})
    services = {s["id"]: s for s in await db.services.find({"id": {"$in": service_ids}}, {"_id": 0}).to_list(100)}
    for b in bookings:
        b["service"] = services.get(b["service_id"])
    return {
        "week_start": week_start,
        "working_hours": stylist.get("working_hours") or {},
        "blocks": blocks,
        "recurring_blocks": recurring_blocks,
        "bookings": bookings,
    }


@api_router.put("/stylist/{stylist_id}/blocks")
async def upsert_block(stylist_id: str, payload: BlockUpsert):
    await _get_stylist(stylist_id)
    if payload.status not in {"busy", "leave", "break"}:
        raise HTTPException(status_code=400, detail="status must be busy, leave or break")
    s_min = _t_to_minutes(payload.start_time)
    e_min = _t_to_minutes(payload.end_time)
    if e_min <= s_min:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    block = {
        "id": str(uuid.uuid4()),
        "stylist_id": stylist_id,
        "date": payload.date,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "status": payload.status,
        "label": payload.label,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.stylist_blocks.insert_one(block)
    block.pop("_id", None)
    return {"block": block}


@api_router.delete("/stylist/{stylist_id}/blocks/{block_id}")
async def delete_block(stylist_id: str, block_id: str):
    res = await db.stylist_blocks.delete_one({"id": block_id, "stylist_id": stylist_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"ok": True}


@api_router.put("/stylist/{stylist_id}/recurring-blocks")
async def upsert_recurring_block(stylist_id: str, payload: RecurringBlockUpsert):
    await _get_stylist(stylist_id)
    if payload.status not in {"busy", "break"}:
        raise HTTPException(status_code=400, detail="status must be busy or break")
    if not payload.weekdays or any(day not in range(7) for day in payload.weekdays):
        raise HTTPException(status_code=400, detail="weekdays must contain values 0..6")
    s_min = _t_to_minutes(payload.start_time)
    e_min = _t_to_minutes(payload.end_time)
    if e_min <= s_min:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    block = {
        "id": str(uuid.uuid4()),
        "stylist_id": stylist_id,
        "weekdays": sorted(list(set(payload.weekdays))),
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "status": payload.status,
        "label": (payload.label or "Break").strip() or "Break",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.recurring_blocks.insert_one(block)
    block.pop("_id", None)
    return {"block": block}


@api_router.delete("/stylist/{stylist_id}/recurring-blocks/{block_id}")
async def delete_recurring_block(stylist_id: str, block_id: str):
    res = await db.recurring_blocks.delete_one({"id": block_id, "stylist_id": stylist_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recurring block not found")
    return {"ok": True}


@api_router.put("/stylist/{stylist_id}/working-hours")
async def update_working_hours(stylist_id: str, payload: WorkingHoursUpdate):
    if payload.weekday not in range(7):
        raise HTTPException(status_code=400, detail="weekday must be 0..6")
    stylist = await _get_stylist(stylist_id)
    wh = dict(stylist.get("working_hours") or {})
    key = str(payload.weekday)
    if payload.closed:
        wh[key] = None
    else:
        if not payload.open or not payload.close:
            raise HTTPException(status_code=400, detail="open and close required")
        if _t_to_minutes(payload.close) <= _t_to_minutes(payload.open):
            raise HTTPException(status_code=400, detail="close must be after open")
        wh[key] = {"open": payload.open, "close": payload.close}
    await db.stylists.update_one({"id": stylist_id}, {"$set": {"working_hours": wh}})
    return {"working_hours": wh}


# ============================================================
# Owner & customer lookup
# ============================================================
class OwnerLoginPayload(BaseModel):
    pin: str


class RescheduleRequest(BaseModel):
    booking_id: str
    phone: str
    new_date: str
    new_start_time: str


class LookupRequest(BaseModel):
    phone: str
    code: Optional[str] = None  # last 4 of reference (case-insensitive)


def _matches_code(booking_id: str, code: Optional[str]) -> bool:
    if not code:
        return True
    return booking_id[:8].upper().endswith(code.strip().upper())


async def _hydrate(b: dict) -> dict:
    svc = await db.services.find_one({"id": b["service_id"]}, {"_id": 0})
    st = await db.stylists.find_one({"id": b["stylist_id"]}, {"_id": 0, "pin": 0})
    b["service"] = svc
    b["stylist"] = st
    return b


def _today_local_date():
    return datetime.now(SALON_TZ).date()


def _month_bounds(month: Optional[str] = None) -> tuple[str, str, str]:
    if month:
        try:
            first = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    else:
        first = _today_local_date().replace(day=1)
    if first.month == 12:
        next_month = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_month = first.replace(month=first.month + 1, day=1)
    last = next_month - timedelta(days=1)
    return first.strftime("%Y-%m"), first.isoformat(), last.isoformat()


def _revenue_period_bounds(period: Optional[str], anchor_date: Optional[str], days: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> tuple[str, str, str, str, str]:
    today = _today_local_date()
    if anchor_date:
        try:
            anchor = datetime.strptime(anchor_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="anchor_date must be YYYY-MM-DD")
    else:
        anchor = today

    if not period:
        start = today - timedelta(days=days - 1)
        end = today
        return "custom", anchor.isoformat(), start.isoformat(), end.isoformat(), f"Last {days} days"

    normalized = period.lower()
    if normalized == "day":
        start = anchor
        end = anchor
        label = anchor.strftime("%a, %d %b %Y")
    elif normalized == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        # Week-of-month = 1 + week index of the anchor within its month, based on
        # the Monday-start week number. First Monday of the month starts Week 1.
        first_of_month = anchor.replace(day=1)
        # Anchor Monday's day-of-month; align to the same weekday base.
        anchor_monday = anchor - timedelta(days=anchor.weekday())
        first_monday = first_of_month - timedelta(days=first_of_month.weekday())
        week_of_month = ((anchor_monday - first_monday).days // 7) + 1
        label = f"{anchor.strftime('%B %Y')} • Week {week_of_month}"
    elif normalized == "month":
        start = anchor.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
        label = anchor.strftime("%B %Y")
    elif normalized == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date are required for period=custom")
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date/end_date must be YYYY-MM-DD")
        if end < start:
            raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
        # Cap custom range to a reasonable window (2 years) to prevent runaway queries.
        if (end - start).days > 730:
            raise HTTPException(status_code=400, detail="Custom range cannot exceed 730 days")
        label = f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
    else:
        raise HTTPException(status_code=400, detail="period must be day, week, month, or custom")

    return normalized, anchor.isoformat(), start.isoformat(), end.isoformat(), label


async def _services_by_id(service_ids: List[str]) -> dict:
    if not service_ids:
        return {}
    return {s["id"]: s for s in await db.services.find({"id": {"$in": service_ids}}, {"_id": 0}).to_list(200)}


async def _stylists_by_id(stylist_ids: List[str]) -> dict:
    if not stylist_ids:
        return {}
    return {s["id"]: s for s in await db.stylists.find({"id": {"$in": stylist_ids}}, {"_id": 0, "pin": 0}).to_list(100)}


def _add_metric(bucket: dict, key: str, label: str, amount: float, count: int = 1):
    item = bucket.setdefault(key, {"id": key, "name": label, "revenue": 0.0, "count": 0})
    item["revenue"] += amount
    item["count"] += count


def _create_owner_token() -> str:
    payload = {
        "sub": "owner",
        "role": "owner",
        "type": "owner_access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=OWNER_TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, OWNER_TOKEN_SECRET, algorithm=OWNER_TOKEN_ALGORITHM)


async def require_owner(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Owner authentication required")
    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        payload = jwt.decode(token, OWNER_TOKEN_SECRET, algorithms=[OWNER_TOKEN_ALGORITHM])
        if payload.get("sub") != "owner" or payload.get("role") != "owner" or payload.get("type") != "owner_access":
            raise HTTPException(status_code=401, detail="Invalid owner token")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Owner session expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid owner token")


def _create_manager_token(manager_id: str, salon_id: str) -> str:
    payload = {
        "sub": manager_id,
        "role": "manager",
        "type": "manager_access",
        "salon_id": salon_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=OWNER_TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, OWNER_TOKEN_SECRET, algorithm=OWNER_TOKEN_ALGORITHM)


def _create_customer_token(phone: str) -> str:
    """Signed token issued on successful customer OTP login. Enables /api/customer/*
    endpoints to fetch fresh data without another OTP round-trip on every page load."""
    payload = {
        "sub": phone,
        "role": "customer",
        "type": "customer_access",
        "phone": phone,
        "exp": datetime.now(timezone.utc) + timedelta(hours=OWNER_TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, OWNER_TOKEN_SECRET, algorithm=OWNER_TOKEN_ALGORITHM)


async def require_customer(authorization: Optional[str] = Header(None)) -> str:
    """Returns the authenticated customer's phone number from the JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Customer authentication required")
    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        payload = jwt.decode(token, OWNER_TOKEN_SECRET, algorithms=[OWNER_TOKEN_ALGORITHM])
        if payload.get("role") != "customer" or payload.get("type") != "customer_access":
            raise HTTPException(status_code=401, detail="Invalid customer token")
        phone = payload.get("phone")
        if not phone:
            raise HTTPException(status_code=401, detail="Invalid customer token")
        return phone
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Customer session expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid customer token")


async def require_manager(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Manager authentication required")
    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        payload = jwt.decode(token, OWNER_TOKEN_SECRET, algorithms=[OWNER_TOKEN_ALGORITHM])
        if payload.get("role") != "manager" or payload.get("type") != "manager_access" or not payload.get("salon_id"):
            raise HTTPException(status_code=401, detail="Invalid manager token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Manager session expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid manager token")
    manager = await db.managers.find_one({"id": payload["sub"], "is_active": {"$ne": False}}, {"_id": 0})
    if not manager:
        raise HTTPException(status_code=401, detail="Manager account not found or archived")
    return {**payload, "manager": manager}



class OtpLoginRequest(BaseModel):
    phone: str


class OtpLoginVerify(BaseModel):
    phone: str
    otp: str


async def _request_login_otp(phone: str, purpose: str) -> dict:
    normalized = _normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Valid phone is required")
    otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    await db.login_otps.update_one(
        {"phone": normalized, "purpose": purpose},
        {"$set": {"phone": normalized, "purpose": purpose, "otp": otp, "expires_at": expires_at.isoformat(), "verified": False, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    status, err = send_whatsapp_otp(normalized, otp)
    if status == "failed":
        logger.warning(f"{purpose} OTP WhatsApp failed for {normalized}: {err}")
    return {"ok": True, "phone": normalized, "expires_in_seconds": 300, "mock_otp": otp, "mocked": True, "whatsapp_status": status}


async def _verify_login_otp(phone: str, otp: str, purpose: str) -> str:
    normalized = _normalize_phone(phone)
    record = await db.login_otps.find_one({"phone": normalized, "purpose": purpose}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="OTP not requested")
    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
    if str(record.get("otp")) != str(otp).strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")
    await db.login_otps.update_one({"phone": normalized, "purpose": purpose}, {"$set": {"verified": True, "verified_at": datetime.now(timezone.utc).isoformat()}})
    return normalized


@api_router.post("/owner/login/request-otp")
async def owner_login_request_otp(payload: OtpLoginRequest):
    if _normalize_phone(payload.phone) != _normalize_phone(OWNER_PHONE):
        raise HTTPException(status_code=403, detail="Phone is not authorized for owner login")
    return await _request_login_otp(payload.phone, "owner")


@api_router.post("/owner/login/verify-otp")
async def owner_login_verify_otp(payload: OtpLoginVerify):
    phone = await _verify_login_otp(payload.phone, payload.otp, "owner")
    if phone != _normalize_phone(OWNER_PHONE):
        raise HTTPException(status_code=403, detail="Phone is not authorized for owner login")
    return {"token": _create_owner_token(), "name": "Maison Aurelle", "phone": phone}


@api_router.post("/login/request-otp")
async def unified_login_request_otp(payload: OtpLoginRequest):
    return await _request_login_otp(payload.phone, "unified")


@api_router.post("/login/verify-otp")
async def unified_login_verify_otp(payload: OtpLoginVerify):
    phone = await _verify_login_otp(payload.phone, payload.otp, "unified")
    if phone == _normalize_phone(OWNER_PHONE):
        return {"role": "owner", "token": _create_owner_token(), "phone": phone}
    manager = await db.managers.find_one(
        {"login_phone": phone, "is_active": {"$ne": False}},
        {"_id": 0},
    )
    if manager:
        salon = await db.salons.find_one({"id": manager["salon_id"]}, {"_id": 0}) if manager.get("salon_id") else None
        return {
            "role": "manager",
            "token": _create_manager_token(manager["id"], manager["salon_id"]),
            "manager": manager,
            "salon": salon,
            "phone": phone,
        }
    stylist = await db.stylists.find_one(
        {"$and": [{"$or": [{"login_phone": phone}, {"phone": phone}]}, {"is_active": {"$ne": False}}]},
        {"_id": 0, "pin": 0},
    )
    if stylist:
        return {"role": "stylist", "stylist": stylist, "phone": phone}
    appointments = await _self_serve_phone_appointments(phone)
    return {
        "role": "customer",
        "phone": phone,
        "appointments": appointments,
        "token": _create_customer_token(phone),
    }


@api_router.get("/customer/appointments")
async def customer_get_appointments(phone: str = Depends(require_customer)):
    """Return the caller's own appointments — fresh from the DB. Used by the
    customer dashboard and /manage to refresh the list without another OTP."""
    appointments = await _self_serve_phone_appointments(phone)
    return {"phone": phone, "appointments": appointments}


@api_router.post("/owner/login")
async def owner_login(payload: OwnerLoginPayload):
    if payload.pin != OWNER_PIN:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"token": _create_owner_token(), "name": "Maison Aurelle"}


@api_router.get("/owner/notifications")
async def owner_notifications(_owner: dict = Depends(require_owner)):
    rows = await db.owner_notifications.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    unread = await db.owner_notifications.count_documents({"read": False})
    return {"notifications": rows, "unread": unread}


@api_router.post("/owner/notifications/mark-read")
async def owner_notifications_mark_read(_owner: dict = Depends(require_owner)):
    await db.owner_notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"ok": True}


def _slug_id(prefix: str, name: str) -> str:
    clean = "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in name).split())[:40]
    return f"{prefix}-{clean or uuid.uuid4().hex[:8]}"


DEFAULT_SALON_ID = "salon-main"
DEFAULT_SALON_DOC = {
    "id": DEFAULT_SALON_ID,
    "name": "Maison Aurelle — Main",
    "slug": "main",
    "address": "",
    "city": "",
    "phone": "",
    "timezone": "Asia/Kolkata",
    "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)},
    "booking_window_days": 30,
    "is_active": True,
}


async def _ensure_default_salon():
    """Idempotent: create the default salon and back-fill salon_id on stylists/bookings."""
    existing = await db.salons.find_one({"id": DEFAULT_SALON_ID}, {"_id": 0})
    if not existing:
        doc = {**DEFAULT_SALON_DOC, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.salons.insert_one(doc)
    # Backfill booking_window_days on any salon docs that predate the field.
    await db.salons.update_many({"booking_window_days": {"$exists": False}}, {"$set": {"booking_window_days": 30}})
    # Repair any salon rows where working_hours got nulled out by an earlier
    # partial PATCH (before the endpoint learned to preserve the field).
    await db.salons.update_many(
        {"working_hours": {"$in": [None, {}]}},
        {"$set": {"working_hours": DEFAULT_SALON_DOC["working_hours"]}},
    )
    await db.salons.update_many({"working_hours": {"$exists": False}}, {"$set": {"working_hours": DEFAULT_SALON_DOC["working_hours"]}})
    await db.stylists.update_many({"salon_id": {"$in": [None, ""]}}, {"$set": {"salon_id": DEFAULT_SALON_ID}})
    await db.stylists.update_many({"salon_id": {"$exists": False}}, {"$set": {"salon_id": DEFAULT_SALON_ID}})
    await db.bookings.update_many({"salon_id": {"$in": [None, ""]}}, {"$set": {"salon_id": DEFAULT_SALON_ID}})
    await db.bookings.update_many({"salon_id": {"$exists": False}}, {"$set": {"salon_id": DEFAULT_SALON_ID}})


@api_router.get("/salons")
async def list_salons(service_id: Optional[str] = Query(None)):
    docs = await db.salons.find({"is_active": {"$ne": False}}, {"_id": 0}).sort("name", 1).to_list(200)
    if service_id:
        off_salons = await db.salon_services.find(
            {"service_id": service_id, "is_offered": False},
            {"_id": 0, "salon_id": 1},
        ).to_list(500)
        off_set = {o["salon_id"] for o in off_salons}
        docs = [s for s in docs if s["id"] not in off_set]
    return {"salons": docs}


@api_router.get("/owner/salons")
async def owner_list_salons(_owner: dict = Depends(require_owner)):
    docs = await db.salons.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return {"salons": docs}


@api_router.post("/owner/salons")
async def owner_create_salon(payload: OwnerSalonUpsert, _owner: dict = Depends(require_owner)):
    salon_id = _slug_id("salon", payload.name)
    existing = await db.salons.find_one({"id": salon_id})
    if existing:
        if existing.get("is_active") is False:
            # Reactivate and update the archived salon rather than accumulating duplicates
            data = payload.model_dump()
            if not data.get("slug"):
                data["slug"] = salon_id.removeprefix("salon-")
            if not data.get("working_hours"):
                data["working_hours"] = DEFAULT_SALON_DOC["working_hours"]
            if data.get("phone"):
                data["phone"] = _normalize_phone(data["phone"])
            data["is_active"] = True
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.salons.update_one({"id": salon_id}, {"$set": data})
            return await db.salons.find_one({"id": salon_id}, {"_id": 0})
        raise HTTPException(status_code=409, detail="A salon with this name already exists")
    data = payload.model_dump()
    if not data.get("slug"):
        data["slug"] = salon_id.removeprefix("salon-")
    if not data.get("working_hours"):
        data["working_hours"] = DEFAULT_SALON_DOC["working_hours"]
    if data.get("phone"):
        data["phone"] = _normalize_phone(data["phone"])
    doc = {"id": salon_id, **data, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.salons.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.patch("/owner/salons/{salon_id}")
async def owner_update_salon(salon_id: str, payload: OwnerSalonUpsert, _owner: dict = Depends(require_owner)):
    update = payload.model_dump()
    if update.get("phone"):
        update["phone"] = _normalize_phone(update["phone"])
    if not update.get("slug"):
        update.pop("slug", None)
    # Do not overwrite ``working_hours`` when the caller omitted it — otherwise
    # a partial PATCH (e.g. tweaking booking_window_days) would null out the
    # salon's operating hours.
    if update.get("working_hours") is None:
        update.pop("working_hours", None)
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.salons.update_one({"id": salon_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Salon not found")
    return await db.salons.find_one({"id": salon_id}, {"_id": 0})


@api_router.post("/owner/salons/{salon_id}/archive")
async def owner_archive_salon(salon_id: str, _owner: dict = Depends(require_owner)):
    if salon_id == DEFAULT_SALON_ID:
        raise HTTPException(status_code=400, detail="The default salon cannot be archived")
    result = await db.salons.update_one({"id": salon_id}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Salon not found")
    return {"ok": True}


async def _effective_salon_menu(salon_id: str) -> List[dict]:
    """Return the master services list joined with per-salon overrides.

    Default semantics: if no salon_services doc exists for (salon_id, service_id), the service
    is offered at its base price. is_offered=false in a doc explicitly opts the service out.
    """
    services = await db.services.find({"is_active": {"$ne": False}}, {"_id": 0}).sort("name", 1).to_list(500)
    overrides = await db.salon_services.find({"salon_id": salon_id}, {"_id": 0}).to_list(500)
    override_by_svc = {o["service_id"]: o for o in overrides}
    menu = []
    for svc in services:
        entry = override_by_svc.get(svc["id"], {})
        is_offered = entry.get("is_offered", True)
        price_override = entry.get("price_override")
        effective_price = float(price_override) if price_override not in (None, "") else float(svc.get("price", 0))
        menu.append({
            **svc,
            "is_offered": is_offered,
            "price_override": price_override,
            "effective_price": effective_price,
        })
    return menu


@api_router.get("/owner/salons/{salon_id}/menu")
async def owner_get_salon_menu(salon_id: str, _owner: dict = Depends(require_owner)):
    if not await db.salons.find_one({"id": salon_id}):
        raise HTTPException(status_code=404, detail="Salon not found")
    menu = await _effective_salon_menu(salon_id)
    return {"salon_id": salon_id, "menu": menu}


@api_router.put("/owner/salons/{salon_id}/menu")
async def owner_update_salon_menu(salon_id: str, payload: OwnerSalonMenuBulkUpdate, _owner: dict = Depends(require_owner)):
    if not await db.salons.find_one({"id": salon_id}):
        raise HTTPException(status_code=404, detail="Salon not found")
    valid_service_ids = {svc["id"] for svc in await db.services.find({"is_active": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(500)}
    now = datetime.now(timezone.utc).isoformat()
    for entry in payload.entries:
        if entry.service_id not in valid_service_ids:
            continue
        price_override = None if entry.price_override in (None, "") else float(entry.price_override)
        await db.salon_services.update_one(
            {"salon_id": salon_id, "service_id": entry.service_id},
            {"$set": {"salon_id": salon_id, "service_id": entry.service_id, "is_offered": bool(entry.is_offered), "price_override": price_override, "updated_at": now}},
            upsert=True,
        )
    menu = await _effective_salon_menu(salon_id)
    return {"salon_id": salon_id, "menu": menu}


@api_router.get("/owner/managers")
async def owner_list_managers(_owner: dict = Depends(require_owner)):
    docs = await db.managers.find({}, {"_id": 0}).sort("name", 1).to_list(5000)
    return {"managers": docs}


@api_router.post("/owner/managers")
async def owner_create_manager(payload: OwnerManagerUpsert, _owner: dict = Depends(require_owner)):
    if not await db.salons.find_one({"id": payload.salon_id}):
        raise HTTPException(status_code=400, detail="Unknown salon_id")
    login_phone = _normalize_phone(payload.login_phone) if payload.login_phone else ""
    if not login_phone:
        raise HTTPException(status_code=400, detail="login_phone is required")
    if login_phone == _normalize_phone(OWNER_PHONE):
        raise HTTPException(status_code=400, detail="This number is reserved for the owner")
    if await db.managers.find_one({"login_phone": login_phone, "is_active": {"$ne": False}}):
        raise HTTPException(status_code=409, detail="A manager with this login phone already exists")
    if await db.stylists.find_one({"login_phone": login_phone, "is_active": {"$ne": False}}):
        raise HTTPException(status_code=409, detail="This login phone is already used by a stylist")
    manager_id = _slug_id("manager", payload.name)
    if await db.managers.find_one({"id": manager_id}):
        manager_id = f"{manager_id}-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": manager_id,
        "name": payload.name.strip(),
        "phone": _normalize_phone(payload.phone) if payload.phone else "",
        "login_phone": login_phone,
        "salon_id": payload.salon_id,
        "is_active": payload.is_active,
        "created_at": now,
        "updated_at": now,
    }
    await db.managers.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.patch("/owner/managers/{manager_id}")
async def owner_update_manager(manager_id: str, payload: OwnerManagerUpsert, _owner: dict = Depends(require_owner)):
    if not await db.salons.find_one({"id": payload.salon_id}):
        raise HTTPException(status_code=400, detail="Unknown salon_id")
    login_phone = _normalize_phone(payload.login_phone) if payload.login_phone else ""
    if not login_phone:
        raise HTTPException(status_code=400, detail="login_phone is required")
    if login_phone == _normalize_phone(OWNER_PHONE):
        raise HTTPException(status_code=400, detail="This number is reserved for the owner")
    conflict = await db.managers.find_one({"login_phone": login_phone, "is_active": {"$ne": False}, "id": {"$ne": manager_id}})
    if conflict:
        raise HTTPException(status_code=409, detail="A manager with this login phone already exists")
    update = {
        "name": payload.name.strip(),
        "phone": _normalize_phone(payload.phone) if payload.phone else "",
        "login_phone": login_phone,
        "salon_id": payload.salon_id,
        "is_active": payload.is_active,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.managers.update_one({"id": manager_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Manager not found")
    return await db.managers.find_one({"id": manager_id}, {"_id": 0})


@api_router.post("/owner/managers/{manager_id}/archive")
async def owner_archive_manager(manager_id: str, _owner: dict = Depends(require_owner)):
    result = await db.managers.update_one({"id": manager_id}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Manager not found")
    return {"ok": True}


# --- Manager-scoped read/write endpoints (all filter by the manager's salon_id) ---

@api_router.get("/manager/me")
async def manager_me(ctx: dict = Depends(require_manager)):
    salon = await db.salons.find_one({"id": ctx["salon_id"]}, {"_id": 0})
    return {"manager": ctx["manager"], "salon": salon}


@api_router.get("/manager/bookings")
async def manager_bookings(date: str = Query(...), ctx: dict = Depends(require_manager)):
    bookings = await db.bookings.find({"date": date, "salon_id": ctx["salon_id"]}, {"_id": 0}).sort([("start_time", 1)]).to_list(1000)
    for b in bookings:
        await _hydrate(b)
    return {"date": date, "salon_id": ctx["salon_id"], "bookings": bookings}


@api_router.get("/manager/revenue-trend")
async def manager_revenue_trend(days: int = Query(7, ge=1, le=60), ctx: dict = Depends(require_manager)):
    today = datetime.now(SALON_TZ).date()
    start = today - timedelta(days=days - 1)
    rows = await db.bookings.find(
        {"date": {"$gte": start.isoformat(), "$lte": today.isoformat()}, "status": {"$in": ["upcoming", "done"]}, "salon_id": ctx["salon_id"]},
        {"_id": 0, "date": 1, "service_id": 1},
    ).to_list(5000)
    services = {s["id"]: s for s in await db.services.find({}, {"_id": 0, "id": 1, "price": 1}).to_list(500)}
    by_day: dict = {}
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        by_day[d] = {"date": d, "revenue": 0.0, "count": 0}
    for r in rows:
        d = r["date"]
        price = float(services.get(r["service_id"], {}).get("price", 0))
        by_day[d]["revenue"] += price
        by_day[d]["count"] += 1
    return {"series": list(by_day.values())}


@api_router.get("/manager/no-shows")
async def manager_no_shows(month: Optional[str] = Query(None), ctx: dict = Depends(require_manager)):
    month_label, start, end = _month_bounds(month)
    bookings = await db.bookings.find(
        {"date": {"$gte": start, "$lte": end}, "salon_id": ctx["salon_id"]},
        {"_id": 0},
    ).sort([("date", -1), ("start_time", 1)]).to_list(5000)
    return await _no_show_report(bookings, month_label, start, end)


@api_router.get("/manager/revenue-insights")
async def manager_revenue_insights(
    days: int = Query(30, ge=1, le=90),
    period: Optional[str] = Query(None, pattern="^(day|week|month|custom)$"),
    anchor_date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="Custom range start YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Custom range end YYYY-MM-DD"),
    ctx: dict = Depends(require_manager),
):
    period_key, anchor, start, end, period_label = _revenue_period_bounds(period, anchor_date, days, start_date, end_date)
    bookings = await db.bookings.find(
        {"date": {"$gte": start, "$lte": end}, "salon_id": ctx["salon_id"]},
        {"_id": 0},
    ).to_list(10000)
    return await _revenue_insights_from_bookings(bookings, period_key, anchor, start, end, period_label)


@api_router.get("/manager/customers/search")
async def manager_customers_search(ctx: dict = Depends(require_manager)):
    # Only customers who have at least one booking at this salon
    pipeline = [
        {"$match": {"salon_id": ctx["salon_id"]}},
        {"$group": {"_id": "$customer_phone", "customer_name": {"$last": "$customer_name"}, "last_visit": {"$max": "$date"}, "visit_count": {"$sum": 1}}},
        {"$sort": {"customer_name": 1}},
        {"$limit": 500},
    ]
    docs = await db.bookings.aggregate(pipeline).to_list(500)
    customers = [{"customer_phone": d["_id"], "customer_name": d["customer_name"], "last_visit": d.get("last_visit"), "visit_count": d.get("visit_count", 0)} for d in docs]
    return {"customers": customers}


@api_router.get("/manager/customers/{phone}")
async def manager_customer_profile(phone: str, ctx: dict = Depends(require_manager)):
    # Guard: this customer must have booked at the manager's salon
    exists = await db.bookings.find_one({"customer_phone": phone, "salon_id": ctx["salon_id"]}, {"_id": 0, "id": 1})
    if not exists:
        raise HTTPException(status_code=404, detail="Customer not seen at this salon")
    return await _build_customer_profile(phone)


@api_router.patch("/manager/bookings/{booking_id}/status")
async def manager_set_booking_status(booking_id: str, payload: BookingStatusUpdate, ctx: dict = Depends(require_manager)):
    booking = await db.bookings.find_one({"id": booking_id, "salon_id": ctx["salon_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found at this salon")
    allowed = {"upcoming", "done", "no_show", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    updated = await _apply_booking_status(booking_id, payload.status)
    return {"booking": updated}


@api_router.patch("/manager/bookings/{booking_id}/cancel")
async def manager_cancel_booking(booking_id: str, ctx: dict = Depends(require_manager)):
    booking = await db.bookings.find_one({"id": booking_id, "salon_id": ctx["salon_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found at this salon")
    res = await db.bookings.update_one({"id": booking_id}, {"$set": {"status": "cancelled"}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


@api_router.get("/owner/services")
async def owner_list_services(_owner: dict = Depends(require_owner)):
    docs = await db.services.find({}, {"_id": 0}).sort("name", 1).to_list(500)
    return {"services": docs}


@api_router.post("/owner/services")
async def owner_create_service(payload: OwnerServiceUpsert, _owner: dict = Depends(require_owner)):
    service_id = _slug_id("svc", payload.name)
    if await db.services.find_one({"id": service_id}):
        service_id = f"{service_id}-{uuid.uuid4().hex[:6]}"
    doc = {"id": service_id, **payload.model_dump(), "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.services.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.patch("/owner/services/{service_id}")
async def owner_update_service(service_id: str, payload: OwnerServiceUpsert, _owner: dict = Depends(require_owner)):
    update = {**payload.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
    result = await db.services.update_one({"id": service_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    return await db.services.find_one({"id": service_id}, {"_id": 0})


@api_router.post("/owner/services/{service_id}/archive")
async def owner_archive_service(service_id: str, _owner: dict = Depends(require_owner)):
    result = await db.services.update_one({"id": service_id}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.stylists.update_many({"services": service_id}, {"$pull": {"services": service_id}})
    return {"ok": True}


@api_router.get("/owner/stylists")
async def owner_list_stylists(salon_id: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    query: dict = {}
    if salon_id:
        query["salon_id"] = salon_id
    docs = await db.stylists.find(query, {"_id": 0, "pin": 0}).sort("name", 1).to_list(500)
    return {"stylists": docs}


@api_router.post("/owner/stylists")
async def owner_create_stylist(payload: OwnerStylistUpsert, _owner: dict = Depends(require_owner)):
    stylist_id = _slug_id("stylist", payload.name)
    if await db.stylists.find_one({"id": stylist_id}):
        stylist_id = f"{stylist_id}-{uuid.uuid4().hex[:6]}"
    active_service_ids = {svc["id"] for svc in await db.services.find({"is_active": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(500)}
    services = [sid for sid in payload.services if sid in active_service_ids]
    salon_id = payload.salon_id or DEFAULT_SALON_ID
    if not await db.salons.find_one({"id": salon_id}):
        raise HTTPException(status_code=400, detail="Unknown salon_id")
    doc = {**payload.model_dump(), "id": stylist_id, "salon_id": salon_id, "services": services, "pin": str(random.randint(1000, 9999)), "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)}, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    if doc.get("phone"):
        doc["phone"] = _normalize_phone(doc["phone"])
    if doc.get("login_phone"):
        doc["login_phone"] = _normalize_phone(doc["login_phone"])
    await db.stylists.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("pin", None)
    return doc


@api_router.patch("/owner/stylists/{stylist_id}")
async def owner_update_stylist(stylist_id: str, payload: OwnerStylistUpsert, _owner: dict = Depends(require_owner)):
    active_service_ids = {svc["id"] for svc in await db.services.find({"is_active": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(500)}
    update = payload.model_dump()
    update["services"] = [sid for sid in update.get("services", []) if sid in active_service_ids]
    if update.get("phone"):
        update["phone"] = _normalize_phone(update["phone"])
    if update.get("login_phone"):
        update["login_phone"] = _normalize_phone(update["login_phone"])
    if update.get("salon_id"):
        if not await db.salons.find_one({"id": update["salon_id"]}):
            raise HTTPException(status_code=400, detail="Unknown salon_id")
    else:
        update.pop("salon_id", None)  # don't overwrite existing salon_id with empty
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.stylists.update_one({"id": stylist_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return await db.stylists.find_one({"id": stylist_id}, {"_id": 0, "pin": 0})


@api_router.post("/owner/stylists/{stylist_id}/archive")
async def owner_archive_stylist(stylist_id: str, _owner: dict = Depends(require_owner)):
    result = await db.stylists.update_one({"id": stylist_id}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stylist not found")
    return {"ok": True}


@api_router.delete("/owner/stylists/{stylist_id}")
async def owner_delete_stylist(stylist_id: str, _owner: dict = Depends(require_owner)):
    """Permanently remove a stylist profile and their availability records.
    Booking history is preserved (bookings retain the stylist_id for audit)."""
    stylist = await db.stylists.find_one({"id": stylist_id})
    if not stylist:
        raise HTTPException(status_code=404, detail="Stylist not found")
    await db.stylists.delete_one({"id": stylist_id})
    # Best-effort cleanup of availability rules so stale blocks don't linger.
    await db.stylist_blocks.delete_many({"stylist_id": stylist_id})
    await db.recurring_blocks.delete_many({"stylist_id": stylist_id})
    return {"ok": True}


_ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 2 * 1024 * 1024


@api_router.post("/owner/uploads/image")
async def owner_upload_image(file: UploadFile = File(...), _owner: dict = Depends(require_owner)):
    if file.content_type not in _ALLOWED_IMAGE_MIME:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP or GIF images allowed")
    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 2 MB or smaller")
    ext = (file.filename or "img").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    if ext not in storage.MIME_BY_EXT:
        ext = "jpg"
    path = f"{storage.APP_NAME}/stylists/{uuid.uuid4().hex}.{ext}"
    try:
        result = storage.put_object(path, data, file.content_type or storage.MIME_BY_EXT[ext])
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Storage upload failed: %s", exc)
        raise HTTPException(status_code=502, detail="Image upload failed")
    stored_path = result.get("path") or path
    return {"path": stored_path, "url": f"/api/files/{stored_path}", "size": result.get("size", len(data))}


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    if not path.startswith(f"{storage.APP_NAME}/"):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = storage.get_object(path)
    except requests.HTTPError as exc:
        # Upstream storage returns 500 (not 404) for missing objects; treat any upstream
        # error response as "not found" from our consumer's perspective.
        raise HTTPException(status_code=404, detail="File not found") from exc
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("File fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail="File fetch failed")
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@api_router.get("/owner/bookings")
async def owner_bookings(date: str = Query(...), salon_id: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    query: dict = {"date": date}
    if salon_id:
        query["salon_id"] = salon_id
    bookings = await db.bookings.find(query, {"_id": 0}).sort([("start_time", 1)]).to_list(1000)
    for b in bookings:
        await _hydrate(b)
    return {"date": date, "salon_id": salon_id, "bookings": bookings}


@api_router.get("/owner/summary")
async def owner_summary(date: str = Query(...), salon_id: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    query: dict = {"date": date}
    if salon_id:
        query["salon_id"] = salon_id
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(1000)
    revenue = 0.0
    counts = {"upcoming": 0, "done": 0, "no_show": 0, "cancelled": 0}
    per_stylist: dict = {}
    for b in bookings:
        counts[b.get("status", "upcoming")] = counts.get(b.get("status", "upcoming"), 0) + 1
        if b.get("status") in ("upcoming", "done"):
            svc = await db.services.find_one({"id": b["service_id"]}, {"_id": 0, "price": 1})
            if svc:
                revenue += float(svc.get("price", 0))
                per_stylist[b["stylist_id"]] = per_stylist.get(b["stylist_id"], 0) + float(svc.get("price", 0))
    return {"date": date, "revenue": revenue, "counts": counts, "total": len(bookings), "per_stylist": per_stylist}


@api_router.get("/owner/customers/search")
async def owner_customer_search(q: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    rows = await _search_customer_profiles(q)
    return {"customers": rows}


@api_router.get("/owner/customers/{phone}")
async def owner_customer_profile(phone: str, _owner: dict = Depends(require_owner)):
    return await _build_customer_profile(phone)


@api_router.patch("/owner/customers/{phone}")
async def owner_update_customer_profile(phone: str, payload: CustomerProfileUpdate, _owner: dict = Depends(require_owner)):
    normalized = _normalize_phone(phone)
    update = payload.model_dump(exclude_unset=True)
    update["customer_phone"] = normalized
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    if update.get("preferred_stylist_id"):
        await _get_stylist(update["preferred_stylist_id"])
    await db.customer_profiles.update_one({"customer_phone": normalized}, {"$set": update, "$setOnInsert": {"created_at": update["updated_at"]}}, upsert=True)
    return await _build_customer_profile(normalized)


@api_router.patch("/owner/bookings/{booking_id}/cancel")
async def owner_cancel(booking_id: str, _owner: dict = Depends(require_owner)):
    res = await db.bookings.update_one({"id": booking_id}, {"$set": {"status": "cancelled"}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


@api_router.patch("/owner/bookings/{booking_id}/status")
async def owner_update_booking_status(booking_id: str, payload: BookingStatusUpdate, _owner: dict = Depends(require_owner)):
    allowed = {"upcoming", "done", "no_show", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    booking = await _apply_booking_status(booking_id, payload.status)
    return {"booking": booking}


class CustomerCancelPayload(BaseModel):
    booking_id: str
    phone: str


class SelfServeCancelPayload(BaseModel):
    reason: Optional[str] = "other"
    reason_note: Optional[str] = ""


class SelfServeReschedulePayload(BaseModel):
    new_date: str
    new_start_time: str


class ManageOtpRequest(BaseModel):
    phone: str


class ManageOtpVerify(BaseModel):
    phone: str
    otp: str


async def _self_serve_booking_response(booking: dict, request: Optional[Request] = None) -> dict:
    booking = await _ensure_manage_token(booking, request)
    await _hydrate(booking)
    booking_dt = _booking_local_dt(booking)
    within_24h = booking_dt - datetime.now(SALON_TZ) < timedelta(hours=24)
    return {
        "booking": booking,
        "policy_notice": "Please cancel or reschedule at least 24 hours before your appointment.",
        "within_24h": within_24h,
        "cancellation_reasons": [
            {"value": "schedule_conflict", "label": "Schedule conflict"},
            {"value": "not_feeling_well", "label": "Not feeling well"},
            {"value": "travel_or_traffic", "label": "Travel or traffic issue"},
            {"value": "family_emergency", "label": "Family emergency"},
            {"value": "work_commitment", "label": "Work commitment"},
            {"value": "booked_by_mistake", "label": "Booked by mistake"},
            {"value": "other", "label": "Other"},
        ],
    }


class CustomerProfileSelfUpdate(BaseModel):
    customer_name: Optional[str] = None
    birthday: Optional[str] = None
    hair_type: Optional[str] = None
    product_allergies: Optional[str] = None
    preferences: Optional[str] = None
    stylist_notes: Optional[str] = None


@api_router.get("/customer/profile/{phone}")
async def customer_self_profile(phone: str):
    return await _build_customer_profile(phone)


@api_router.patch("/customer/profile/{phone}")
async def customer_self_update_profile(phone: str, payload: CustomerProfileSelfUpdate):
    normalized = _normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Valid customer phone is required")
    update = payload.model_dump(exclude_unset=True)
    update["customer_phone"] = normalized
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.customer_profiles.update_one(
        {"customer_phone": normalized},
        {"$set": update, "$setOnInsert": {"created_at": update["updated_at"]}},
        upsert=True,
    )
    return await _build_customer_profile(normalized)


async def _self_serve_phone_appointments(phone: str, request: Optional[Request] = None) -> List[dict]:
    normalized = _normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Valid phone is required")
    rows = await db.bookings.find({"customer_phone": {"$regex": f"{normalized}$"}}, {"_id": 0}).sort("date", -1).to_list(200)
    appointments = []
    for row in rows:
        row = await _ensure_manage_token(row, request)
        await _hydrate(row)
        appointments.append(row)
    return appointments


@api_router.post("/customer/manage/request-otp")
async def customer_manage_request_otp(payload: ManageOtpRequest):
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Valid phone is required")
    otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    await db.customer_otps.update_one(
        {"phone": phone},
        {"$set": {"phone": phone, "otp": otp, "expires_at": expires_at.isoformat(), "verified": False, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    status, err = send_whatsapp_otp(phone, otp)
    if status == "failed":
        logger.warning(f"Customer manage OTP WhatsApp failed for {phone}: {err}")
    return {"ok": True, "phone": phone, "expires_in_seconds": 300, "mock_otp": otp, "mocked": True, "whatsapp_status": status}


@api_router.post("/customer/manage/verify-otp")
async def customer_manage_verify_otp(payload: ManageOtpVerify, request: Request):
    phone = _normalize_phone(payload.phone)
    record = await db.customer_otps.find_one({"phone": phone}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="OTP not requested")
    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
    if str(record.get("otp")) != str(payload.otp).strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")
    await db.customer_otps.update_one({"phone": phone}, {"$set": {"verified": True, "verified_at": datetime.now(timezone.utc).isoformat()}})
    appointments = await _self_serve_phone_appointments(phone, request)
    return {"ok": True, "phone": phone, "appointments": appointments, "mocked": True}


@api_router.get("/customer/manage/{token}")
async def customer_manage_detail(token: str, request: Request):
    b = await db.bookings.find_one({"manage_token": token}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return await _self_serve_booking_response(b, request)


@api_router.post("/customer/manage/{token}/cancel")
async def customer_manage_cancel(token: str, payload: SelfServeCancelPayload):
    b = await db.bookings.find_one({"manage_token": token}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")
    if b.get("status") == "done":
        raise HTTPException(status_code=400, detail="Completed bookings cannot be cancelled")
    update = {
        "status": "cancelled",
        "cancelled_by": "customer",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancellation_reason": payload.reason or "other",
        "cancellation_reason_note": (payload.reason_note or "").strip(),
    }
    await db.bookings.update_one({"id": b["id"]}, {"$set": update})
    b.update(update)
    await _create_owner_notification("customer_cancelled", b, f"{b.get('customer_name')} cancelled {b.get('date')} at {b.get('start_time')}.")
    return await _self_serve_booking_response(b)


@api_router.post("/customer/manage/{token}/reschedule")
async def customer_manage_reschedule(token: str, payload: SelfServeReschedulePayload):
    b = await db.bookings.find_one({"manage_token": token}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Booking already cancelled")
    if b.get("status") == "done":
        raise HTTPException(status_code=400, detail="Completed bookings cannot be rescheduled")
    service = await _get_service(b["service_id"])
    stylist = await _get_stylist(b["stylist_id"])
    try:
        new_date_d = datetime.strptime(payload.new_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    if new_date_d < datetime.now(SALON_TZ).date():
        raise HTTPException(status_code=400, detail="Cannot reschedule to a past date")
    start_min = _t_to_minutes(payload.new_start_time)
    end_min = start_min + service["duration_min"]
    weekday = new_date_d.weekday()
    wh = (stylist.get("working_hours") or {}).get(str(weekday))
    if not wh:
        raise HTTPException(status_code=400, detail="Stylist not working that day")
    if start_min < _t_to_minutes(wh["open"]) or end_min > _t_to_minutes(wh["close"]):
        raise HTTPException(status_code=400, detail="Slot outside working hours")
    others = await db.bookings.find({"stylist_id": b["stylist_id"], "date": payload.new_date, "status": {"$ne": "cancelled"}, "id": {"$ne": b["id"]}}, {"_id": 0, "start_time": 1, "end_time": 1}).to_list(500)
    blocks = await db.stylist_blocks.find({"stylist_id": b["stylist_id"], "date": payload.new_date}, {"_id": 0, "start_time": 1, "end_time": 1}).to_list(500)
    for r in others + blocks:
        s, e = _t_to_minutes(r["start_time"]), _t_to_minutes(r["end_time"])
        if not (end_min <= s or start_min >= e):
            raise HTTPException(status_code=409, detail="Slot not available")
    previous = f"{b['date']} {b['start_time']}"
    new_doc = {"date": payload.new_date, "start_time": _minutes_to_t(start_min), "end_time": _minutes_to_t(end_min), "reminders_sent": []}
    await db.bookings.update_one({"id": b["id"]}, {"$set": new_doc})
    b.update(new_doc)
    await _create_owner_notification("customer_rescheduled", b, f"{b.get('customer_name')} rescheduled from {previous} to {b.get('date')} {b.get('start_time')}.")
    return await _self_serve_booking_response(b)


@api_router.post("/customer/cancel")
async def customer_cancel(payload: CustomerCancelPayload):
    b = await db.bookings.find_one({"id": payload.booking_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.get("customer_phone", "").strip() != payload.phone.strip():
        raise HTTPException(status_code=403, detail="Phone does not match")
    if b.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")
    if b.get("status") == "done":
        raise HTTPException(status_code=400, detail="Completed bookings cannot be cancelled")
    await db.bookings.update_one({"id": b["id"]}, {"$set": {"status": "cancelled"}})
    # Send a brief cancellation confirmation on WhatsApp (best-effort)
    try:
        service = await db.services.find_one({"id": b["service_id"]}, {"_id": 0})
        first_name = b.get("customer_name", "there").split()[0]
        _send_whatsapp_message(
            b["customer_phone"],
            f"Hi {first_name}, your Maison Aurelle booking for "
            f"{service.get('name','-') if service else '-'} on {_format_date_human(b['date'])} at {b['start_time']} "
            f"has been cancelled. Ref: {b['id'][:8].upper()}. We hope to see you again soon."
        )
    except Exception as e:
        logger.warning(f"Cancellation WhatsApp failed: {e}")
    return {"ok": True}


@api_router.get("/owner/revenue-trend")
async def owner_revenue_trend(days: int = Query(7, ge=1, le=60), salon_id: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    """Returns daily revenue + booking count for the last N days (inclusive of today)."""
    today = datetime.now(SALON_TZ).date()
    start = today - timedelta(days=days - 1)
    query: dict = {"date": {"$gte": start.isoformat(), "$lte": today.isoformat()}, "status": {"$in": ["upcoming", "done"]}}
    if salon_id:
        query["salon_id"] = salon_id
    rows = await db.bookings.find(
        query,
        {"_id": 0, "date": 1, "service_id": 1},
    ).to_list(5000)
    # Hydrate prices
    svc_ids = list({r["service_id"] for r in rows})
    services = {s["id"]: s for s in await db.services.find({"id": {"$in": svc_ids}}, {"_id": 0}).to_list(100)}
    by_date: dict = {}
    for r in rows:
        s = services.get(r["service_id"], {})
        d = r["date"]
        cur = by_date.setdefault(d, {"date": d, "revenue": 0.0, "count": 0})
        cur["revenue"] += float(s.get("price", 0))
        cur["count"] += 1
    series = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        series.append(by_date.get(d, {"date": d, "revenue": 0.0, "count": 0}))
    return {"series": series}


@api_router.get("/owner/no-shows")
async def owner_no_shows(month: Optional[str] = Query(None, description="YYYY-MM"), salon_id: Optional[str] = Query(None), _owner: dict = Depends(require_owner)):
    month_label, start, end = _month_bounds(month)
    query: dict = {"date": {"$gte": start, "$lte": end}}
    if salon_id:
        query["salon_id"] = salon_id
    bookings = await db.bookings.find(
        query,
        {"_id": 0},
    ).sort([("date", -1), ("start_time", 1)]).to_list(5000)
    return await _no_show_report(bookings, month_label, start, end)


async def _no_show_report(bookings: List[dict], month_label: str, start: str, end: str) -> dict:
    service_ids = list({b["service_id"] for b in bookings})
    stylist_ids = list({b["stylist_id"] for b in bookings})
    services = await _services_by_id(service_ids)
    stylists = await _stylists_by_id(stylist_ids)

    monthly_customer_totals: dict = {}
    no_show_rows = []
    considered_statuses = {"done", "no_show", "cancelled"}
    completed_or_missed = 0

    for b in bookings:
        status = b.get("status", "upcoming")
        if status in considered_statuses:
            completed_or_missed += 1
        if status != "no_show":
            continue
        phone = b.get("customer_phone", "")
        monthly_customer_totals[phone] = monthly_customer_totals.get(phone, 0) + 1
        service = services.get(b["service_id"], {})
        stylist = stylists.get(b["stylist_id"], {})
        row = dict(b)
        row["service"] = service
        row["stylist"] = stylist
        no_show_rows.append(row)

    lifetime_counts = {}
    phones = list({row.get("customer_phone", "") for row in no_show_rows if row.get("customer_phone")})
    if phones:
        lifetime_rows = await db.bookings.find(
            {"customer_phone": {"$in": phones}, "status": "no_show"},
            {"_id": 0, "customer_phone": 1},
        ).to_list(10000)
        for row in lifetime_rows:
            phone = row.get("customer_phone", "")
            lifetime_counts[phone] = lifetime_counts.get(phone, 0) + 1

    for row in no_show_rows:
        count = lifetime_counts.get(row.get("customer_phone", ""), 0)
        row["customer_no_show_count"] = count
        row["repeat_no_show"] = count >= 3

    rate = (len(no_show_rows) / completed_or_missed * 100) if completed_or_missed else 0.0
    return {
        "month": month_label,
        "start_date": start,
        "end_date": end,
        "total_no_shows": len(no_show_rows),
        "completed_or_missed": completed_or_missed,
        "no_show_rate": rate,
        "repeat_customers": sum(1 for phone in set(monthly_customer_totals) if lifetime_counts.get(phone, 0) >= 3),
        "no_shows": no_show_rows,
    }


@api_router.get("/owner/revenue-insights")
async def owner_revenue_insights(
    days: int = Query(30, ge=1, le=90),
    period: Optional[str] = Query(None, pattern="^(day|week|month|custom)$"),
    anchor_date: Optional[str] = Query(None, description="YYYY-MM-DD date inside the requested period"),
    start_date: Optional[str] = Query(None, description="Custom range start YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Custom range end YYYY-MM-DD"),
    salon_id: Optional[str] = Query(None),
    _owner: dict = Depends(require_owner),
):
    period_key, anchor, start, end, period_label = _revenue_period_bounds(period, anchor_date, days, start_date, end_date)

    query: dict = {"date": {"$gte": start, "$lte": end}}
    if salon_id:
        query["salon_id"] = salon_id
    bookings = await db.bookings.find(
        query,
        {"_id": 0},
    ).to_list(10000)
    return await _revenue_insights_from_bookings(bookings, period_key, anchor, start, end, period_label)


async def _revenue_insights_from_bookings(bookings: List[dict], period_key: str, anchor: str, start: str, end: str, period_label: str) -> dict:
    service_ids = list({b["service_id"] for b in bookings})
    stylist_ids = list({b["stylist_id"] for b in bookings})
    services = await _services_by_id(service_ids)
    stylists = await _stylists_by_id(stylist_ids)

    status_counts = {"upcoming": 0, "done": 0, "no_show": 0, "cancelled": 0}
    revenue_today = 0.0
    revenue_week = 0.0
    revenue_month = 0.0
    revenue_total = 0.0
    paid_booking_count = 0
    per_stylist: dict = {}
    per_service: dict = {}
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    range_days = (end_date - start_date).days + 1
    by_weekday = {i: {"weekday": i, "label": (start_date + timedelta(days=(i - start_date.weekday()) % 7)).strftime("%a"), "revenue": 0.0, "count": 0} for i in range(7)}
    by_date = {}
    for offset in range(range_days):
        d = start_date + timedelta(days=offset)
        if period_key == "month":
            label = d.strftime("%-d")
        elif period_key == "day":
            label = d.strftime("%d %b")
        elif period_key == "custom":
            # For custom ranges pick a sensible density based on span length.
            if range_days <= 7:
                label = d.strftime("%a")
            elif range_days <= 31:
                label = d.strftime("%-d %b")
            else:
                label = d.strftime("%d/%m")
        else:
            label = d.strftime("%a")
        by_date[d.isoformat()] = {"date": d.isoformat(), "label": label, "revenue": 0.0, "count": 0}

    for b in bookings:
        status = b.get("status", "upcoming")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status not in {"done", "upcoming"}:
            continue
        service = services.get(b["service_id"], {})
        stylist = stylists.get(b["stylist_id"], {})
        price = float(service.get("price", 0))
        try:
            b_date = datetime.strptime(b["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        revenue_total += price
        paid_booking_count += 1
        revenue_today += price
        revenue_week += price
        revenue_month += price
        _add_metric(per_stylist, b["stylist_id"], stylist.get("name", b["stylist_id"]), price)
        _add_metric(per_service, b["service_id"], service.get("name", b["service_id"]), price)
        weekday = b_date.weekday()
        by_weekday[weekday]["revenue"] += price
        by_weekday[weekday]["count"] += 1
        if b["date"] in by_date:
            by_date[b["date"]]["revenue"] += price
            by_date[b["date"]]["count"] += 1

    average_booking_value = revenue_total / paid_booking_count if paid_booking_count else 0.0
    return {
        "range": {
            "days": range_days,
            "period": period_key,
            "anchor_date": anchor,
            "start_date": start,
            "end_date": end,
            "label": period_label,
        },
        "kpis": {
            "today_revenue": revenue_today,
            "week_revenue": revenue_week,
            "month_revenue": revenue_month,
            "total_revenue": revenue_total,
            "average_booking_value": average_booking_value,
            "paid_booking_count": paid_booking_count,
        },
        "status_counts": status_counts,
        "revenue_per_stylist": sorted(per_stylist.values(), key=lambda x: x["revenue"], reverse=True),
        "revenue_per_service": sorted(per_service.values(), key=lambda x: x["revenue"], reverse=True),
        "revenue_by_weekday": [by_weekday[i] for i in range(7)],
        "revenue_series": [by_date[(start_date + timedelta(days=offset)).isoformat()] for offset in range(range_days)],
    }


@api_router.post("/twilio/inbound")
async def twilio_inbound(From: str = Form(""), Body: str = Form("")):
    """Twilio WhatsApp webhook for inbound replies. Supports: 'CONFIRM <ref>' / 'CANCEL <ref>'."""
    phone = From.replace("whatsapp:", "").strip()
    text = (Body or "").strip().upper()
    if not text:
        return {"reply": "Please reply with CONFIRM <reference> or CANCEL <reference>."}
    parts = text.split()
    action = parts[0]
    ref = parts[1] if len(parts) > 1 else None
    if action not in {"CONFIRM", "CANCEL"} or not ref:
        return {"reply": "Format: CONFIRM <ref> or CANCEL <ref>."}
    # Find booking by ref prefix + phone
    candidates = await db.bookings.find({"customer_phone": phone}, {"_id": 0}).to_list(50)
    match = next((b for b in candidates if b["id"][:8].upper() == ref), None)
    if not match:
        return {"reply": f"No booking found for reference {ref}."}
    if action == "CANCEL":
        if match.get("status") == "cancelled":
            return {"reply": "Already cancelled."}
        await db.bookings.update_one({"id": match["id"]}, {"$set": {"status": "cancelled"}})
        return {"reply": f"Booking {ref} cancelled. We hope to see you again soon."}
    return {"reply": f"Booking {ref} confirmed. See you soon!"}


@api_router.post("/lookup")
async def customer_lookup(payload: LookupRequest):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")
    candidates = await db.bookings.find(
        {"customer_phone": phone, "status": {"$ne": "cancelled"}},
        {"_id": 0},
    ).sort([("date", 1), ("start_time", 1)]).to_list(50)
    matched = [b for b in candidates if _matches_code(b["id"], payload.code)]
    for b in matched:
        await _hydrate(b)
    return {"bookings": matched}


@api_router.post("/customer/reschedule")
async def reschedule(payload: RescheduleRequest):
    b = await db.bookings.find_one({"id": payload.booking_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.get("customer_phone", "").strip() != payload.phone.strip():
        raise HTTPException(status_code=403, detail="Phone does not match")
    if b.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Booking already cancelled")

    service = await _get_service(b["service_id"])
    stylist = await _get_stylist(b["stylist_id"])

    try:
        new_date_d = datetime.strptime(payload.new_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    if new_date_d < datetime.now(SALON_TZ).date():
        raise HTTPException(status_code=400, detail="Cannot reschedule to a past date")

    start_min = _t_to_minutes(payload.new_start_time)
    end_min = start_min + service["duration_min"]

    # Working hours
    weekday = new_date_d.weekday()
    wh = (stylist.get("working_hours") or {}).get(str(weekday))
    if not wh:
        raise HTTPException(status_code=400, detail="Stylist not working that day")
    if start_min < _t_to_minutes(wh["open"]) or end_min > _t_to_minutes(wh["close"]):
        raise HTTPException(status_code=400, detail="Slot outside working hours")

    # Conflict check (exclude this booking)
    others = await db.bookings.find(
        {"stylist_id": b["stylist_id"], "date": payload.new_date, "status": {"$ne": "cancelled"}, "id": {"$ne": b["id"]}},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(500)
    blocks = await db.stylist_blocks.find(
        {"stylist_id": b["stylist_id"], "date": payload.new_date},
        {"_id": 0, "start_time": 1, "end_time": 1},
    ).to_list(500)
    for r in others + blocks:
        s, e = _t_to_minutes(r["start_time"]), _t_to_minutes(r["end_time"])
        if not (end_min <= s or start_min >= e):
            raise HTTPException(status_code=409, detail="Slot not available")

    new_doc = {
        "date": payload.new_date,
        "start_time": _minutes_to_t(start_min),
        "end_time": _minutes_to_t(end_min),
        "reminders_sent": [],  # reset reminders for new time
    }
    await db.bookings.update_one({"id": b["id"]}, {"$set": new_doc})
    updated = await db.bookings.find_one({"id": b["id"]}, {"_id": 0})
    await _hydrate(updated)
    return {"booking": updated}


# ============================================================
# Seed on startup
# ============================================================
@app.on_event("startup")
async def seed_data():
    try:
        await _ensure_default_salon()
        for s in SEED_SERVICES:
            await db.services.update_one({"id": s["id"]}, {"$set": s}, upsert=True)
        for st in SEED_STYLISTS:
            # Always update display fields; only set pin/working_hours on insert
            update_fields = {k: v for k, v in st.items() if k not in ("pin", "working_hours")}
            await db.stylists.update_one(
                {"id": st["id"]},
                {
                    "$set": update_fields,
                    "$setOnInsert": {"pin": st["pin"], "working_hours": st["working_hours"]},
                },
                upsert=True,
            )
            # Ensure pin/working_hours exist for already-seeded docs
            existing = await db.stylists.find_one({"id": st["id"]}, {"_id": 0, "pin": 1, "working_hours": 1})
            if not existing.get("pin"):
                await db.stylists.update_one({"id": st["id"]}, {"$set": {"pin": st["pin"]}})
            if not existing.get("working_hours"):
                await db.stylists.update_one({"id": st["id"]}, {"$set": {"working_hours": st["working_hours"]}})

        today = _today_local_date()
        demo_docs = []
        for offset in range(1, 91):
            day = today - timedelta(days=offset)
            demo_docs.extend(_demo_booking_docs_for_day(day))
        await db.bookings.delete_many({"demo_seed": True})
        for doc in demo_docs:
            await db.bookings.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        logger.info(f"Historical demo bookings ensured: {len(demo_docs)} docs.")
        logger.info("Seed data ensured for services & stylists.")
    except Exception as e:
        logging.getLogger(__name__).error(f"Seed failed: {e}")


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone=SALON_TZ)
    _scheduler.add_job(run_reminder_tick, "interval", minutes=1, id="reminders", max_instances=1, coalesce=True)
    _scheduler.start()
    logger.info("Reminder scheduler started.")


@app.on_event("startup")
async def init_object_storage():
    storage.init_storage()


@app.on_event("shutdown")
async def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
