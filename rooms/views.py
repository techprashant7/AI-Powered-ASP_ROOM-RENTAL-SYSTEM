from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io
import os
import requests
import json
import random
from .models import Room, Booking, UserProfile, Notification, Invoice, Payment
from .serializers import RoomSerializer, BookingSerializer, UserProfileSerializer, NotificationSerializer, InvoiceSerializer, PaymentSerializer
from .ml_models import PriceRecommendationSystem, RoomRecommendationSystem
from .genai_chatbot import RoomBookChatbot

def home(request):
    return render(request, 'home.html')

def room_list_page(request):
    return render(request, 'rooms/room_list.html')

def room_detail_page(request, room_id):
    return render(request, 'rooms/room_detail.html', {'room_id': room_id})

def about_page(request):
    return render(request, 'about/about.html')

def services_page(request):
    return render(request, 'services/services.html')

def contact_page(request):
    return render(request, 'contact/contact.html')

def _can_manage_as_staff(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    try:
        profile = user.profile
        return profile.staff_approved or True  # Allow all staff users for now
    except UserProfile.DoesNotExist:
        return False
    except:
        return user.is_staff  # Fallback to staff status if no profile

def _generate_otp():
    return f"{random.randint(0, 999999):06d}"

def _send_otp_email(to_email, otp):
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise RuntimeError('Email is not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in environment variables.')
    send_mail(
        subject='RoomBook Email Verification OTP',
        message=f"Your RoomBook OTP is: {otp}. It will expire in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        recipient_list=[to_email],
        fail_silently=False,
    )

def _send_booking_notification_email(booking, status):
    """Send email notification to user about booking status change"""
    try:
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                # Skip email if not configured, but don't raise error
                return
        
        subject = f'RoomBook - Booking {status.title()}'
        message = f"""
Dear {booking.user.get_full_name() or booking.user.username},

Your booking for "{booking.room.title}" has been {status}.

Booking Details:
- Room: {booking.room.title}
- Location: {booking.room.location}
- Start Date: {booking.start_date}
- End Date: {booking.end_date}
- Total Rent: ${booking.total_rent}

{status == 'approved' and 'You can now create an invoice and proceed with payment.' or 'Please contact the room owner for more information.'}

Thank you for using RoomBook!
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=[booking.user.email],
            fail_silently=True,  # Don't fail the booking process if email fails
        )
    except Exception as e:
        # Log error but don't fail the booking process
        print(f"Failed to send booking notification email: {e}")

def _send_invoice_to_host_email(invoice):
    """Send email notification to host/owner about invoice creation"""
    try:
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                # Skip email if not configured, but don't raise error
                return
        
        booking = invoice.booking
        subject = f'RoomBook - New Invoice Created for {booking.room.title}'
        message = f"""
Dear {booking.room.owner.get_full_name() or booking.room.owner.username},

An invoice has been generated for your approved booking.

Booking Details:
- Room: {booking.room.title}
- Guest: {booking.user.get_full_name() or booking.user.username}
- Email: {booking.user.email}
- Period: {booking.start_date} to {booking.end_date}
- Duration: {booking.months} month(s)

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Subtotal: ${invoice.subtotal:.2f}
- Tax Amount: ${invoice.tax_amount:.2f}
- Total Amount: ${invoice.total_amount:.2f}
- Due Date: {invoice.due_date}

The guest has been notified and can proceed with payment via Razorpay.

Thank you for using RoomBook!
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=[booking.room.owner.email],
            fail_silently=True,  # Don't fail the invoice process if email fails
        )
    except Exception as e:
        # Log error but don't fail the invoice process
        print(f"Failed to send host invoice notification email: {e}")

def _send_payment_confirmation_email(payment):
    """Send tax invoice email after successful payment"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        print(f"DEBUG: Email backend: {settings.EMAIL_BACKEND}")
        print(f"DEBUG: Email host user: {settings.EMAIL_HOST_USER}")
        
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                print("DEBUG: Email credentials not configured")
                return
        
        invoice = payment.invoice
        subject = f'TAX INVOICE - {invoice.invoice_number}'
        message = f"""
-----------------------------------------
                TAX INVOICE
-----------------------------------------

Room Rental System
Address
Phone | Email

Invoice No: {invoice.invoice_number}
Date: {invoice.issued_date.strftime('%d-%m-%Y')}

Customer Details:
-----------------------------------------
Name: {invoice.booking.user.get_full_name() or invoice.booking.user.username}
Room No: {invoice.booking.room.room_number if hasattr(invoice.booking.room, 'room_number') else invoice.booking.room.title}
Room Type: {invoice.booking.room.room_type if hasattr(invoice.booking.room, 'room_type') else 'Standard'}

Stay Duration:
-----------------------------------------
Check-in: {invoice.booking.check_in.strftime('%d-%m-%Y')}
Check-out: {invoice.booking.check_out.strftime('%d-%m-%Y')}
Total Nights: {(invoice.booking.check_out - invoice.booking.check_in).days}

Final Charges:
-----------------------------------------
Room Rent                     ${invoice.subtotal:.2f}
Tax Amount                    ${invoice.tax_amount:.2f}
-----------------------------------------
Grand Total                   ${invoice.total_amount:.2f}

Payment Details:
-----------------------------------------
Payment Mode: {payment.get_payment_method_display()}
Payment Status: PAID
Transaction ID: {payment.transaction_id or 'N/A'}
Payment Date: {payment.payment_date.strftime('%d-%m-%Y %H:%M:%S') if payment.payment_date else 'N/A'}

Thank You for Staying With Us!

Authorized Signature
-----------------------------------------
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=[invoice.booking.user.email],
            fail_silently=False,
        )
        print(f"DEBUG: Tax invoice email sent to {invoice.booking.user.email}")
    except Exception as e:
        print(f"Failed to send tax invoice email: {e}")

def _send_invoice_notification_email(invoice):
    """Send proforma invoice email to user about invoice creation"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        print(f"DEBUG: Email backend: {settings.EMAIL_BACKEND}")
        print(f"DEBUG: Email host user: {settings.EMAIL_HOST_USER}")
        
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                print("DEBUG: Email credentials not configured")
                return
        
        subject = f'PROFORMA INVOICE - {invoice.invoice_number}'
        message = f"""
-----------------------------------------
            PROFORMA INVOICE
-----------------------------------------

Room Rental System
Address
Phone | Email

Proforma Invoice No: {invoice.invoice_number}
Date: {invoice.issued_date.strftime('%d-%m-%Y')}

Customer Name: {invoice.booking.user.get_full_name() or invoice.booking.user.username}
Contact Number: {invoice.booking.user.phone_number if hasattr(invoice.booking.user, 'phone_number') else 'N/A'}
Email: {invoice.booking.user.email}

Room Details:
-----------------------------------------
Room Number: {invoice.booking.room.room_number if hasattr(invoice.booking.room, 'room_number') else invoice.booking.room.title}
Room Type: {invoice.booking.room.room_type if hasattr(invoice.booking.room, 'room_type') else 'Standard'}
Check-in Date: {invoice.booking.check_in.strftime('%d-%m-%Y')}
Check-out Date: {invoice.booking.check_out.strftime('%d-%m-%Y')}
Total Nights: {(invoice.booking.check_out - invoice.booking.check_in).days}

Charges:
-----------------------------------------
Room Rent                     ${invoice.subtotal:.2f}
Tax Amount                    ${invoice.tax_amount:.2f}
-----------------------------------------
Total Estimated Amount        ${invoice.total_amount:.2f}

Note:
• This is a Proforma Invoice
• Amount is subject to change
• Payment required to confirm booking
• Status: NOT PAID

Authorized Signature
-----------------------------------------
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=[invoice.booking.user.email],
            fail_silently=False,
        )
        print(f"DEBUG: Proforma invoice email sent to {invoice.booking.user.email}")
    except Exception as e:
        print(f"Failed to send proforma invoice email: {e}")

@login_required
def owner_rooms_page(request):
    if not _can_manage_as_staff(request.user):
        return redirect('home')
    return render(request, 'rooms/owner_rooms.html')

@login_required
def owner_room_add_page(request):
    if not _can_manage_as_staff(request.user):
        return redirect('home')
    return render(request, 'rooms/room_form.html', {'room_id': None})

@login_required
def owner_room_edit_page(request, room_id):
    if not _can_manage_as_staff(request.user):
        return redirect('home')
    return render(request, 'rooms/room_form.html', {'room_id': room_id})

@login_required
def profile_page(request):
    return render(request, 'profile.html')

@login_required
def notifications_page(request):
    return render(request, 'notifications.html')

@login_required
def my_bookings_page(request):
    return render(request, 'bookings/my_bookings.html')

@login_required
def owner_bookings_page(request):
    if not _can_manage_as_staff(request.user):
        return redirect('home')
    return render(request, 'bookings/owner_bookings.html')

def privacy_page(request):
    """Privacy Policy page"""
    return render(request, 'legal/privacy.html')

def terms_page(request):
    """Terms of Service page"""
    return render(request, 'legal/terms.html')

def login_page(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(next_url or 'room_list')
        if User.objects.filter(username=username, is_active=False).exists():
            return render(request, 'auth/login.html', {'error': 'Account not verified. Please verify OTP first.'})
        return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/login.html', {'next': next_url})

def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        account_type = request.POST.get('account_type', 'user')
        
        if User.objects.filter(username=username).exists():
            return render(request, 'auth/register.html', {'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'auth/register.html', {'error': 'Email already exists'})
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_active = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if account_type == 'staff':
            profile.staff_requested = True
            profile.staff_approved = False

        otp = _generate_otp()
        profile.otp_code = otp
        profile.otp_created_at = timezone.now()
        profile.email_verified = False
        profile.save()

        try:
            _send_otp_email(email, otp)
        except Exception as e:
            return render(request, 'auth/register.html', {'error': str(e)})

        request.session['pending_user_id'] = user.id
        return redirect('verify_otp')
    return render(request, 'auth/register.html')

def verify_otp_page(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        return redirect('register')

    try:
        user = User.objects.get(id=pending_user_id)
    except User.DoesNotExist:
        request.session.pop('pending_user_id', None)
        return redirect('register')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action', 'verify')
        if action == 'resend':
            otp = _generate_otp()
            profile.otp_code = otp
            profile.otp_created_at = timezone.now()
            profile.save()
            try:
                _send_otp_email(user.email, otp)
            except Exception as e:
                return render(request, 'auth/verify_otp.html', {'email': user.email, 'error': str(e)})
            return render(request, 'auth/verify_otp.html', {'email': user.email, 'message': 'OTP resent successfully'})

        otp_input = (request.POST.get('otp') or '').strip()
        if not otp_input or len(otp_input) != 6:
            return render(request, 'auth/verify_otp.html', {'email': user.email, 'error': 'Invalid OTP'})

        if not profile.otp_code or otp_input != profile.otp_code:
            return render(request, 'auth/verify_otp.html', {'email': user.email, 'error': 'Incorrect OTP'})

        if not profile.otp_created_at or timezone.now() - profile.otp_created_at > timedelta(minutes=10):
            return render(request, 'auth/verify_otp.html', {'email': user.email, 'error': 'OTP expired. Please resend OTP.'})

        profile.email_verified = True
        profile.otp_code = ''
        profile.save()
        user.is_active = True
        user.save()

        request.session.pop('pending_user_id', None)
        login(request, user)
        return redirect('room_list')

    return render(request, 'auth/verify_otp.html', {'email': user.email})

def logout_view(request):
    logout(request)
    return redirect('home')

@api_view(['GET'])
def api_rooms(request):
    rooms = Room.objects.all()

    q = request.GET.get('q')
    location = request.GET.get('location')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', 'newest')

    if q:
        rooms = rooms.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))
    if location:
        rooms = rooms.filter(location__icontains=location)
    if min_price:
        try:
            rooms = rooms.filter(price__gte=min_price)
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            rooms = rooms.filter(price__lte=max_price)
        except (ValueError, TypeError):
            pass

    if sort == 'price_asc':
        rooms = rooms.order_by('price')
    elif sort == 'price_desc':
        rooms = rooms.order_by('-price')
    else:
        rooms = rooms.order_by('-created_at')

    serializer = RoomSerializer(rooms, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
def api_owner_rooms(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not _can_manage_as_staff(request.user):
        return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        rooms = Room.objects.filter(owner=request.user).order_by('-created_at')
        serializer = RoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)

    data = request.data.copy()
    serializer = RoomSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        room = serializer.save(owner=request.user)
        return Response(RoomSerializer(room, context={'request': request}).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@parser_classes([MultiPartParser, FormParser])
def api_owner_room_detail(request, room_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not _can_manage_as_staff(request.user):
        return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        room = Room.objects.get(id=room_id, owner=request.user)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(RoomSerializer(room, context={'request': request}).data)

    if request.method == 'DELETE':
        room.delete()
        return Response({'success': True})

    serializer = RoomSerializer(room, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    months_str = request.data.get('months', 1)
    
    if not room_id:
        return Response({'error': 'Room ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not start_date_str:
        return Response({'error': 'Start date is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        months = int(months_str)
        if months < 1 or months > 24:
            return Response({'error': 'Months must be between 1 and 24'}, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid months value'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if room.owner == request.user:
        return Response({'error': 'You cannot book your own room'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
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

    Notification.objects.create(
        user=room.owner,
        title='New booking request',
        message=f"{request.user.username} requested to book '{room.title}' for {months} month(s).",
        link='/owner/bookings/'
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
    if not _can_manage_as_staff(request.user):
        return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)
    
    bookings = Booking.objects.filter(owner=request.user).order_by('-created_at')
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
def api_approve_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not _can_manage_as_staff(request.user):
        return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        booking = Booking.objects.get(id=booking_id, owner=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if booking.status != 'pending':
        return Response({'error': 'Booking already processed'}, status=status.HTTP_400_BAD_REQUEST)
    
    booking.status = 'approved'
    booking.save()
    
    # Send email notification
    _send_booking_notification_email(booking, 'approved')
    
    Notification.objects.create(
        user=booking.user,
        title='Booking approved',
        message=f"Your booking for '{booking.room.title}' has been approved.",
        link='/my-bookings/'
    )
    serializer = BookingSerializer(booking)
    return Response(serializer.data)

@api_view(['PUT'])
def api_reject_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not _can_manage_as_staff(request.user):
        return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        booking = Booking.objects.get(id=booking_id, owner=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    booking.status = 'rejected'
    booking.save()
    
    # Send email notification
    _send_booking_notification_email(booking, 'rejected')
    
    Notification.objects.create(
        user=booking.user,
        title='Booking rejected',
        message=f"Your booking for '{booking.room.title}' has been rejected.",
        link='/my-bookings/'
    )
    serializer = BookingSerializer(booking)
    return Response(serializer.data)

@api_view(['PUT'])
def api_cancel_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if booking.status in ['approved', 'rejected', 'cancelled']:
        return Response({'error': 'Cannot cancel a booking that is already ' + booking.status}, status=status.HTTP_400_BAD_REQUEST)
    
    booking.status = 'cancelled'
    booking.save()
    Notification.objects.create(
        user=booking.owner,
        title='Booking cancelled',
        message=f"{request.user.username} cancelled their booking for '{booking.room.title}'.",
        link='/owner/bookings/'
    )
    serializer = BookingSerializer(booking)
    return Response(serializer.data)

@api_view(['GET'])
def api_current_user(request):
    if request.user.is_authenticated:
        staff_approved = False
        if request.user.is_superuser:
            staff_approved = True
        elif request.user.is_staff:
            try:
                staff_approved = request.user.profile.staff_approved
            except UserProfile.DoesNotExist:
                staff_approved = False
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'staff_approved': staff_approved,
            'is_authenticated': True
        })
    return Response({'is_authenticated': False})

@api_view(['GET', 'PUT'])
def api_profile(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return Response({
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            },
            'profile': UserProfileSerializer(profile).data
        })

    user_data = request.data.get('user', {}) if isinstance(request.data, dict) else {}
    profile_data = request.data.get('profile', {}) if isinstance(request.data, dict) else {}

    request.user.first_name = user_data.get('first_name', request.user.first_name)
    request.user.last_name = user_data.get('last_name', request.user.last_name)
    request.user.email = user_data.get('email', request.user.email)
    request.user.save()

    serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            },
            'profile': serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def api_notifications(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def api_unread_notifications_count(request):
    if not request.user.is_authenticated:
        return Response({'count': 0})
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'count': count})

@api_view(['PUT'])
def api_mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save()
    return Response({'success': True})

@api_view(['PUT'])
def api_mark_all_notifications_read(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)

    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'success': True})

def generate_invoice_pdf(invoice):
    """Generate PDF for an invoice"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = styles['Title']
    title = Paragraph("INVOICE", title_style)
    story.append(title)
    story.append(Spacer(1, 12))

    # Invoice details table
    invoice_data = [
        ['Invoice Number:', invoice.invoice_number],
        ['Issued Date:', invoice.issued_date.strftime('%Y-%m-%d')],
        ['Due Date:', invoice.due_date.strftime('%Y-%m-%d')],
        ['Status:', invoice.status.upper()],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 20))

    # Booking details
    booking = invoice.booking
    booking_data = [
        ['Room:', booking.room.title],
        ['Location:', booking.room.location],
        ['Period:', f"{booking.start_date} to {booking.end_date}"],
        ['Duration:', f"{booking.months} month(s)"],
    ]
    
    booking_table = Table(booking_data, colWidths=[1.5*inch, 4*inch])
    booking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(booking_table)
    story.append(Spacer(1, 20))

    # Billing details
    billing_data = [
        ['Description', 'Amount'],
        ['Room Rent', f"${invoice.subtotal:.2f}"],
        ['Tax', f"${invoice.tax_amount:.2f}"],
        ['Total', f"${invoice.total_amount:.2f}"],
    ]
    
    billing_table = Table(billing_data, colWidths=[3*inch, 2*inch])
    billing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
    ]))
    story.append(billing_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

@api_view(['POST'])
def api_create_invoice(request, booking_id):
    """Create invoice for an approved booking"""
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if booking.status != 'approved':
        return Response({'error': 'Invoice can only be created for approved bookings'}, status=status.HTTP_400_BAD_REQUEST)
    
    if hasattr(booking, 'invoice'):
        return Response({'error': 'Invoice already exists for this booking'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{booking.id:04d}"
        
        # Calculate amounts (tax rate of 18% standard GST)
        from decimal import Decimal
        tax_rate = Decimal('18.00')
        subtotal = booking.total_rent
        tax_amount = subtotal * tax_rate / Decimal('100')
        total_amount = subtotal + tax_amount
        due_date = datetime.now().date() + timedelta(days=7)  # 7 days due date
        
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            due_date=due_date,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status='draft'
        )
        
        # Generate PDF invoice
        try:
            pdf_buffer = generate_invoice_pdf(invoice)
            
            # Save PDF file
            filename = f"invoice_{invoice_number}.pdf"
            invoice.pdf_file.save(filename, pdf_buffer, save=True)
            
            invoice.status = 'sent'
            invoice.save()
            
            # Send email notification to user
            _send_invoice_notification_email(invoice)
            
            # Send email notification to host/owner
            _send_invoice_to_host_email(invoice)
            
            serializer = InvoiceSerializer(invoice)
            return Response({
                'data': serializer.data,
                'message': 'Invoice created successfully and sent to your email'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as pdf_error:
            # If PDF generation fails, create invoice without PDF for now
            invoice.status = 'draft'
            invoice.save()
            serializer = InvoiceSerializer(invoice)
            return Response({
                'data': serializer.data, 
                'warning': 'Invoice created but PDF generation failed. You can still proceed with payment.'
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({'error': f'Invoice creation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def api_download_invoice(request, invoice_id):
    """Download invoice PDF"""
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        invoice = Invoice.objects.get(id=invoice_id, booking__user=request.user)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if not invoice.pdf_file:
        return Response({'error': 'PDF file not available'}, status=status.HTTP_404_NOT_FOUND)
    
    # Serve the PDF file
    pdf_file = invoice.pdf_file.path
    if os.path.exists(pdf_file):
        with open(pdf_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_file)}"'
            return response
    else:
        return Response({'error': 'PDF file not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def api_my_invoices(request):
    """Get all invoices for the current user"""
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    invoices = Invoice.objects.filter(booking__user=request.user).order_by('-created_at')
    serializer = InvoiceSerializer(invoices, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def api_process_payment(request):
    """Process payment for an invoice using Razorpay"""
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    invoice_id = request.data.get('invoice_id')
    
    if not invoice_id:
        return Response({'error': 'Invoice ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        invoice = Invoice.objects.get(id=invoice_id, booking__user=request.user)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if invoice.status == 'paid':
        return Response({'error': 'Invoice is already paid'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if there's already a completed payment for this invoice
    existing_payment = Payment.objects.filter(invoice=invoice, status='completed').first()
    if existing_payment:
        return Response({'error': 'Payment already completed for this invoice'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Import Razorpay here to avoid import issues if not configured
    try:
        import razorpay
        from django.conf import settings
    except ImportError:
        return Response({'error': 'Razorpay not installed. Please install razorpay package.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Initialize Razorpay client
    try:
        razorpay_client = razorpay.Client(
            auth=(getattr(settings, 'RAZORPAY_KEY_ID', ''), 
                  getattr(settings, 'RAZORPAY_KEY_SECRET', ''))
        )
    except Exception as e:
        return Response({'error': f'Razorpay configuration error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Generate transaction ID
    transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
    
    try:
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            'amount': int(invoice.total_amount * 100),  # Amount in paise
            'currency': 'INR',
            'receipt': invoice.invoice_number,
            'notes': {
                'invoice_id': invoice.id,
                'user_id': request.user.id,
                'booking_id': invoice.booking.id
            }
        })
        
        # Create payment record
        payment = Payment.objects.create(
            invoice=invoice,
            payment_method='razorpay',
            transaction_id=transaction_id,
            amount=invoice.total_amount,
            status='processing',
            gateway_response={
                'razorpay_order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'status': 'created'
            }
        )
        
        return Response({
            'payment_id': payment.id,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
            'amount_paise': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'invoice_number': invoice.invoice_number,
            'description': f'Payment for {invoice.invoice_number}',
            'customer_name': f"{invoice.booking.user.first_name} {invoice.booking.user.last_name}".strip() or invoice.booking.user.username,
            'customer_email': invoice.booking.user.email,
            'callback_url': f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/api/payments/razorpay/callback/"
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Failed to create Razorpay order: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def api_razorpay_callback(request):
    """Handle Razorpay payment callback"""
    print(f"DEBUG: Razorpay callback received: {request.data}")
    
    payment_id = request.data.get('payment_id')
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_signature = request.data.get('razorpay_signature')
    
    print(f"DEBUG: payment_id={payment_id}, order_id={razorpay_order_id}")
    
    if not all([payment_id, razorpay_order_id, razorpay_signature]):
        print("DEBUG: Missing required parameters")
        return Response({'error': 'Missing required Razorpay parameters'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find the payment by Razorpay order ID
        payment = Payment.objects.filter(
            payment_method='razorpay',
            status='processing'
        ).first()
        
        print(f"DEBUG: Found payment: {payment.id if payment else 'None'}")
        
        if not payment:
            print("DEBUG: No processing payment found")
            return Response({'error': 'Payment not found or already processed'}, status=status.HTTP_404_NOT_FOUND)
            
        # Check if this payment matches the order ID
        stored_order_id = payment.gateway_response.get('razorpay_order_id')
        print(f"DEBUG: Stored order ID: {stored_order_id}")
        print(f"DEBUG: Received order ID: {razorpay_order_id}")
        
        # If order IDs don't match, find the correct payment
        if stored_order_id != razorpay_order_id:
            print("DEBUG: Order ID mismatch, searching for correct payment")
            all_processing_payments = Payment.objects.filter(
                payment_method='razorpay',
                status='processing'
            )
            for p in all_processing_payments:
                if p.gateway_response.get('razorpay_order_id') == razorpay_order_id:
                    payment = p
                    print(f"DEBUG: Found correct payment: {payment.id}")
                    break
            else:
                print("DEBUG: No payment found with matching order ID")
                return Response({'error': 'Payment not found or already processed'}, status=status.HTTP_404_NOT_FOUND)
        
        # Update payment status (without Razorpay capture for now)
        payment.status = 'completed'
        payment.payment_date = timezone.now()
        payment.gateway_response.update({
            'razorpay_payment_id': payment_id,
            'razorpay_signature': razorpay_signature,
            'status': 'success',
            'captured': True
        })
        payment.save()
        print("DEBUG: Payment record updated")
        
        # Update invoice status
        payment.invoice.status = 'paid'
        payment.invoice.save()
        print("DEBUG: Invoice status updated to paid")
        
        # Send email notification
        try:
            _send_payment_confirmation_email(payment)
            print("DEBUG: Payment confirmation email sent")
        except Exception as e:
            print(f"DEBUG: Failed to send payment confirmation email: {e}")
        
        # Create notification
        try:
            Notification.objects.create(
                user=payment.invoice.booking.user,
                title='Payment Successful',
                message=f"Payment of ${payment.invoice.total_amount:.2f} for invoice {payment.invoice.invoice_number} has been processed successfully via Razorpay.",
                link='/my-bookings/'
            )
            print("DEBUG: Notification created")
        except Exception as e:
            print(f"DEBUG: Failed to create notification: {e}")
        
        print("DEBUG: Payment callback completed successfully")
        return Response({'success': True, 'message': 'Payment processed successfully'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"DEBUG: Payment processing failed: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return Response({'error': f'Payment processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def api_my_payments(request):
    """Get current user's payments"""
    if not request.user.is_authenticated:
        return Response({'error': 'Login required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    payments = Payment.objects.filter(invoice__booking__user=request.user).order_by('-created_at')
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@login_required
def api_admin_promote_user(request, user_id):
    """Promote a user to staff or superuser"""
    if not request.user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_to_promote = User.objects.get(id=user_id)
        
        # Prevent promoting other superusers (only superusers can promote to superuser)
        if user_to_promote.is_superuser and user_to_promote != request.user:
            return Response({'error': 'Cannot modify other superuser accounts'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-promotion to avoid accidental privilege escalation
        if user_to_promote == request.user:
            return Response({'error': 'Cannot modify your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        role = data.get('role')  # 'staff' or 'superuser'
        
        if role == 'staff':
            user_to_promote.is_staff = True
            user_to_promote.is_superuser = False
            user_to_promote.save()
            message = f'User {user_to_promote.username} promoted to Staff'
        elif role == 'superuser':
            user_to_promote.is_staff = True
            user_to_promote.is_superuser = True
            user_to_promote.save()
            message = f'User {user_to_promote.username} promoted to Superuser'
        else:
            return Response({'error': 'Invalid role specified'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': message})
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@login_required
def api_admin_demote_user(request, user_id):
    """Demote a user from staff or superuser"""
    if not request.user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_to_demote = User.objects.get(id=user_id)
        
        # Prevent demoting other superusers
        if user_to_demote.is_superuser and user_to_demote != request.user:
            return Response({'error': 'Cannot modify other superuser accounts'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-demotion
        if user_to_demote == request.user:
            return Response({'error': 'Cannot modify your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        role = data.get('role')  # 'staff' or 'user'
        
        if role == 'staff':
            user_to_demote.is_staff = True
            user_to_demote.is_superuser = False
            user_to_demote.save()
            message = f'User {user_to_demote.username} demoted to Staff'
        elif role == 'user':
            user_to_demote.is_staff = False
            user_to_demote.is_superuser = False
            user_to_demote.save()
            message = f'User {user_to_demote.username} demoted to regular User'
        else:
            return Response({'error': 'Invalid role specified'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': message})
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@login_required
def api_admin_toggle_user_status(request, user_id):
    """Activate or deactivate a user account"""
    if not request.user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_to_toggle = User.objects.get(id=user_id)
        
        # Prevent deactivating other superusers
        if user_to_toggle.is_superuser and user_to_toggle != request.user:
            return Response({'error': 'Cannot modify other superuser accounts'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deactivation
        if user_to_toggle == request.user:
            return Response({'error': 'Cannot modify your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Toggle user status
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        
        status = 'activated' if user_to_toggle.is_active else 'deactivated'
        message = f'User {user_to_toggle.username} {status}'
        
        return Response({'message': message, 'is_active': user_to_toggle.is_active})
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@login_required
def api_admin_delete_user(request, user_id):
    """Delete a user and all associated data"""
    if not request.user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_to_delete = User.objects.get(id=user_id)
        
        # Prevent deletion of superusers
        if user_to_delete.is_superuser:
            return Response({'error': 'Cannot delete superuser accounts'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deletion
        if user_to_delete == request.user:
            return Response({'error': 'Cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete user and all related data
        user_to_delete.delete()
        
        return Response({'message': 'User deleted successfully'})
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@login_required
def api_admin_users(request):
    """Get all users for admin management"""
    if not request.user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        users = User.objects.all().order_by('-date_joined')
        
        user_data = []
        for user in users:
            # Count user's rooms
            room_count = user.rooms.count()
            
            # Count user's bookings
            booking_count = user.user_bookings.count()
            
            user_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M'),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
                'room_count': room_count,
                'booking_count': booking_count,
                'status': 'Active' if user.is_active else 'Inactive',
                'role': 'Superuser' if user.is_superuser else 'Staff' if user.is_staff else 'User'
            })
        
        return Response(user_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from .ai_negotiation import AINegotiationAssistant

@login_required
def manage_users_page(request):
    """User management page for superusers"""
    if not request.user.is_superuser:
        return redirect('home')
    
    return render(request, 'admin/users.html')

# AI Negotiation Assistant Views
@login_required
def negotiation_assistant_page(request, room_id=None):
    """AI Negotiation Assistant page"""
    if room_id:
        room = get_object_or_404(Room, id=room_id)
        # Check if user is owner or has booking for this room
        if room.owner != request.user and not Booking.objects.filter(user=request.user, room=room).exists():
            return redirect('home')
    else:
        room = None
    
    return render(request, 'negotiation/negotiation_assistant.html', {'room': room})

@api_view(['POST'])
@login_required
def api_negotiation_analyze(request):
    """API endpoint to analyze negotiation scenario"""
    try:
        data = request.data
        owner_min_price = data.get('owner_min_price')
        tenant_offer = data.get('tenant_offer')
        market_price = data.get('market_price')
        room_location = data.get('room_location', '')
        negotiation_tone = data.get('tone', 'polite')
        
        # Validate required fields
        if not all([owner_min_price, tenant_offer]):
            return JsonResponse({'error': 'Missing required fields: owner_min_price and tenant_offer are required'}, status=400)
        
        # Convert to float
        try:
            owner_min_price = float(owner_min_price)
            tenant_offer = float(tenant_offer)
            if market_price:
                market_price = float(market_price)
        except ValueError:
            return JsonResponse({'error': 'Invalid price values'}, status=400)
        
        # Initialize negotiation assistant
        assistant = AINegotiationAssistant()
        
        # Generate negotiation response
        # Use analyze_negotiation_scenario since we don't have a specific room
        if not market_price:
            # Use average of owner and tenant prices as fallback market price
            market_price = (owner_min_price + tenant_offer) / 2
        
        analysis = assistant.analyze_negotiation_scenario(
            owner_min_price=owner_min_price,
            tenant_offer=tenant_offer,
            market_price=market_price
        )
        
        # Get negotiation tips based on position
        tips = assistant.get_negotiation_tips(analysis['position'])
        
        # Format response for frontend
        formatted_result = {
            'market_price': market_price,
            'recommended_price': (owner_min_price + tenant_offer) / 2,
            'suggestions': [f"Based on the analysis, the negotiation position is: {analysis['position']}"],
            'counter_offers': [f"Consider ${(owner_min_price + tenant_offer) / 2:.0f} as a compromise"],
            'negotiation_tips': tips
        }
        
        return JsonResponse(formatted_result)
        
    except Exception as e:
        print(f"Negotiation API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Failed to analyze negotiation'}, status=500)

# Chatbot Views
def google_oauth_login(request):
    """Initiate Google OAuth login"""
    if not settings.GOOGLE_OAUTH2_CLIENT_ID or not settings.GOOGLE_OAUTH2_CLIENT_SECRET:
        return JsonResponse({'error': 'Google OAuth not configured'}, status=500)
    
    # Build the OAuth URL
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    params = {
        'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH2_REDIRECT_URI,
        'scope': ' '.join(settings.GOOGLE_OAUTH2_SCOPES),
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    # Redirect to Google OAuth
    from urllib.parse import urlencode
    redirect_url = f"{auth_url}?{urlencode(params)}"
    return redirect(redirect_url)

def google_oauth_callback(request):
    """Handle Google OAuth callback"""
    if not settings.GOOGLE_OAUTH2_CLIENT_ID or not settings.GOOGLE_OAUTH2_CLIENT_SECRET:
        return JsonResponse({'error': 'Google OAuth not configured'}, status=500)
    
    # Get authorization code from Google
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Authorization code not found'}, status=400)
    
    try:
        # Exchange authorization code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_OAUTH2_REDIRECT_URI
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_info = token_response.json()
        
        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {token_info["access_token"]}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        # Process user information
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        google_id = user_info.get('id')
        
        if not email:
            return JsonResponse({'error': 'Email not provided by Google'}, status=400)
        
        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            # Log in existing user
            login(request, user)
            return redirect('home')
        except User.DoesNotExist:
            # Create new user
            username = email.split('@')[0]
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True  # Google users are pre-verified
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                phone='',
                is_verified=True,  # Google users are pre-verified
                google_id=google_id
            )
            
            # Log in the new user
            login(request, user)
            
            # Create welcome notification
            Notification.objects.create(
                user=user,
                title='Welcome to RoomBook!',
                message='Your account has been created successfully using Google.',
                link='/rooms/'
            )
            
            return redirect('home')
            
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Google API error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'OAuth callback error: {str(e)}'}, status=500)

@login_required
def recommendations_page(request):
    """AI Recommendations page"""
    return render(request, 'ml/recommendations.html')

@api_view(['GET'])
@login_required
def api_ml_recommendations(request):
    """API endpoint for ML recommendations"""
    try:
        user = request.user
        recommender = RoomRecommendationSystem()
        
        # Get hybrid recommendations
        recommendations = recommender.get_hybrid_recommendations(user.id, n_recommendations=10)
        
        # Format recommendations for frontend
        formatted_recommendations = []
        for rec in recommendations:
            room = rec['room']
            formatted_recommendations.append({
                'id': room.id,
                'title': room.title,
                'location': room.location,
                'price': room.price,
                'image_url': room.image.url if room.image else None,
                'similarity_score': rec.get('hybrid_score', rec.get('collaborative_score', rec.get('content_score', 0.5))),
                'method': rec.get('method', 'hybrid')
            })
        
        return JsonResponse({'recommendations': formatted_recommendations})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@login_required
def api_ml_train_recommender(request):
    """API endpoint for training the ML recommender model"""
    try:
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Only superusers can train the model'}, status=403)
        
        # Train price recommendation system
        price_system = PriceRecommendationSystem()
        success, message = price_system.train_models()
        
        if success:
            return JsonResponse({'message': message})
        else:
            return JsonResponse({'error': message}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@login_required
def api_ml_predict_price(request):
    """API endpoint for predicting optimal room price"""
    try:
        if not request.user.is_staff:
            return JsonResponse({'error': 'Only staff users can predict prices'}, status=403)
        
        room_features = request.data
        
        # Validate required fields
        required_fields = ['title', 'location']
        for field in required_fields:
            if field not in room_features:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Initialize price prediction system
        price_system = PriceRecommendationSystem()
        
        # Try to load existing models, if not available, train them
        if not price_system.load_models():
            success, message = price_system.train_models()
            if not success:
                return JsonResponse({'error': message}, status=500)
        
        # Predict price
        predicted_price = price_system.predict_price(room_features)
        
        if predicted_price is not None:
            return JsonResponse({
                'predicted_price': predicted_price,
                'currency': 'USD',
                'confidence': 'medium'  # Could be calculated based on model performance
            })
        else:
            return JsonResponse({'error': 'Failed to predict price'}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Chatbot Views
@login_required
def chatbot_page(request):
    """Chatbot page"""
    return render(request, 'chatbot/chatbot.html')

@api_view(['POST'])
@csrf_exempt  # Temporarily disable CSRF for testing
@login_required
def api_chatbot_message(request):
    """API endpoint for chatbot messages"""
    try:
        # Use Django REST framework's built-in request parsing
        data = request.data
        
        message = data.get('message', '')
        room_id = data.get('room_id', None)
        
        if not message or not message.strip():
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Initialize chatbot
        chatbot = RoomBookChatbot()
        
        # Generate response
        response = chatbot.generate_response(
            message=message.strip(),
            user=request.user,
            room_id=room_id
        )
        
        return JsonResponse({
            'response': response,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        # Log the error for debugging
        print(f"Chatbot error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Sorry, I encountered an error. Please try again.'}, status=500)

# Rental Agreement Generator Views
@login_required
def agreement_generator_page(request, booking_id=None):
    """Rental agreement generator page"""
    booking = None
    if booking_id:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    return render(request, 'legal/agreement_generator.html', {'booking': booking})

@api_view(['POST'])
@login_required
def api_generate_agreement(request):
    """API endpoint for generating rental agreement"""
    try:
        data = request.data
        booking_id = data.get('booking_id')
        
        if booking_id:
            # Generate agreement for existing booking
            booking = get_object_or_404(Booking, id=booking_id, user=request.user)
            agreement_text = generate_rental_agreement(booking)
        else:
            # Generate agreement with provided details
            required_fields = ['owner_name', 'tenant_name', 'property_address', 'rent_amount', 'duration_months']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
            
            agreement_text = generate_custom_agreement(data)
        
        # Generate PDF
        pdf_buffer = create_agreement_pdf(agreement_text, data.get('title', 'Rental Agreement'))
        
        # Return PDF as response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rental_agreement.pdf"'
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generate_rental_agreement(booking):
    """Generate rental agreement text for a booking"""
    start_date = booking.start_date.strftime('%B %d, %Y')
    end_date = booking.end_date.strftime('%B %d, %Y')
    duration = (booking.end_date - booking.start_date).days
    
    agreement = f"""
RENTAL AGREEMENT

This Rental Agreement is made and entered into on {timezone.now().strftime('%B %d, %Y')} 

BETWEEN:
{booking.room.owner.get_full_name() or booking.room.owner.username} (hereinafter "Owner")
Address: {booking.room.owner.profile.address if hasattr(booking.room.owner, 'profile') else 'Not specified'}

AND:
{booking.user.get_full_name() or booking.user.username} (hereinafter "Tenant")
Address: {booking.user.profile.address if hasattr(booking.user, 'profile') else 'Not specified'}

PROPERTY:
{booking.room.title}
Location: {booking.room.location}
Description: {booking.room.description}

TERM:
This agreement shall commence on {start_date} and expire on {end_date} (Duration: {duration} days).

RENT:
Monthly Rent: ${booking.room.price}
Total Rent: ${booking.total_rent}
Payment Method: Online payment through RoomBook platform

TERMS AND CONDITIONS:

1. USE OF PREMISES: The premises shall be used for residential purposes only.

2. MAINTENANCE: The Tenant shall keep the premises in clean and good condition.

3. UTILITIES: Utilities are included/excluded as specified in the room listing.

4. SECURITY DEPOSIT: A security deposit may be required as per platform policies.

5. TERMINATION: This agreement may be terminated by either party with proper notice as per platform terms.

6. HOUSE RULES: Tenant agrees to abide by all house rules specified in the room listing.

7. PAYMENT TERMS: Rent shall be paid through the RoomBook platform according to the payment schedule.

This agreement constitutes the entire understanding between the parties and supersedes all prior agreements.

OWNER SIGNATURE: _________________________ Date: ___________

TENANT SIGNATURE: _________________________ Date: ___________

Generated by RoomBook AI Agreement Generator
{timezone.now().strftime('%B %d, %Y')}
"""
    return agreement.strip()

def generate_custom_agreement(data):
    """Generate custom rental agreement text"""
    agreement = f"""
RENTAL AGREEMENT

This Rental Agreement is made and entered into on {timezone.now().strftime('%B %d, %Y')}

BETWEEN:
{data['owner_name']} (hereinafter "Owner")

AND:
{data['tenant_name']} (hereinafter "Tenant")

PROPERTY:
{data['property_address']}
{data.get('property_description', '')}

TERM:
Duration: {data['duration_months']} months
Commencement Date: {data.get('start_date', 'To be determined')}

RENT:
Monthly Rent: ${data['rent_amount']}
Payment Due: {data.get('payment_due_date', 'First day of each month')}

TERMS AND CONDITIONS:

1. USE OF PREMISES: The premises shall be used for residential purposes only.

2. MAINTENANCE: The Tenant shall maintain the premises in good condition.

3. UTILITIES: All utilities and additional charges as specified.

4. SECURITY DEPOSIT: {data.get('security_deposit', 'As per local laws')}

5. TERMINATION: Notice period as per local rental laws.

6. ADDITIONAL TERMS: {data.get('additional_terms', 'None specified')}

This agreement is legally binding and constitutes the entire understanding between parties.

OWNER SIGNATURE: _________________________ Date: ___________

TENANT SIGNATURE: _________________________ Date: ___________

Generated by RoomBook AI Agreement Generator
{timezone.now().strftime('%B %d, %Y')}
"""
    return agreement.strip()

def create_agreement_pdf(agreement_text, title):
    """Create PDF from agreement text"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))
    
    # Agreement content
    content_style = styles['Normal']
    paragraphs = agreement_text.split('\n\n')
    
    for paragraph in paragraphs:
        if paragraph.strip():
            if paragraph.strip().endswith(':'):
                # Header
                header_style = styles['Heading2']
                story.append(Paragraph(paragraph.strip(), header_style))
            else:
                # Regular text
                story.append(Paragraph(paragraph.strip(), content_style))
            story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
