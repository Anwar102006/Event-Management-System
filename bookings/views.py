from io import BytesIO
from datetime import timedelta
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from events.models import Event
from .models import Booking
from notifications.utils import create_notification
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
import os

@login_required
def checkout_view(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk, is_approved=True)

    if event.is_sold_out():
        messages.error(request, "Sorry, this event is sold out.")
        return redirect('events:detail', pk=event_pk)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        payment_method = request.POST.get('payment_method', 'Cash')

        try:
            with transaction.atomic():
                # Acquire row-level lock on the Event row
                locked_event = Event.objects.select_for_update().get(pk=event_pk, is_approved=True)

                if quantity < 1:
                    messages.error(request, "Invalid ticket quantity.")
                    return redirect('bookings:checkout', event_pk=event_pk)

                if quantity > locked_event.available_seats:
                    messages.error(request, f"Sorry, only {locked_event.available_seats} seats are available.")
                    return redirect('bookings:checkout', event_pk=event_pk)

                total_price = locked_event.ticket_price * quantity

                # Temporarily deduct seats from available count
                locked_event.available_seats -= quantity
                locked_event.save()

                # Create booking in Pending Payment state
                booking = Booking.objects.create(
                    user=request.user,
                    event=locked_event,
                    quantity=quantity,
                    total_price=total_price,
                    status='Pending Payment',
                    expires_at=timezone.now() + timedelta(minutes=15)
                )

                # Create corresponding Payment record in Pending state
                from payments.models import Payment
                import uuid
                Payment.objects.create(
                    booking=booking,
                    payment_method=payment_method,
                    transaction_id='TXN-' + str(uuid.uuid4()).upper()[:10],
                    amount=total_price,
                    status='Pending',
                )

                # Create notification
                create_notification(
                    user=request.user,
                    title='Seat Reservation Held! ⏳',
                    message=f'Your reservation for "{locked_event.title}" (ID: {booking.booking_id}) is held. Please complete your payment within 15 minutes.'
                )

                messages.success(request, f"Seat reservation held! Booking ID: {booking.booking_id}. Please complete payment in 15 minutes.")
                return redirect('bookings:confirmation', pk=booking.pk)
        except Event.DoesNotExist:
            messages.error(request, "Event not found.")
            return redirect('events:list')
        except Exception as e:
            messages.error(request, f"Checkout failed: {e}")
            return redirect('events:detail', pk=event_pk)

    context = {'event': event}
    return render(request, 'bookings/checkout.html', context)

@login_required
def booking_confirmation_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    return render(request, 'bookings/confirmation.html', {'booking': booking})

@login_required
def download_ticket_pdf(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Background gradient effect - plain white with colored header
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.rect(0, h - 160, w, 160, fill=True, stroke=False)

    # Header text
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 28)
    p.drawString(30, h - 55, "EventHub Ticket")
    p.setFont("Helvetica", 12)
    p.drawString(30, h - 80, "Your official entry pass")
    p.drawString(30, h - 100, f"Booking ID: {booking.booking_id}")

    # Event banner (if exists)
    y_pos = h - 320
    if booking.event.banner:
        try:
            banner_path = booking.event.banner.path
            p.drawImage(banner_path, 30, y_pos, width=w - 60, height=140, preserveAspectRatio=True)
        except Exception:
            pass
        y_pos -= 160

    # Body section
    p.setFillColor(colors.HexColor('#1e1b4b'))
    p.setFont("Helvetica-Bold", 20)
    p.drawString(30, y_pos, booking.event.title)

    y_pos -= 30
    p.setFillColor(colors.HexColor('#6b7280'))
    p.setFont("Helvetica", 12)
    lines = [
        f"Date & Time:   {booking.event.date_time.strftime('%B %d, %Y at %H:%M')}",
        f"Venue:         {booking.event.venue}",
        f"Category:      {booking.event.category}",
        f"Organizer:     {booking.event.organizer.get_full_name() or booking.event.organizer.username}",
        "",
        f"Attendee:      {booking.user.get_full_name() or booking.user.username}",
        f"Email:         {booking.user.email}",
        f"Quantity:      {booking.quantity} ticket(s)",
        f"Total Paid:    ${booking.total_price}",
        f"Booking Date:  {booking.booking_date.strftime('%B %d, %Y')}",
        f"Status:        {booking.status}",
    ]
    for line in lines:
        p.drawString(30, y_pos, line)
        y_pos -= 20

    # QR Code
    if booking.qr_code_image:
        try:
            qr_path = booking.qr_code_image.path
            p.drawImage(qr_path, w - 180, y_pos - 140, width=150, height=150)
        except Exception:
            pass

    # Footer
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(30, 40, "EventHub - Scan the QR code at the venue entrance for quick check-in.")
    p.drawString(30, 25, "Powered by EventHub Event Management Platform")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="EventHub_Ticket_{booking.booking_id}.pdf"'
    return response

@login_required
def cancel_booking_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if booking.status == 'Confirmed':
        booking.status = 'Cancelled'
        booking.save()
        # Restore available seats
        booking.event.available_seats += booking.quantity
        booking.event.save()
        create_notification(
            user=request.user,
            title='Booking Cancelled',
            message=f'Your booking {booking.booking_id} for "{booking.event.title}" has been cancelled. Refund (if applicable) will be processed shortly.'
        )
        messages.info(request, f"Booking {booking.booking_id} has been cancelled.")
    return redirect('dashboard:dashboard')

@login_required
def checkin_view(request):
    """Organizer ticket scanning/manual check-in interface."""
    if not (request.user.is_organizer() or request.user.is_admin()):
        messages.error(request, "Access denied.")
        return redirect('landing')

    # Organizers only see their events' bookings
    organizer_events = request.user.organized_events.all() if request.user.is_organizer() else None
    booking = None
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id', '').strip().upper()
        try:
            booking = Booking.objects.get(booking_id=booking_id)
            if organizer_events and booking.event not in organizer_events:
                messages.error(request, "This booking is not for one of your events.")
                booking = None
            elif booking.status == 'Attended':
                messages.warning(request, f"Booking {booking_id} has already been checked in.")
            elif booking.status == 'Cancelled':
                messages.error(request, f"Booking {booking_id} has been cancelled.")
            else:
                booking.status = 'Attended'
                booking.save()
                messages.success(request, f"✅ Check-in successful for {booking.user.username} at {booking.event.title}!")
        except Booking.DoesNotExist:
            messages.error(request, f"No booking found with ID: {booking_id}")

    return render(request, 'bookings/checkin.html', {'booking': booking})

@login_required
def download_certificate_pdf(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if booking.event.category != 'Workshops':
        messages.error(request, "Certificates are only generated for Workshops.")
        return redirect('dashboard:dashboard')
        
    if booking.status not in ['Confirmed', 'Attended']:
        messages.error(request, "You must attend the workshop to obtain a certificate.")
        return redirect('dashboard:dashboard')

    buffer = BytesIO()
    from reportlab.lib.pagesizes import landscape
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    w, h = landscape(A4)

    p.setStrokeColor(colors.HexColor('#7c3aed'))
    p.setLineWidth(4)
    p.rect(30, 30, w - 60, h - 60)
    
    p.setStrokeColor(colors.HexColor('#db2777'))
    p.setLineWidth(1)
    p.rect(38, 38, w - 76, h - 76)

    p.setFont("Helvetica-Bold", 36)
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.drawCentredString(w / 2.0, h - 120, "CERTIFICATE OF COMPLETION")
    
    p.setFont("Helvetica", 14)
    p.setFillColor(colors.HexColor('#4b5563'))
    p.drawCentredString(w / 2.0, h - 165, "PROUDLY PRESENTED TO")
    
    p.setFont("Helvetica-Bold", 26)
    p.setFillColor(colors.HexColor('#1e1b4b'))
    user_name = booking.user.get_full_name() or booking.user.username
    p.drawCentredString(w / 2.0, h - 220, user_name.upper())
    
    p.setStrokeColor(colors.HexColor('#db2777'))
    p.setLineWidth(2)
    p.line(w / 2.0 - 150, h - 235, w / 2.0 + 150, h - 235)
    
    p.setFont("Helvetica", 14)
    p.setFillColor(colors.HexColor('#4b5563'))
    p.drawCentredString(w / 2.0, h - 275, "for successfully participating in and completing the professional workshop")
    
    p.setFont("Helvetica-Bold", 20)
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.drawCentredString(w / 2.0, h - 315, f'"{booking.event.title}"')
    
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.HexColor('#6b7280'))
    p.drawCentredString(w / 2.0, h - 355, f"Held on {booking.event.date_time.strftime('%B %d, %Y')} at {booking.event.venue}")
    p.drawCentredString(w / 2.0, h - 375, f"Verification ID: {booking.booking_id}")

    sig_y = 120
    p.setStrokeColor(colors.HexColor('#94a3b8'))
    p.setLineWidth(1)
    
    p.line(100, sig_y + 15, 280, sig_y + 15)
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor('#374151'))
    org_name = booking.event.organizer.get_full_name() or booking.event.organizer.username
    p.drawCentredString(190, sig_y, org_name)
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(colors.HexColor('#6b7280'))
    p.drawCentredString(190, sig_y - 15, "Workshop Instructor / Organizer")
    
    p.line(w - 280, sig_y + 15, w - 100, sig_y + 15)
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor('#374151'))
    p.drawCentredString(w - 190, sig_y, "EventHub Director")
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(colors.HexColor('#6b7280'))
    p.drawCentredString(w - 190, sig_y - 15, "Verification Authority")

    p.setFillColor(colors.HexColor('#d97706'))
    p.circle(w / 2.0, sig_y + 20, 30, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 8)
    p.drawCentredString(w / 2.0, sig_y + 22, "VERIFIED")
    p.drawCentredString(w / 2.0, sig_y + 10, "SEAL")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Workshop_Certificate_{booking.booking_id}.pdf"'
    return response
