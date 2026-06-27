"""

HOW TO ACTIVATE:
  1. Install PostgreSQL
  2. pip3 install psycopg2-binary
  3. Add to .env:
       DB_HOST=localhost
       DB_PORT=5432
       DB_NAME=flights
       DB_USER=postgres
       DB_PASSWORD=yourpassword
  4. Change USE_DB=postgres in .env
  5. tools.py auto-switches to this adapter

NOTE:
  This is a TEMPLATE showing the pattern.
  Fill in the actual SQL queries when you're ready to use it.
  The function signatures are IDENTICAL to json_adapter.py —
  that's the whole point of adapters.
"""

# TO USE THIS:
# pip3 install psycopg2-binary
# import psycopg2
# import os

def create_booking(flight_id: str, passenger_name: str, email: str, seat_class: str) -> dict:
    """
    Save booking to PostgreSQL.
    Same signature as json_adapter.create_booking().
    """
    # conn = psycopg2.connect(
    #     host=os.getenv("DB_HOST"),
    #     port=os.getenv("DB_PORT"),
    #     dbname=os.getenv("DB_NAME"),
    #     user=os.getenv("DB_USER"),
    #     password=os.getenv("DB_PASSWORD")
    # )
    # cursor = conn.cursor()
    # cursor.execute(
    #     "INSERT INTO bookings (flight_id, passenger_name, email) VALUES (%s, %s, %s)",
    #     (flight_id, passenger_name, email)
    # )
    # conn.commit()
    raise NotImplementedError("PostgreSQL adapter not configured yet. Use json_adapter.")


def cancel_booking(booking_id: str, reason: str) -> dict:
    """Cancel booking in PostgreSQL. Same signature as json_adapter."""
    raise NotImplementedError("PostgreSQL adapter not configured yet.")


def get_booking(booking_id: str) -> dict:
    """Get booking from PostgreSQL. Same signature as json_adapter."""
    raise NotImplementedError("PostgreSQL adapter not configured yet.")


def get_all() -> dict:
    """Get all bookings from PostgreSQL. Same signature as json_adapter."""
    raise NotImplementedError("PostgreSQL adapter not configured yet.")
