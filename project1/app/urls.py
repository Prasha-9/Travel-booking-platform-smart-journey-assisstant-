from django.urls import path
from . import views



urlpatterns = [

    # =========================
    # HOME
    # =========================

    path(
        '',
        views.home,
        name='home'
    ),


    # =========================
    # SIGNUP
    # =========================

    path(
        'signup/',
        views.signup,
        name='signup'
    ),


    # =========================
    # LOGIN
    # =========================

    path(
        'login/',
        views.login,
        name='login'
    ),


    # =========================
    # FORGOT PASSWORD
    # =========================

    path(
        'forgot-password/',
        views.forgot_password,
        name='forgot_password'
    ),


    # =========================
    # VERIFY OTP
    # =========================

    path(
        'verify-otp/',
        views.verify_otp,
        name='verify_otp'
    ),


    # =========================
    # RESET PASSWORD
    # =========================

    path(
        'reset-password/',
        views.reset_password,
        name='reset_password'
    ),


    # =========================
    # RESEND OTP
    # =========================

    path(
        'resend-otp/',
        views.resend_otp,
        name='resend_otp'
    ),


    # =========================
    # CUSTOMER DASHBOARD
    # =========================

    path(
        'customer-dashboard/',
        views.customer_dashboard,
        name='customer_dashboard'
    ),
    path(
    'profile/',
    views.profile,
    name='profile'
),
path(
    'chatbot/',
    views.chatbot,
    name='chatbot'
),
path('book-train/', views.book_train, name='book_train'),
path('search-stations/', views.search_stations, name='search_stations'),
path('search-trains/', views.search_trains, name='search_trains'),
path('booking-success/', views.booking_success, name='booking_success'),
path('nearby-places/', views.nearby_places, name='nearby_places'),
path('search-nearby/', views.search_nearby, name='search_nearby'),
path('upload-ticket/', views.upload_ticket, name='upload_ticket'),
path('confirm-ticket/', views.confirm_ticket, name='confirm_ticket'),
path('track-by-number/', views.track_by_train_number, name='track_by_train_number'),
path('live-tracking/', views.live_tracking, name='live_tracking'),
path('live-train-status/', views.live_train_status, name='live_train_status'),
path('station-coordinates/', views.get_station_coordinates, name='get_station_coordinates'),
path('train-eta/', views.get_train_eta, name='get_train_eta'),
    # =========================
    # PROVIDER DASHBOARD
    # =========================

    path(
        'provider-dashboard/',
        views.provider_dashboard,
        name='provider_dashboard'
    ),
    path(
    'provider-profile/',
    views.provider_profile,
    name='provider_profile'
),


# =========================
# ADMIN DASHBOARD
# =========================

path(
    'admin-dashboard/',
    views.admin_dashboard,
    name='admin_dashboard'
),

path(
    'manage/delete-user/<int:user_id>/',
    views.delete_user,
    name='delete_user'
),

path(
    'manage/delete-service/<int:service_id>/',
    views.delete_service,
    name='delete_service'
),

path(
    'manage/delete-booking/<int:booking_id>/',
    views.delete_booking,
    name='delete_booking'
),
path(
    'manage/update-user/<int:user_id>/',
    views.update_user,
    name='update_user'
),
]