from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('rooms/', views.room_list_page, name='room_list'),
    path('rooms/<int:room_id>/', views.room_detail_page, name='room_detail'),
    path('about/', views.about_page, name='about'),
    path('services/', views.services_page, name='services'),
    path('contact/', views.contact_page, name='contact'),
    path('owner/rooms/', views.owner_rooms_page, name='owner_rooms'),
    path('owner/rooms/add/', views.owner_room_add_page, name='owner_room_add'),
    path('owner/rooms/<int:room_id>/edit/', views.owner_room_edit_page, name='owner_room_edit'),
    path('my-bookings/', views.my_bookings_page, name='my_bookings'),
    path('owner/bookings/', views.owner_bookings_page, name='owner_bookings'),
    path('profile/', views.profile_page, name='profile'),
    path('notifications/', views.notifications_page, name='notifications'),
    path('privacy/', views.privacy_page, name='privacy'),
    path('terms/', views.terms_page, name='terms'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('verify-otp/', views.verify_otp_page, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    
    path('api/rooms/', views.api_rooms, name='api_rooms'),
    path('api/rooms/<int:room_id>/', views.api_room_detail, name='api_room_detail'),
    path('api/owner/rooms/', views.api_owner_rooms, name='api_owner_rooms'),
    path('api/owner/rooms/<int:room_id>/', views.api_owner_room_detail, name='api_owner_room_detail'),
    path('api/bookings/add/', views.api_create_booking, name='api_create_booking'),
    path('api/bookings/my/', views.api_my_bookings, name='api_my_bookings'),
    path('api/bookings/received/', views.api_received_bookings, name='api_received_bookings'),
    path('api/bookings/approve/<int:booking_id>/', views.api_approve_booking, name='api_approve_booking'),
    path('api/bookings/reject/<int:booking_id>/', views.api_reject_booking, name='api_reject_booking'),
    path('api/bookings/cancel/<int:booking_id>/', views.api_cancel_booking, name='api_cancel_booking'),
    path('api/user/', views.api_current_user, name='api_current_user'),
    path('api/profile/', views.api_profile, name='api_profile'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/unread-count/', views.api_unread_notifications_count, name='api_unread_notifications_count'),
    path('api/notifications/<int:notification_id>/read/', views.api_mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/read-all/', views.api_mark_all_notifications_read, name='api_mark_all_notifications_read'),
    path('api/invoices/', views.api_my_invoices, name='api_my_invoices'),
    path('api/invoices/create/<int:booking_id>/', views.api_create_invoice, name='api_create_invoice'),
    path('api/invoices/<int:invoice_id>/download/', views.api_download_invoice, name='api_download_invoice'),
    path('api/payments/process/', views.api_process_payment, name='api_process_payment'),
    path('api/payments/razorpay/callback/', views.api_razorpay_callback, name='api_razorpay_callback'),
    path('api/payments/', views.api_my_payments, name='api_my_payments'),
    path('api/admin/users/', views.api_admin_users, name='api_admin_users'),
    path('api/admin/users/<int:user_id>/delete/', views.api_admin_delete_user, name='api_admin_delete_user'),
    path('api/admin/users/<int:user_id>/promote/', views.api_admin_promote_user, name='api_admin_promote_user'),
    path('api/admin/users/<int:user_id>/demote/', views.api_admin_demote_user, name='api_admin_demote_user'),
    path('api/admin/users/<int:user_id>/toggle-status/', views.api_admin_toggle_user_status, name='api_admin_toggle_user_status'),
    path('manage-users/', views.manage_users_page, name='manage_users'),
    
    # AI Negotiation Assistant URLs
    path('negotiation/', views.negotiation_assistant_page, name='negotiation_assistant'),
    path('negotiation/<int:room_id>/', views.negotiation_assistant_page, name='negotiation_assistant_room'),
    path('api/negotiation/analyze/', views.api_negotiation_analyze, name='api_negotiation_analyze'),
    
    # Google OAuth URLs
    path('auth/google/', views.google_oauth_login, name='google_oauth_login'),
    path('auth/google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    
    # AI Recommendations URLs
    path('recommendations/', views.recommendations_page, name='recommendations'),
    path('api/ml/recommendations/', views.api_ml_recommendations, name='api_ml_recommendations'),
    path('api/ml/train-recommender/', views.api_ml_train_recommender, name='api_ml_train_recommender'),
    path('api/ml/predict-price/', views.api_ml_predict_price, name='api_ml_predict_price'),
    
    # Chatbot URLs
    path('chatbot/', views.chatbot_page, name='chatbot'),
    path('api/chatbot/message/', views.api_chatbot_message, name='api_chatbot_message'),
    
    # Rental Agreement Generator URLs
    path('agreement-generator/', views.agreement_generator_page, name='agreement_generator'),
    path('agreement-generator/<int:booking_id>/', views.agreement_generator_page, name='agreement_generator_booking'),
    path('api/generate-agreement/', views.api_generate_agreement, name='api_generate_agreement'),
]
