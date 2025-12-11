from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('rooms/', views.room_list_page, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail_page, name='room_detail'),
    path('my-bookings/', views.my_bookings_page, name='my_bookings'),
    path('owner/bookings/', views.owner_bookings_page, name='owner_bookings'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('api/rooms/', views.api_rooms, name='api_rooms'),
    path('api/rooms/<int:room_id>/', views.api_room_detail, name='api_room_detail'),
    path('api/bookings/add/', views.api_create_booking, name='api_create_booking'),
    path('api/bookings/my/', views.api_my_bookings, name='api_my_bookings'),
    path('api/bookings/received/', views.api_received_bookings, name='api_received_bookings'),
    path('api/bookings/approve/<int:booking_id>/', views.api_approve_booking, name='api_approve_booking'),
    path('api/bookings/reject/<int:booking_id>/', views.api_reject_booking, name='api_reject_booking'),
    path('api/user/', views.api_current_user, name='api_current_user'),
]
