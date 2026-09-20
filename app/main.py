import json
import time
import uuid
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest
from starlette.responses import JSONResponse

app = FastAPI(title="Campus Room Booking API")

bookings = {}
booking_lock = Lock()

fault_enabled = False
create_request_number = 0


# Application metrics
HTTP_REQUESTS = Counter(
    "room_booking_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

HTTP_DURATION = Histogram(
    "room_booking_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2],
)


# Business metrics
BOOKING_EVENTS = Counter(
    "room_booking_events_total",
    "Booking business events",
    ["action", "result"],
)

ACTIVE_BOOKINGS = Gauge(
    "room_booking_active_bookings",
    "Current number of active bookings",
)

VALIDATION_DURATION = Summary(
    "room_booking_validation_duration_seconds",
    "Time spent validating booking requests",
)


class BookingRequest(BaseModel):
    room: str = Field(min_length=1, max_length=30)
    duration_minutes: int = Field(ge=15, le=180)


def write_log(
    severity: str,
    message: str,
    request_id: str,
    **extra,
):
    event = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "room-booking-api",
        "severity": severity,
        "message": message,
        "request_id": request_id,
        **extra,
    }

    print(json.dumps(event), flush=True)


@app.middleware("http")
async def observe_request(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        write_log(
            "ERROR",
            "unhandled request error",
            request_id,
            method=request.method,
            path=request.url.path,
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    duration = time.perf_counter() - started

    route_object = request.scope.get("route")
    route = getattr(route_object, "path", request.url.path)

    HTTP_REQUESTS.labels(
        method=request.method,
        route=route,
        status=str(status),
    ).inc()

    HTTP_DURATION.labels(
        method=request.method,
        route=route,
    ).observe(duration)

    write_log(
        "INFO" if status < 400 else "WARNING",
        "request completed",
        request_id,
        method=request.method,
        route=route,
        status=status,
        duration_ms=round(duration * 1000, 2),
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/bookings")
def list_bookings():
    return {"bookings": list(bookings.values())}


@app.post("/bookings", status_code=201)
def create_booking(booking: BookingRequest):
    global create_request_number

    create_request_number += 1

    if fault_enabled and create_request_number % 5 == 0:
        time.sleep(0.5)

    validation_started = time.perf_counter()

    with booking_lock:
        room_in_use = any(
            existing["room"].lower() == booking.room.lower()
            for existing in bookings.values()
        )

        if room_in_use:
            VALIDATION_DURATION.observe(
                time.perf_counter() - validation_started
            )
            BOOKING_EVENTS.labels(
                action="create",
                result="rejected",
            ).inc()
            raise HTTPException(
                status_code=409,
                detail="Room already has an active booking",
            )

        booking_id = str(uuid.uuid4())

        stored_booking = {
            "id": booking_id,
            "room": booking.room,
            "duration_minutes": booking.duration_minutes,
        }

        bookings[booking_id] = stored_booking

    VALIDATION_DURATION.observe(time.perf_counter() - validation_started)
    BOOKING_EVENTS.labels(action="create", result="success").inc()
    ACTIVE_BOOKINGS.inc()

    return stored_booking


@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    with booking_lock:
        if booking_id not in bookings:
            BOOKING_EVENTS.labels(
                action="cancel",
                result="rejected",
            ).inc()
            raise HTTPException(status_code=404, detail="Booking not found")

        cancelled = bookings.pop(booking_id)

    BOOKING_EVENTS.labels(action="cancel", result="success").inc()
    ACTIVE_BOOKINGS.dec()

    return {"cancelled": cancelled}


@app.post("/fault/slow")
def configure_slow_fault(enabled: bool):
    global fault_enabled
    fault_enabled = enabled
    return {"slow_fault_enabled": fault_enabled}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4",
    )