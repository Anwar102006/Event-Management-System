from io import BytesIO
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from bookings.models import Booking
from .models import Payment

@login_required
def invoice_detail_view(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    # Check permissions: only booking owner, event organizer, or admin can view
    if booking.user != request.user and booking.event.organizer != request.user and not request.user.is_admin():
        raise Http404("Invoice not found or access denied.")
    
    payment = getattr(booking, 'payment', None)
    context = {
        'booking': booking,
        'payment': payment,
    }
    return render(request, 'payments/invoice.html', context)

@login_required
def download_receipt_pdf(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    if booking.user != request.user and booking.event.organizer != request.user and not request.user.is_admin():
        raise Http404("Invoice not found or access denied.")
        
    payment = getattr(booking, 'payment', None)
    if not payment:
        raise Http404("Payment record not found.")

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Outer border
    p.setStrokeColor(colors.HexColor('#e2e8f0'))
    p.setLineWidth(1)
    p.rect(20, 20, w - 40, h - 40)

    # Top purple bar
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.rect(20, h - 120, w - 40, 100, fill=True, stroke=False)

    # Header text
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(40, h - 70, "EVENTHUB INVOICE")
    p.setFont("Helvetica", 10)
    p.drawString(40, h - 95, f"Transaction Date: {payment.created_at.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(w - 240, h - 70, f"Invoice #: INV-{payment.transaction_id}")
    p.drawString(w - 240, h - 95, f"Booking Ref: {booking.booking_id}")

    # Details columns
    y = h - 170
    p.setFillColor(colors.HexColor('#1e1b4b'))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Billed To:")
    p.drawString(w - 240, y, "Event Details:")

    y -= 20
    p.setFillColor(colors.HexColor('#374151'))
    p.setFont("Helvetica", 10)
    
    # User Details
    user_name = booking.user.get_full_name() or booking.user.username
    p.drawString(40, y, user_name)
    p.drawString(40, y - 15, booking.user.email)
    if booking.user.phone_number:
        p.drawString(40, y - 30, booking.user.phone_number)
    else:
        p.drawString(40, y - 30, "")

    # Event Details
    p.drawString(w - 240, y, booking.event.title)
    p.drawString(w - 240, y - 15, f"Date: {booking.event.date_time.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(w - 240, y - 30, f"Venue: {booking.event.venue}")

    # Divider line
    y -= 60
    p.setStrokeColor(colors.HexColor('#cbd5e1'))
    p.setLineWidth(0.5)
    p.line(40, y, w - 40, y)

    # Table headers
    y -= 25
    p.setFillColor(colors.HexColor('#1e1b4b'))
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "Description")
    p.drawRightString(w - 180, y, "Price")
    p.drawRightString(w - 100, y, "Qty")
    p.drawRightString(w - 40, y, "Total")

    # Table items
    y -= 10
    p.line(40, y, w - 40, y)
    y -= 25
    p.setFillColor(colors.HexColor('#374151'))
    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Ticket Entry - {booking.event.title}")
    p.drawRightString(w - 180, y, f"${booking.event.ticket_price:.2f}")
    p.drawRightString(w - 100, y, str(booking.quantity))
    p.drawRightString(w - 40, y, f"${booking.total_price:.2f}")

    # Subtotals & Totals
    y -= 50
    p.line(40, y, w - 40, y)
    y -= 25
    p.setFillColor(colors.HexColor('#1e1b4b'))
    p.setFont("Helvetica-Bold", 11)
    p.drawString(w - 240, y, "Subtotal:")
    p.drawRightString(w - 40, y, f"${booking.total_price:.2f}")
    
    y -= 20
    p.drawString(w - 240, y, "Payment Method:")
    p.drawRightString(w - 40, y, payment.payment_method)

    y -= 20
    p.drawString(w - 240, y, "Status:")
    p.setFillColor(colors.HexColor('#059669'))
    p.drawRightString(w - 40, y, payment.get_status_display())

    y -= 25
    p.setFillColor(colors.HexColor('#7c3aed'))
    p.rect(w - 250, y - 5, 210, 30, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(w - 240, y, "Total Paid:")
    p.drawRightString(w - 50, y, f"${payment.amount:.2f}")

    # Footer notice
    p.setFillColor(colors.HexColor('#6b7280'))
    p.setFont("Helvetica-Oblique", 9)
    p.drawCentredString(w / 2.0, 50, "This is a computer-generated receipt and does not require a physical signature.")
    p.drawCentredString(w / 2.0, 35, "Thank you for using EventHub! Enjoy your event.")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{payment.transaction_id}.pdf"'
    return response
