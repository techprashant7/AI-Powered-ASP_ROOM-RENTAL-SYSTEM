from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .models import Room, Booking
from .serializers import RoomSerializer, BookingSerializer
import json

def home(request):
    return render(request, 'home.html')

def room_list_page(request):
    return render(request, 'rooms/room_list.html')

def room_detail_page(request, room_id):
    return render(request, 'rooms/room_detail.html', {'room_id': room_id})

@login_required
def my_bookings_page(request):
    return render(request, 'bookings/my_bookings.html')

@login_required
def owner_bookings_page(request):
    return render(request, 'bookings/owner_bookings.html')

def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('room_list')
        return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/login.html')

def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if User.objects.filter(username=username).exists():
            return render(request, 'auth/register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password,
                                         first_name=first_name, last_name=last_name)
        login(request, user)
        return redirect('room_list')
    return render(request, 'auth/register.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@api_view(['GET'])
def api_rooms(request):
    rooms = Room.objects.all().order_by('-created_at')
    serializer = RoomSerializer(rooms, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def api_room_detail(request, room_id):
    try:
        room = Room.objects.get(id=room_id)
        serializer = RoomSerializer(room, context={'request': request})
        return Response(serializer.data)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def api_create_booking(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    room_id = request.data.get('room_id')
    start_date_str = request.data.get('start_date')
    months = int(request.data.get('months', 1))
    
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if room.owner == request.user:
        return Response({'error': 'You cannot book your own room'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = start_date + relativedelta(months=months)
    total_rent = float(room.price) * months
    
    booking = Booking.objects.create(
        room=room,
        user=request.user,
        owner=room.owner,
        start_date=start_date,
        end_date=end_date,
        months=months,
        total_rent=total_rent
    )
    
    serializer = BookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def api_my_bookings(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def api_received_bookings(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    bookings = Booking.objects.filter(owner=request.user).order_by('-created_at')
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
def api_approve_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        booking = Booking.objects.get(id=booking_id, owner=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    booking.status = 'approved'
    booking.save()
    serializer = BookingSerializer(booking)
    return Response(serializer.data)

@api_view(['PUT'])
def api_reject_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        booking = Booking.objects.get(id=booking_id, owner=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    booking.status = 'rejected'
    booking.save()
    serializer = BookingSerializer(booking)
    return Response(serializer.data)

@api_view(['GET'])
def api_current_user(request):
    if request.user.is_authenticated:
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_authenticated': True
        })
    return Response({'is_authenticated': False})
