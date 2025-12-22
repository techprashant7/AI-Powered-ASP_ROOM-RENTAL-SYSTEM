# Razorpay Integration Setup Guide

This guide will help you set up Razorpay payment integration for your Room Rental System.

## Prerequisites

1. **Razorpay Account**: Create an account on [Razorpay](https://razorpay.com/)
2. **Test Mode**: Enable test mode for development
3. **API Keys**: Get your Test Key ID and Test Key Secret

## Step 1: Get Razorpay API Keys

1. Log in to your Razorpay dashboard
2. Go to Settings → API Keys
3. Generate a new key pair for test mode
4. Note down:
   - Key ID (starts with `rzp_test_`)
   - Key Secret (starts with `rzp_test_`)

## Step 2: Configure Environment Variables

Add the following environment variables to your system or `.env` file:

```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_RtVZAJX5D2vIbd
RAZORPAY_KEY_SECRET=3uWYuFDaeyiZEkjQDFJ5YRiU

# Email Configuration (for invoice notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=bprashant23cs@student.mes.ac.in
EMAIL_HOST_PASSWORD=pr@sh@nt777777
DEFAULT_FROM_EMAIL=bprashant23cs@student.mes.ac.in

# Base URL (update with your deployment URL)
BASE_URL=http://localhost:8000
```

## Step 3: Install Dependencies

The required Razorpay package is already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Step 4: Update Django Settings

The Razorpay configuration is already added to `roombook/settings.py`:

```python
# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
```

## Step 5: Frontend Integration

To use Razorpay on the frontend, you need to include the Razorpay checkout script:

```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

### Example Payment Flow:

```javascript
// 1. Create payment order from your backend
const response = await fetch('/api/payments/process/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({
        invoice_id: invoiceId
    })
});

const paymentData = await response.json();

// 2. Open Razorpay checkout
const options = {
    key: paymentData.razorpay_key_id,
    amount: paymentData.amount_paise,
    currency: paymentData.currency,
    name: 'Room Rental System',
    description: paymentData.description,
    order_id: paymentData.razorpay_order_id,
    handler: function (response) {
        // 3. Handle successful payment
        handlePaymentSuccess(response);
    },
    prefill: {
        name: paymentData.customer_name,
        email: paymentData.customer_email,
    },
    theme: {
        color: '#3399cc'
    }
};

const rzp = new Razorpay(options);
rzp.open();
```

## Step 6: Payment Success Handler

```javascript
async function handlePaymentSuccess(response) {
    try {
        const callbackResponse = await fetch('/api/payments/razorpay/callback/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature
            })
        });
        
        const result = await callbackResponse.json();
        
        if (callbackResponse.ok) {
            alert('Payment successful!');
            window.location.reload();
        } else {
            alert('Payment verification failed: ' + result.error);
        }
    } catch (error) {
        alert('Payment processing error: ' + error.message);
    }
}
```

## Step 7: Test the Integration

1. Start your Django development server:
   ```bash
   python manage.py runserver
   ```

2. Test the complete flow:
   - Create a booking
   - Get the booking approved
   - Create an invoice
   - Process payment via Razorpay
   - Check email notifications

## Email Configuration

The system sends emails for:
- Invoice creation (to both user and host)
- Payment confirmation
- Booking status updates

### Gmail Configuration (if using Gmail):

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password
   - Use this password in `EMAIL_HOST_PASSWORD`

## Production Deployment

For production:

1. **Switch to Live Mode**: Change Razorpay keys from test to live mode
2. **Update BASE_URL**: Set your actual domain URL
3. **HTTPS**: Ensure your site uses HTTPS (required by Razorpay)
4. **Security**: Keep your API keys secure and never expose them in frontend code

## Troubleshooting

### Common Issues:

1. **Invalid Signature Error**
   - Ensure your API keys are correct
   - Check that the callback URL matches your BASE_URL

2. **Payment Capture Failed**
   - Verify the payment ID is valid
   - Check if the payment is already captured

3. **Email Not Sending**
   - Verify SMTP settings
   - Check if email/password are correct
   - Ensure less secure apps are enabled (for Gmail)

4. **CORS Issues**
   - Add your frontend domain to `CORS_ALLOWED_ORIGINS` in settings

### Test Cards for Razorpay Test Mode:

Use these test cards for testing payments:

- **Successful Payment**: 4111 1111 1111 1111
- **International Card**: 4212 1234 5678 1234
- **Card with 3D Secure**: 4012 8888 8888 1881

Use any future expiry date and any random CVV.

## Support

- Razorpay Documentation: https://razorpay.com/docs/
- Django Integration Guide: https://razorpay.com/docs/payment-gateway/web-integration/standard/
- For issues, check Django logs and Razorpay dashboard

## Security Notes

1. Never expose your Razorpay Key Secret in frontend code
2. Always verify payment signatures on the backend
3. Use HTTPS in production
4. Implement proper error handling
5. Log all payment transactions for audit purposes
