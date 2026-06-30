from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from events.models import Event
from bookings.models import Booking
from payments.models import Payment

class EventManagementSystemTests(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpassword123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.organizer = User.objects.create_user(
            username='organizer_test',
            email='organizer@test.com',
            password='testpassword123',
            role='organizer'
        )
        self.user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            password='testpassword123',
            role='user'
        )

        # Create an event
        self.event = Event.objects.create(
            title='Tech Workshop 2026',
            description='Learn Python Django web development.',
            category='Workshops',
            organizer=self.organizer,
            date_time=timezone.now() + timezone.timedelta(days=5),
            venue='Silicon Valley',
            max_seats=50,
            available_seats=50,
            ticket_price=10.00,
            status='Upcoming',
            is_approved=True
        )

    def test_user_roles(self):
        """Test user role classifications."""
        self.assertTrue(self.admin.is_admin())
        self.assertTrue(self.organizer.is_organizer())
        self.assertTrue(self.user.is_regular_user())

    def test_booking_and_payment_flow(self):
        """Test user checkout process, seat reduction, and payment creation."""
        self.client.login(username='user_test', password='testpassword123')
        
        # Verify available seats before booking
        self.assertEqual(self.event.available_seats, 50)

        # Post booking request
        checkout_url = reverse('bookings:checkout', kwargs={'event_pk': self.event.pk})
        response = self.client.post(checkout_url, {
            'quantity': 2,
            'payment_method': 'Credit Card'
        })
        
        # Verify redirect to confirmation
        self.assertEqual(response.status_code, 302)
        
        # Refresh event from DB and verify seat reduction
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_seats, 48)

        # Verify booking creation
        booking = Booking.objects.get(user=self.user, event=self.event)
        self.assertEqual(booking.quantity, 2)
        self.assertEqual(booking.total_price, 20.00)
        self.assertEqual(booking.status, 'Confirmed')
        self.assertTrue(booking.booking_id.startswith('EVH-'))
        self.assertTrue(booking.qr_code_image.name.startswith('qrcodes/qr_'))

        # Verify payment creation
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.amount, 20.00)
        self.assertEqual(payment.payment_method, 'Credit Card')
        self.assertEqual(payment.status, 'Completed')

    def test_role_based_permissions(self):
        """Test dashboard routing based on user role permissions."""
        # 1. Admin login redirects to admin dashboard when hitting standard dashboard
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertRedirects(response, reverse('dashboard:admin'))

        # 2. Organizer login redirects to organizer dashboard
        self.client.login(username='organizer_test', password='testpassword123')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertRedirects(response, reverse('dashboard:organizer'))

        # 3. Regular user dashboard loads correctly
        self.client.login(username='user_test', password='testpassword123')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/user.html')

    def test_admin_event_approval_actions(self):
        """Test admin's ability to approve or reject events."""
        # Create an unapproved event
        pending_event = Event.objects.create(
            title='Secret Tech Talk',
            description='Unapproved session.',
            category='Technology',
            organizer=self.organizer,
            date_time=timezone.now() + timezone.timedelta(days=2),
            venue='Unknown',
            max_seats=10,
            available_seats=10,
            ticket_price=0.00,
            status='Upcoming',
            is_approved=False
        )

        # Try to approve as normal user -> access denied
        self.client.login(username='user_test', password='testpassword123')
        approve_url = reverse('dashboard:approve_event', kwargs={'pk': pending_event.pk})
        response = self.client.get(approve_url)
        self.assertEqual(response.status_code, 403)

        # Approve as admin
        self.client.login(username='admin_test', password='testpassword123')
        response = self.client.get(approve_url)
        self.assertEqual(response.status_code, 302)
        
        pending_event.refresh_from_db()
        self.assertTrue(pending_event.is_approved)

    def test_pdf_downloads(self):
        """Test PDF receipt, ticket pass, and certificate endpoint downloads."""
        self.client.login(username='user_test', password='testpassword123')
        
        booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            quantity=1,
            total_price=10.00,
            status='Confirmed'
        )
        Payment.objects.create(
            booking=booking,
            payment_method='UPI',
            transaction_id='TXN-TESTPDF',
            amount=10.00,
            status='Completed'
        )

        # 1. Ticket PDF
        ticket_url = reverse('bookings:download_ticket', kwargs={'pk': booking.pk})
        response = self.client.get(ticket_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # 2. Receipt PDF
        receipt_url = reverse('payments:download_receipt', kwargs={'booking_id': booking.booking_id})
        response = self.client.get(receipt_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # 3. Certificate PDF (Since category is Workshops and status is Confirmed)
        cert_url = reverse('bookings:download_certificate', kwargs={'pk': booking.pk})
        response = self.client.get(cert_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
