from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth.forms import AuthenticationForm
from .forms import CustomUserCreationForm, ProfileEditForm
from .models import User

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send mock verification email
            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', kwargs={'username': user.username})
            )
            try:
                send_mail(
                    subject='Verify your EventHub Account',
                    message=f'Hello {user.username},\n\nPlease verify your email by clicking the link: {verification_url}\n\nRegards,\nEventHub Team',
                    from_email='noreply@eventhub.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "Registration successful! A mock verification email has been printed to the server console. Click the link in the console to verify your account.")
            except Exception as e:
                messages.error(request, f"Error sending verification email: {e}")
                
            return redirect('accounts:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def verify_email_view(request, username):
    user = get_object_or_404(User, username=username)
    user.is_email_verified = True
    user.save()
    auth_login(request, user)
    messages.success(request, f"Email verified successfully! Welcome to EventHub, {user.username}.")
    return redirect('dashboard:dashboard')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid login credentials.")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        auth_logout(request)
        messages.info(request, "Logged out successfully.")
    return redirect('landing')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
