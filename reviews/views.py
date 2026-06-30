from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from events.models import Event
from .models import Review

@login_required
def submit_review_view(request, event_pk):
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=event_pk, is_approved=True)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not comment:
            messages.error(request, "Please provide both a rating and a comment.")
            return redirect('events:detail', pk=event_pk)

        review, created = Review.objects.update_or_create(
            event=event,
            user=request.user,
            defaults={'rating': int(rating), 'comment': comment}
        )
        if created:
            messages.success(request, "Thank you for your review!")
        else:
            messages.info(request, "Your review has been updated.")
    return redirect('events:detail', pk=event_pk)

@login_required
def like_review_view(request, review_pk):
    if request.method == 'POST':
        review = get_object_or_404(Review, pk=review_pk)
        if request.user in review.likes.all():
            review.likes.remove(request.user)
            status = 'unliked'
        else:
            review.likes.add(request.user)
            status = 'liked'
        return JsonResponse({'status': status, 'likes_count': review.likes.count()})
    return JsonResponse({'error': 'Invalid request'}, status=400)
