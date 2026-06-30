from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from .models import Event
from .forms import EventForm
from accounts.models import User

def event_list_view(request):
    events = Event.objects.filter(is_approved=True)

    # Search
    search = request.GET.get('search', '')
    if search:
        events = events.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(venue__icontains=search))

    # Category filter
    category = request.GET.get('category', '')
    if category:
        events = events.filter(category=category)

    # Date filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        events = events.filter(date_time__date__gte=date_from)
    if date_to:
        events = events.filter(date_time__date__lte=date_to)

    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by == 'price_asc':
        events = events.order_by('ticket_price')
    elif sort_by == 'price_desc':
        events = events.order_by('-ticket_price')
    elif sort_by == 'date':
        events = events.order_by('date_time')
    elif sort_by == 'popular':
        events = events.annotate(booking_count=Count('bookings')).order_by('-booking_count')
    else:
        events = events.order_by('-created_at')

    from events.models import Event as EventModel
    categories = [c[0] for c in EventModel.CATEGORY_CHOICES]

    context = {
        'events': events,
        'categories': categories,
        'search': search,
        'selected_category': category,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
    }
    return render(request, 'events/list.html', context)

def event_detail_view(request, pk):
    event = get_object_or_404(Event, pk=pk, is_approved=True)

    # Track recently viewed
    if request.user.is_authenticated:
        event.recently_viewed_by.add(request.user)

    reviews = event.reviews.all().order_by('-created_at')
    avg_rating = event.average_rating()
    is_wishlisted = request.user in event.wishlisted_by.all() if request.user.is_authenticated else False

    # AI Recommendations: events of same category, excluding current
    recommended_events = Event.objects.filter(
        category=event.category, is_approved=True
    ).exclude(pk=pk).order_by('-created_at')[:4]

    context = {
        'event': event,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'is_wishlisted': is_wishlisted,
        'recommended_events': recommended_events,
    }
    return render(request, 'events/detail.html', context)

@login_required
def toggle_wishlist_view(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=pk, is_approved=True)
        if request.user in event.wishlisted_by.all():
            event.wishlisted_by.remove(request.user)
            return JsonResponse({'status': 'removed'})
        else:
            event.wishlisted_by.add(request.user)
            return JsonResponse({'status': 'added'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def event_create_view(request):
    if not (request.user.is_organizer() or request.user.is_admin()):
        messages.error(request, "Only organizers can create events.")
        return redirect('events:list')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.available_seats = event.max_seats
            if request.user.is_admin():
                event.is_approved = True
            event.save()
            messages.success(request, "Event submitted successfully! It will be visible once approved by an admin.")
            return redirect('dashboard:organizer')
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})

@login_required
def event_edit_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user and not request.user.is_admin():
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('events:list')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated_event = form.save(commit=False)
            # Adjust available seats if max_seats changed
            diff = form.cleaned_data['max_seats'] - event.max_seats
            updated_event.available_seats = max(0, event.available_seats + diff)
            updated_event.save()
            messages.success(request, "Event updated successfully!")
            return redirect('events:detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Edit', 'event': event})

@login_required
def event_delete_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user and not request.user.is_admin():
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('events:list')
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully.")
        return redirect('dashboard:organizer')
    return render(request, 'events/event_confirm_delete.html', {'event': event})
