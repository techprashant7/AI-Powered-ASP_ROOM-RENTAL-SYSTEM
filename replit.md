# RoomBook - Room Booking Platform

## Overview
A Django-based room booking platform where users can browse rooms, book accommodations, and owners can manage booking requests.

## Features
- **Public Room Listing**: Browse all available rooms with images, prices, and locations
- **Room Details**: View full room information with owner contact details
- **User Booking**: Select dates, duration, auto-calculate total rent
- **Booking Management**: Track booking status (pending/approved/rejected)
- **Owner Dashboard**: Review and approve/reject booking requests
- **User Authentication**: Register, login, logout functionality

## Tech Stack
- **Backend**: Django 5.x with Django REST Framework
- **Database**: SQLite
- **Frontend**: HTML, JavaScript, Bootstrap 5
- **Image Handling**: Pillow

## Project Structure
```
/
├── roombook/           # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── rooms/              # Main app
│   ├── models.py       # Room, Booking models
│   ├── views.py        # API endpoints + page views
│   ├── serializers.py  # DRF serializers
│   ├── urls.py         # URL routing
│   └── admin.py        # Admin configuration
├── templates/          # HTML templates
│   ├── base.html
│   ├── home.html
│   ├── rooms/
│   ├── bookings/
│   └── auth/
├── static/             # Static files
└── media/              # User uploads
```

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/rooms/ | GET | List all rooms |
| /api/rooms/<id>/ | GET | Room details |
| /api/bookings/add/ | POST | Create booking |
| /api/bookings/my/ | GET | User's bookings |
| /api/bookings/received/ | GET | Owner's received requests |
| /api/bookings/approve/<id>/ | PUT | Approve booking |
| /api/bookings/reject/<id>/ | PUT | Reject booking |

## Test Accounts
- **Owner 1**: john_owner / owner123
- **Owner 2**: sarah_owner / owner123
- **User**: mike_user / user123

## Running the Project
```bash
python manage.py runserver 0.0.0.0:5000
```

## Admin Access
Create superuser: `python manage.py createsuperuser`
Access admin at: /admin/
