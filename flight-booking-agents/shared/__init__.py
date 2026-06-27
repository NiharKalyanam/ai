# shared package — imported by all agents
from .models import (
    Flight, FlightSearchRequest, FlightSearchResult,
    BookingRequest, Booking, CancelRequest,
    WebhookEvent, Notification
)
from .database import (
    get_all_flights, get_flight_by_id,
    get_all_bookings, get_booking_by_id,
    save_booking, update_booking,
    decrement_seat, increment_seat
)
