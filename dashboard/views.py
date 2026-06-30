import csv
import json
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from accounts.models import User
from events.models import Event
from bookings.models import Booking
from payments.models import Payment
from notifications.models import Notification
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ─── User Dashboard ──────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    user = request.user
    if user.is_admin():
        return redirect('dashboard:admin')
    elif user.is_organizer():
        return redirect('dashboard:organizer')

    # User data
    bookings = user.bookings.all()
    upcoming_bookings = bookings.filter(
        status='Confirmed',
        event__date_time__gte=timezone.now()
    ).select_related('event')
    wishlist = user.wishlist_events.filter(is_approved=True)
    recently_viewed = user.recently_viewed_events.filter(is_approved=True)[:8]
    notifications = user.notifications.all()[:10]
    unread_count = user.notifications.filter(is_read=False).count()

    # AI recommendations: events matching user's booked categories
    booked_categories = bookings.values_list('event__category', flat=True).distinct()
    if booked_categories.exists():
        recommended = Event.objects.filter(
            is_approved=True,
            category__in=booked_categories
        ).exclude(bookings__user=user).order_by('-created_at')[:4]
    else:
        # Fallback to upcoming approved events if user has no booking history
        recommended = Event.objects.filter(
            is_approved=True,
            date_time__gte=timezone.now()
        ).exclude(bookings__user=user).order_by('-created_at')[:4]


    context = {
        'bookings': bookings,
        'upcoming_bookings': upcoming_bookings,
        'wishlist': wishlist,
        'recently_viewed': recently_viewed,
        'notifications': notifications,
        'unread_count': unread_count,
        'recommended': recommended,
        'now': timezone.now(),
    }
    return render(request, 'dashboard/user.html', context)

# ─── Organizer Dashboard ──────────────────────────────────────────────────────

@login_required
def organizer_dashboard_view(request):
    if not (request.user.is_organizer() or request.user.is_admin()):
        messages.error(request, "Access denied.")
        return redirect('dashboard:dashboard')

    my_events = request.user.organized_events.all()
    total_revenue = Payment.objects.filter(
        booking__event__in=my_events,
        status='Completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bookings = Booking.objects.filter(event__in=my_events, status='Confirmed').count()
    pending_events = my_events.filter(is_approved=False).count()

    # Monthly ticket sales (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month = timezone.now() - timedelta(days=30 * i)
        count = Booking.objects.filter(
            event__in=my_events,
            booking_date__month=month.month,
            booking_date__year=month.year,
        ).count()
        monthly_data.append({'month': month.strftime('%b %Y'), 'count': count})

    context = {
        'my_events': my_events,
        'total_revenue': total_revenue,
        'total_bookings': total_bookings,
        'pending_events': pending_events,
        'monthly_data': json.dumps(monthly_data),
    }
    return render(request, 'dashboard/organizer.html', context)

@login_required
def export_attendees_csv(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)
    if event.organizer != request.user and not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('dashboard:organizer')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendees_{event.title}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Booking ID', 'User', 'Email', 'Quantity', 'Total Price', 'Status', 'Booking Date'])
    for booking in event.bookings.all():
        writer.writerow([
            booking.booking_id,
            booking.user.get_full_name() or booking.user.username,
            booking.user.email,
            booking.quantity,
            booking.total_price,
            booking.status,
            booking.booking_date.strftime('%Y-%m-%d %H:%M'),
        ])
    return response

# ─── Admin Dashboard ──────────────────────────────────────────────────────────

@login_required
def admin_dashboard_view(request):
    if not request.user.is_admin():
        messages.error(request, "Admin access required.")
        return redirect('dashboard:dashboard')

    # Analytics data for Charts
    now = timezone.now()
    monthly_bookings = []
    monthly_revenue = []
    months_labels = []
    for i in range(5, -1, -1):
        month_dt = now - timedelta(days=30 * i)
        month_label = month_dt.strftime('%b %Y')
        months_labels.append(month_label)
        count = Booking.objects.filter(
            booking_date__month=month_dt.month,
            booking_date__year=month_dt.year,
        ).count()
        rev = Payment.objects.filter(
            created_at__month=month_dt.month,
            created_at__year=month_dt.year,
            status='Completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_bookings.append(count)
        monthly_revenue.append(float(rev))

    # Category breakdown
    category_data = list(
        Booking.objects.values('event__category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = [d['event__category'] for d in category_data]
    category_counts = [d['count'] for d in category_data]

    # User growth (new signups by month last 6 months)
    user_growth = []
    for i in range(5, -1, -1):
        month_dt = now - timedelta(days=30 * i)
        count = User.objects.filter(
            date_joined__month=month_dt.month,
            date_joined__year=month_dt.year,
        ).count()
        user_growth.append(count)

    # Summary stats
    total_users = User.objects.count()
    total_events = Event.objects.count()
    total_bookings = Booking.objects.count()
    total_revenue = Payment.objects.filter(status='Completed').aggregate(total=Sum('amount'))['total'] or 0
    pending_approvals = Event.objects.filter(is_approved=False).count()

    # Pending events for approval table
    pending_events = Event.objects.filter(is_approved=False).select_related('organizer')

    context = {
        'months_labels': json.dumps(months_labels),
        'monthly_bookings': json.dumps(monthly_bookings),
        'monthly_revenue': json.dumps(monthly_revenue),
        'category_labels': json.dumps(category_labels),
        'category_counts': json.dumps(category_counts),
        'user_growth': json.dumps(user_growth),
        'total_users': total_users,
        'total_events': total_events,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'pending_approvals': pending_approvals,
        'pending_events': pending_events,
        'all_users': User.objects.all().order_by('-date_joined')[:20],
        'recent_bookings': Booking.objects.all().order_by('-booking_date')[:15],
    }
    return render(request, 'dashboard/admin.html', context)

@login_required
def approve_event_view(request, pk):
    if not request.user.is_admin():
        return JsonResponse({'error': 'Access denied'}, status=403)
    event = get_object_or_404(Event, pk=pk)
    event.is_approved = True
    event.save()
    messages.success(request, f'Event "{event.title}" has been approved.')
    return redirect('dashboard:admin')

@login_required
def reject_event_view(request, pk):
    if not request.user.is_admin():
        return JsonResponse({'error': 'Access denied'}, status=403)
    event = get_object_or_404(Event, pk=pk)
    event.delete()
    messages.info(request, 'Event rejected and removed.')
    return redirect('dashboard:admin')

@login_required
def toggle_user_active_view(request, pk):
    if not request.user.is_admin():
        return redirect('dashboard:admin')
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save()
    status_text = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User {user.username} has been {status_text}.")
    return redirect('dashboard:admin')

@login_required
def delete_user_view(request, pk):
    if not request.user.is_admin():
        return redirect('dashboard:admin')
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} has been deleted.")
    return redirect('dashboard:admin')

@login_required
def export_report_csv(request):
    if not request.user.is_admin():
        return redirect('dashboard:admin')

    report_type = request.GET.get('type', 'monthly')
    now = timezone.now()

    if report_type == 'daily':
        start_date = now - timedelta(days=1)
    elif report_type == 'weekly':
        start_date = now - timedelta(weeks=1)
    elif report_type == 'yearly':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)

    bookings = Booking.objects.filter(booking_date__gte=start_date).select_related('user', 'event')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="EventHub_Report_{report_type}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Booking ID', 'User', 'Event', 'Category', 'Qty', 'Total Price', 'Status', 'Date'])
    for b in bookings:
        writer.writerow([
            b.booking_id, b.user.username, b.event.title, b.event.category,
            b.quantity, b.total_price, b.status,
            b.booking_date.strftime('%Y-%m-%d %H:%M')
        ])
    return response

@login_required
def export_report_pdf(request):
    if not request.user.is_admin():
        return redirect('dashboard:admin')

    report_type = request.GET.get('type', 'monthly')
    now = timezone.now()
    if report_type == 'daily':
        start_date = now - timedelta(days=1)
    elif report_type == 'weekly':
        start_date = now - timedelta(weeks=1)
    elif report_type == 'yearly':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)

    bookings = Booking.objects.filter(booking_date__gte=start_date).select_related('user', 'event')
    total_revenue = bookings.aggregate(total=Sum('total_price'))['total'] or 0

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    p.setFillColor(colors.HexColor('#7c3aed'))
    p.rect(0, h - 100, w, 100, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(30, h - 45, f"EventHub - {report_type.capitalize()} Report")
    p.setFont("Helvetica", 11)
    p.drawString(30, h - 70, f"Generated: {now.strftime('%Y-%m-%d %H:%M')} | Total: {bookings.count()} bookings | Revenue: ${total_revenue:.2f}")

    y = h - 130
    p.setFillColor(colors.HexColor('#1e1b4b'))
    p.setFont("Helvetica-Bold", 10)
    cols = ['Booking ID', 'User', 'Event', 'Qty', 'Price', 'Status']
    col_x = [30, 110, 230, 370, 420, 480]
    for i, col in enumerate(cols):
        p.drawString(col_x[i], y, col)

    y -= 15
    p.setStrokeColor(colors.HexColor('#7c3aed'))
    p.line(30, y, w - 30, y)
    y -= 12

    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor('#374151'))
    for b in bookings:
        if y < 60:
            p.showPage()
            y = h - 60
        p.drawString(col_x[0], y, b.booking_id)
        p.drawString(col_x[1], y, b.user.username[:12])
        p.drawString(col_x[2], y, b.event.title[:18])
        p.drawString(col_x[3], y, str(b.quantity))
        p.drawString(col_x[4], y, f"${b.total_price:.2f}")
        p.drawString(col_x[5], y, b.status)
        y -= 15

    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="EventHub_Report_{report_type}.pdf"'
    return response

@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('dashboard:dashboard')
