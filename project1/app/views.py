from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
import random
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from django.core.mail import EmailMessage
import io
from django.http import JsonResponse
from .travel_data import STATIONS, TRAINS, CLASS_MULTIPLIERS
from datetime import datetime
from datetime import datetime as dt
import json
import requests
import re
import cv2
import pytesseract
from django.core.files.storage import FileSystemStorage
from .travel_data import STATIONS, TRAINS, CLASS_MULTIPLIERS, STATION_COORDINATES

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# =========================================================
# HOME
# =========================================================

def home(request):
    return render(request, "home.html")


# =========================================================
# SIGNUP
# =========================================================

def signup(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        location = request.POST.get("location")
        zipcode = request.POST.get("zipcode")
        gender = request.POST.get("gender")
        dob = request.POST.get("dob")
        role = request.POST.get("role")

        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match."})

        password = make_password(password)

        query = """
            INSERT INTO USERS
            (name, email, phone, password, location, zipcode, gender, dob, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [
                    name, email, phone, password, location, zipcode,
                    gender, dob if dob else None, role
                ])
        except IntegrityError:
            return render(request, "signup.html", {"error": "Email or phone number already exists."})

        return render(request, "login.html", {"success": "Account created successfully. Please login."})

    return render(request, "signup.html")


# =========================================================
# LOGIN
# =========================================================

def login(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        query = """
            SELECT user_id, name, email, password, role
            FROM USERS
            WHERE email = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [email])
            user = cursor.fetchone()

        if not user:
            return render(request, "login.html", {"error": "Invalid email or password."})

        user_id = user[0]
        name = user[1]
        user_email = user[2]
        hashed_password = user[3]
        role = user[4]

        if not check_password(password, hashed_password):
            return render(request, "login.html", {"error": "Invalid email or password."})

        request.session["user_id"] = user_id
        request.session["name"] = name
        request.session["email"] = user_email
        request.session["role"] = role

        if role == "customer":
            return redirect("customer_dashboard")
        elif role == "provider":
            return redirect("provider_dashboard")
        elif role == "admin":
            return redirect("admin_dashboard")
        else:
            return render(request, "login.html", {"error": "Invalid user role."})

    return render(request, "login.html")


# =========================================================
# FORGOT PASSWORD
# =========================================================

def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        query = """
            SELECT user_id, name, role
            FROM USERS
            WHERE email = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [email])
            user = cursor.fetchone()

        if not user:
            return render(request, "forgot_password.html", {"error": "No account found with this email."})

        user_id = user[0]
        name = user[1]
        role = user[2]

        otp = str(random.randint(100000, 999999))

        request.session["reset_user_id"] = user_id
        request.session["reset_email"] = email
        request.session["reset_name"] = name
        request.session["reset_role"] = role
        request.session["reset_otp"] = otp
        request.session["otp_verified"] = False

        send_mail(
            "Smart Journey Assistant - Password Reset OTP",
            f"""
Hello {name},

Your Smart Journey Assistant password reset OTP is:

{otp}

Please enter this OTP on the verification page.

Regards,
Smart Journey Assistant
""",
            "p90448704@gmail.com",
            [email],
            fail_silently=False
        )

        return redirect("verify_otp")

    return render(request, "forgot_password.html")


# =========================================================
# VERIFY OTP
# =========================================================

def verify_otp(request):

    if not request.session.get("reset_otp"):
        return redirect("forgot_password")

    if request.method == "POST":

        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("reset_otp")
        email = request.session.get("reset_email")

        if entered_otp != saved_otp:
            return render(request, "verify_otp.html", {"error": "Invalid OTP. Please try again.", "email": email})

        request.session["otp_verified"] = True
        return redirect("reset_password")

    return render(request, "verify_otp.html")


# =========================================================
# RESEND OTP
# =========================================================

def resend_otp(request):

    email = request.session.get("reset_email")
    user_id = request.session.get("reset_user_id")

    if not email or not user_id:
        return redirect("forgot_password")

    query = "SELECT name FROM USERS WHERE user_id = %s"

    with connection.cursor() as cursor:
        cursor.execute(query, [user_id])
        user = cursor.fetchone()

    if not user:
        return redirect("forgot_password")

    name = user[0]

    otp = str(random.randint(100000, 999999))

    request.session["reset_otp"] = otp
    request.session["otp_verified"] = False

    send_mail(
        "Smart Journey Assistant - New Password Reset OTP",
        f"""
Hello {name},

Your new Smart Journey Assistant password reset OTP is:

{otp}

Please use this OTP to continue.

Regards,
Smart Journey Assistant
""",
        "p90448704@gmail.com",
        [email],
        fail_silently=False
    )

    return redirect("verify_otp")


# =========================================================
# RESET PASSWORD
# =========================================================

def reset_password(request):

    if not request.session.get("otp_verified"):
        return redirect("forgot_password")

    user_id = request.session.get("reset_user_id")

    if not user_id:
        return redirect("forgot_password")

    if request.method == "POST":

        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "reset_password.html", {"error": "Passwords do not match."})

        hashed_password = make_password(password)

        query = "UPDATE USERS SET password = %s WHERE user_id = %s"

        with connection.cursor() as cursor:
            cursor.execute(query, [hashed_password, user_id])

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_email", None)
        request.session.pop("reset_name", None)
        request.session.pop("reset_role", None)
        request.session.pop("reset_otp", None)
        request.session.pop("otp_verified", None)

        return render(request, "login.html", {"success": "Password reset successfully. Please login."})

    return render(request, "reset_password.html")


# =========================================================
# CUSTOMER DASHBOARD
# =========================================================

def customer_dashboard(request):
    return render(request, "customer_dashboard.html")


def profile(request):

    email = request.session.get('email')

    if not email:
        return redirect('login')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, name, email, phone, location, zipcode, gender, dob, role, created_at
            FROM users
            WHERE email = %s
        """, [email])
        user = cursor.fetchone()

    if not user:
        return render(request, 'profile.html', {'error': 'User details not found.'})

    user_data = {
        'user_id': user[0], 'name': user[1], 'email': user[2], 'phone': user[3],
        'location': user[4], 'zipcode': user[5], 'gender': user[6], 'dob': user[7],
        'role': user[8], 'created_at': user[9],
    }

    return render(request, 'profile.html', {'user': user_data})


# =========================================================
# CHATBOT
# =========================================================

def chatbot(request):

    email = request.session.get('email')

    if not email:
        return redirect('login')

    if request.method == "POST":
        try:
            gemini_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-3.6-flash:generateContent?key={settings.GEMINI_API_KEY}"
            )

            payload = {
                "systemInstruction": {
                    "parts": [{"text": (
                        "You are Smart Journey Assistant, "
                        "a helpful travel assistant. "
                        "Help users with travel planning, "
                        "hotels, transportation, nearby places, "
                        "trains, maps and general journey questions. "
                        "Give clear and useful answers."
                    )}]
                },
                "contents": [{"parts": [{"text": user_message}]}]
            }

            gemini_response = requests.post(gemini_url, json=payload, timeout=20)
            gemini_data = gemini_response.json()
            reply = gemini_data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as e:
            reply = f"Sorry, I could not process your request: {str(e)}"

        return JsonResponse({"reply": reply})

    return render(request, "chatbot.html")


# =========================================================
# NEARBY PLACES
# =========================================================

def nearby_places(request):

    if not request.session.get('email'):
        return redirect('login')

    return render(request, "nearby_places.html")


def search_nearby(request):

    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    category = request.GET.get('category', 'hotel')

    if not lat or not lon:
        return JsonResponse({"error": "Location required"}, status=400)

    category_tags = {
        "hotel": '["tourism"="hotel"]',
        "pg": '["tourism"="guest_house"]',
        "hospital": '["amenity"="hospital"]',
        "restaurant": '["amenity"="restaurant"]',
    }

    tag_filter = category_tags.get(category, category_tags["hotel"])

    overpass_query = f"""
    [out:json][timeout:25];
    (
      node{tag_filter}(around:3000,{lat},{lon});
      way{tag_filter}(around:3000,{lat},{lon});
    );
    out center 20;
    """

    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    data = None
    last_error = None

    for mirror in mirrors:
        try:
            response = requests.post(
                mirror,
                data={"data": overpass_query},
                timeout=15,
                headers={"User-Agent": "SmartJourneyAssistant/1.0"}
            )

            if response.status_code != 200:
                last_error = f"Server returned status {response.status_code}"
                continue

            data = response.json()
            break

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)}"
            continue

    if data is None:
        return JsonResponse({"error": last_error or "Could not reach map service."}, status=500)

    results = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")

        if not name:
            continue

        if element["type"] == "node":
            place_lat = element.get("lat")
            place_lon = element.get("lon")
        else:
            center = element.get("center", {})
            place_lat = center.get("lat")
            place_lon = center.get("lon")

        if place_lat is None or place_lon is None:
            continue

        address_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:suburb", ""),
            tags.get("addr:city", ""),
        ]
        address = ", ".join([p for p in address_parts if p]) or "Address not available"
        image_url = tags.get("image")

        results.append({
            "name": name,
            "address": address,
            "phone": tags.get("phone", tags.get("contact:phone", "Not listed")),
            "lat": place_lat,
            "lon": place_lon,
            "image": image_url,
        })

    return JsonResponse({"places": results})


# =========================================================
# SMART TRAIN ASSISTANT - OCR TICKET UPLOAD
# =========================================================

def extract_ticket_data(image_path):

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    data = {}

    pnr_match = re.search(r'PNR\s*[:\-]?\s*(\d{10})', text, re.IGNORECASE)
    if pnr_match:
        data['pnr_number'] = pnr_match.group(1)

    train_no_match = re.search(r'Train\s*No\.?\s*[:\-]?\s*(\d{5})', text, re.IGNORECASE)
    if train_no_match:
        data['train_number'] = train_no_match.group(1)

    date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', text)
    if date_match:
        data['journey_date'] = date_match.group(1)

    time_match = re.search(r'(\d{1,2}:\d{2})', text)
    if time_match:
        data['departure_time'] = time_match.group(1)

    return data


def validate_ticket_format(data):

    errors = []

    pnr = data.get('pnr_number', '')
    if not re.fullmatch(r'\d{10}', pnr):
        errors.append("PNR should be exactly 10 digits.")

    train_number = data.get('train_number', '')
    if not re.fullmatch(r'\d{5}', train_number):
        errors.append("Train number should be exactly 5 digits.")

    journey_date = data.get('journey_date', '')
    if journey_date:
        parsed_date = None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
            try:
                parsed_date = dt.strptime(journey_date, fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            errors.append("Journey date format not recognized.")
    else:
        errors.append("Journey date not found on ticket.")

    departure_time = data.get('departure_time', '')
    if not re.fullmatch(r'([01]?\d|2[0-3]):[0-5]\d', departure_time):
        errors.append("Departure time format not recognized.")

    is_valid = len(errors) == 0

    return is_valid, errors


def upload_ticket(request):

    if not request.session.get('email'):
        return redirect('login')

    extracted_data = None
    validation_errors = []
    is_valid = False
    error = None

    if request.method == "POST" and request.FILES.get('ticket_image'):

        ticket_file = request.FILES['ticket_image']
        fs = FileSystemStorage()
        filename = fs.save(ticket_file.name, ticket_file)
        file_path = fs.path(filename)

        try:
            extracted_data = extract_ticket_data(file_path)

            if not extracted_data.get('pnr_number') and not extracted_data.get('train_number'):
                error = "Could not read ticket details clearly. Please upload a clearer photo, or enter details manually below."
            else:
                is_valid, validation_errors = validate_ticket_format(extracted_data)
                request.session['pending_ticket'] = extracted_data
                request.session['pending_ticket_valid'] = is_valid

        except Exception as e:
            error = f"Error processing ticket: {str(e)}"

        finally:
            fs.delete(filename)

    return render(request, "upload_ticket.html", {
        "extracted_data": extracted_data,
        "validation_errors": validation_errors,
        "is_valid": is_valid,
        "error": error,
        "stations": STATIONS,
    })


def confirm_ticket(request):

    if not request.session.get('email'):
        return redirect('login')

    if request.method == "POST":

        tracking_data = {
            "pnr_number": request.POST.get('pnr_number'),
            "train_number": request.POST.get('train_number'),
            "train_name": request.POST.get('train_name'),
            "source_station": request.POST.get('source_station'),
            "destination_station": request.POST.get('destination_station'),
            "journey_date": request.POST.get('journey_date'),
            "departure_time": request.POST.get('departure_time'),
        }

        is_valid, errors = validate_ticket_format({
            "pnr_number": tracking_data["pnr_number"],
            "train_number": tracking_data["train_number"],
            "journey_date": tracking_data["journey_date"],
            "departure_time": tracking_data["departure_time"],
        })

        tracking_data["format_valid"] = is_valid

        request.session['tracking_ticket'] = tracking_data
        request.session.pop('pending_ticket', None)

        return redirect('live_tracking')

    return redirect('upload_ticket')


# =========================================================
# PROVIDER DASHBOARD
# =========================================================

def provider_dashboard(request):

    if not request.session.get("email"):
        return redirect("login")

    if request.session.get("role") != "provider":
        return redirect("login")

    provider_id = request.session.get("user_id")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT service_id, provider_id, service_type, service_name, description,
                   location, price, rating, status, created_at
            FROM services
            WHERE provider_id = %s
            ORDER BY service_id DESC
        """, [provider_id])
        services = cursor.fetchall()

    return render(request, "provider_dashboard.html", {"services": services})


def provider_profile(request):

    email = request.session.get('email')

    if not email:
        return redirect('login')

    if request.session.get('role') != 'provider':
        return redirect('login')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, name, email, phone, location, zipcode, gender, dob, role, created_at
            FROM users
            WHERE email = %s
        """, [email])
        provider = cursor.fetchone()

    if not provider:
        return render(request, 'provider_profile.html', {'error': 'Provider details not found.'})

    provider_data = {
        'user_id': provider[0], 'name': provider[1], 'email': provider[2], 'phone': provider[3],
        'location': provider[4], 'zipcode': provider[5], 'gender': provider[6], 'dob': provider[7],
        'role': provider[8], 'created_at': provider[9],
    }

    return render(request, 'provider_profile.html', {'provider': provider_data})


# =========================================================
# ADMIN DASHBOARD
# =========================================================

def admin_dashboard(request):

    if not request.session.get("email"):
        return redirect("login")

    if request.session.get("role") != "admin":
        return redirect("login")

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT user_id, name, email, phone, location, zipcode, gender, dob, role, created_at
            FROM users
            ORDER BY user_id DESC
        """)
        users = cursor.fetchall()

        cursor.execute("""
            SELECT service_id, provider_id, service_type, service_name, description,
                   location, price, rating, status, created_at
            FROM services
            ORDER BY service_id DESC
        """)
        services = cursor.fetchall()

        cursor.execute("""
            SELECT booking_id, user_id, service_id, booking_date, booking_time,
                   quantity, total_amount, booking_status, payment_status, created_at
            FROM bookings
            ORDER BY booking_id DESC
        """)
        bookings = cursor.fetchall()

    return render(request, "admin_dashboard.html", {
        "users": users, "services": services, "bookings": bookings
    })


def delete_user(request, user_id):

    if request.session.get('role') != 'admin':
        return redirect('login')

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id = %s", [user_id])
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


def delete_service(request, service_id):

    if request.session.get('role') != 'admin':
        return redirect('login')

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM services WHERE service_id = %s", [service_id])
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


def delete_booking(request, booking_id):

    if request.session.get('role') != 'admin':
        return redirect('login')

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM bookings WHERE booking_id = %s", [booking_id])
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


def update_user(request, user_id):

    if request.session.get('role') != 'admin':
        return redirect('login')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, name, email, phone, location, zipcode, gender, dob, role
            FROM users
            WHERE user_id = %s
        """, [user_id])
        user = cursor.fetchone()

    if not user:
        return redirect('admin_dashboard')

    if request.method == 'POST':

        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        location = request.POST.get('location')
        zipcode = request.POST.get('zipcode')
        gender = request.POST.get('gender')
        dob = request.POST.get('dob')
        role = request.POST.get('role')

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users
                SET name = %s, email = %s, phone = %s, location = %s,
                    zipcode = %s, gender = %s, dob = %s, role = %s
                WHERE user_id = %s
            """, [name, email, phone, location, zipcode, gender,
                  dob if dob else None, role, user_id])

        return redirect('admin_dashboard')

    return render(request, 'update_user.html', {'user': user})


# =========================================================
# TRAIN BOOKING
# =========================================================

def book_train(request):

    if not request.session.get('email'):
        return redirect('login')

    if request.method == "POST":

        passenger_name = request.POST.get('passenger_name')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        train_name = request.POST.get('train_name')
        train_number = request.POST.get('train_number')
        source = request.POST.get('source')
        destination = request.POST.get('destination')
        journey_date = request.POST.get('journey_date')
        departure_time = request.POST.get('departure_time')
        seat_class = request.POST.get('seat_class')
        total_amount = request.POST.get('total_amount')

        pnr = str(random.randint(1000000000, 9999999999))
        seat_number = f"{random.choice(['A1','B2','C3','S4'])}-{random.randint(1,72)}"

        user_id = request.session.get('user_id')
        user_email = request.session.get('email')

        TRAIN_BOOKING_SERVICE_ID = 1  # <-- replace with your actual service_id

        insert_query = """
            INSERT INTO bookings
            (user_id, service_id, booking_date, booking_time, quantity, total_amount, booking_status, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        with connection.cursor() as cursor:
            cursor.execute(insert_query, [
                user_id, TRAIN_BOOKING_SERVICE_ID, journey_date, departure_time,
                1, total_amount, 'confirmed', 'paid'
            ])

        pdf_buffer = generate_ticket_pdf(
            passenger_name, age, gender, train_name, train_number,
            source, destination, journey_date, departure_time,
            seat_class, seat_number, pnr, total_amount
        )

        email = EmailMessage(
            subject="Your Smart Assistant Booking Platform - E-Ticket",
            body=f"Hello {passenger_name},\n\nYour train ticket is attached.\n\nPNR: {pnr}\nFare: Rs. {total_amount}\n\nThis is a demo booking for showcase purposes only.\n\nRegards,\nSmart Assistant Booking Platform",
            from_email="p90448704@gmail.com",
            to=[user_email],
        )
        email.attach(f"ticket_{pnr}.pdf", pdf_buffer.getvalue(), "application/pdf")
        email.send(fail_silently=False)

        request.session['last_booking'] = {
            "pnr": pnr,
            "passenger_name": passenger_name
        }
        return redirect('booking_success')

    return render(request, "book_train.html", {"stations": STATIONS})


def booking_success(request):

    booking = request.session.get('last_booking')

    if not booking:
        return redirect('customer_dashboard')

    return render(request, "booking_success.html", booking)


def generate_ticket_pdf(name, age, gender, train_name, train_number,
                          source, destination, date, dep_time,
                          seat_class, seat_number, pnr, total_amount):

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFillColorRGB(0.96, 0.96, 0.86)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    p.setFillColorRGB(0.07, 0.07, 0.07)
    p.rect(0, height - 30*mm, width, 30*mm, fill=1, stroke=0)
    p.setFillColorRGB(0.22, 0.74, 0.97)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(20*mm, height - 18*mm, "SMART ASSISTANT BOOKING PLATFORM")
    p.setFillColorRGB(0.96, 0.96, 0.86)
    p.setFont("Helvetica", 10)
    p.drawString(20*mm, height - 25*mm, "E-Ticket (Demo Booking - Not a real travel document)")

    p.setFillColorRGB(0, 0, 0)
    y = height - 45*mm

    fields = [
        ("PNR Number", pnr),
        ("Passenger Name", name),
        ("Age / Gender", f"{age} / {gender}"),
        ("Train", f"{train_name} ({train_number})"),
        ("From", source),
        ("To", destination),
        ("Journey Date", date),
        ("Departure Time", dep_time),
        ("Class", seat_class),
        ("Seat Number", seat_number),
        ("Fare", f"Rs. {total_amount}"),
    ]

    p.setFont("Helvetica-Bold", 11)
    for label, value in fields:
        p.drawString(20*mm, y, f"{label}:")
        p.setFont("Helvetica", 11)
        p.drawString(70*mm, y, str(value))
        p.setFont("Helvetica-Bold", 11)
        y -= 8*mm

    p.setFont("Helvetica-Oblique", 8)
    p.drawString(20*mm, 15*mm, "This is a demonstration ticket generated for project showcase purposes only.")
    p.drawString(20*mm, 11*mm, "Not valid for actual travel. Not issued by Indian Railways / IRCTC.")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def search_stations(request):
    query = request.GET.get('q', '').lower()
    matches = [s for s in STATIONS if query in s.lower()][:8]
    return JsonResponse({"stations": matches})


def search_trains(request):

    source = request.GET.get('source', '')
    destination = request.GET.get('destination', '')
    journey_date = request.GET.get('date', '')

    day_name = ""
    if journey_date:
        day_name = datetime.strptime(journey_date, "%Y-%m-%d").strftime("%a")

    results = []
    for train in TRAINS:
        if train['source'] == source and train['destination'] == destination:
            if "Daily" in train['running_days'] or day_name in train['running_days']:
                results.append(train)

    return JsonResponse({"trains": results, "class_multipliers": CLASS_MULTIPLIERS})
def track_by_train_number(request):

    if not request.session.get('email'):
        return redirect('login')

    if request.method == "POST":

        train_number = request.POST.get('train_number', '').strip()
        source_station = request.POST.get('source_station', '')

        if not re.fullmatch(r'\d{5}', train_number):
            return render(request, "upload_ticket.html", {
                "stations": STATIONS,
                "error": "Please enter a valid 5-digit train number."
            })

        tracking_data = {
            "pnr_number": None,
            "train_number": train_number,
            "train_name": None,
            "source_station": source_station,
            "destination_station": None,
            "journey_date": None,
            "departure_time": None,
            "format_valid": None,
        }

        request.session['tracking_ticket'] = tracking_data

        return redirect('live_tracking')

    return redirect('upload_ticket')
def live_tracking(request):

    if not request.session.get('email'):
        return redirect('login')

    ticket = request.session.get('tracking_ticket')

    if not ticket:
        return redirect('upload_ticket')

    return render(request, "live_tracking.html", {
        "ticket": ticket,
        "railradar_key": settings.RAILRADAR_API_KEY,
    })


def live_train_status(request):

    train_number = request.GET.get('train_number', '')

    if not re.fullmatch(r'\d{5}', train_number):
        return JsonResponse({"error": "Invalid train number"}, status=400)

    try:
        headers = {"Authorization": f"Bearer {settings.RAILRADAR_API_KEY}"}
        response = requests.get(
            f"https://api.railradar.in/v1/trains/{train_number}/live",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return JsonResponse({"error": f"RailRadar returned status {response.status_code}"}, status=500)

        return JsonResponse(response.json())

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
def get_station_coordinates(request):
    station_name = request.GET.get('station', '')
    coords = STATION_COORDINATES.get(station_name)

    if not coords:
        return JsonResponse({"error": "Coordinates not available for this station"}, status=404)

    return JsonResponse(coords)
def get_train_eta(request):

    train_number = request.GET.get('train_number', '')

    if not re.fullmatch(r'\d{5}', train_number):
        return JsonResponse({"error": "Invalid train number"}, status=400)

    try:
        headers = {"Authorization": f"Bearer {settings.RAILRADAR_API_KEY}"}

        response = requests.get(
            f"https://api.railradar.in/v1/trains/{train_number}?haltsOnly=true",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return JsonResponse({"error": f"RailRadar returned status {response.status_code}"}, status=500)

        return JsonResponse(response.json())

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
