from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'banner',
            'date_time', 'venue', 'google_maps_link',
            'max_seats', 'ticket_price',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter event title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your event...'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'banner': forms.FileInput(attrs={'class': 'form-control'}),
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter venue name and address'}),
            'google_maps_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://maps.google.com/...'}),
            'max_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
        }

    def save(self, commit=True):
        event = super().save(commit=False)
        # When creating, set available_seats = max_seats
        if not event.pk:
            event.available_seats = self.cleaned_data['max_seats']
        if commit:
            event.save()
        return event
