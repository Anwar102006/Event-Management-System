document.addEventListener('DOMContentLoaded', () => {
    // 1. Theme Toggling Logic
    const themeSwitch = document.querySelector('.theme-switch');
    if (themeSwitch) {
        themeSwitch.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Apply stored theme on load
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme) {
        document.body.setAttribute('data-theme', storedTheme);
    } else {
        // System preference default
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.body.setAttribute('data-theme', systemPrefersDark ? 'dark' : 'light');
    }

    // 2. Mobile Menu Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            // Animate toggle bars if needed
            const spans = navToggle.querySelectorAll('span');
            spans.forEach(span => span.classList.toggle('active'));
        });
    }

    // 3. Message Toast Dismissal
    const alertCloses = document.querySelectorAll('.alert-close');
    alertCloses.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const alert = e.target.closest('.alert-message');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateX(100px)';
                alert.style.transition = 'all 0.3s ease';
                setTimeout(() => alert.remove(), 300);
            }
        });
    });

    // Auto-remove success/info alerts after 5 seconds
    const autoAlerts = document.querySelectorAll('.alert-message:not(.alert-danger)');
    autoAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
            alert.style.transition = 'all 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // 4. Async Wishlist Toggle
    const favButtons = document.querySelectorAll('.event-fav-btn');
    favButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const eventId = button.dataset.eventId;
            if (!eventId) return;

            try {
                const response = await fetch(`/events/${eventId}/wishlist/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'added') {
                        button.classList.add('active');
                        showToast('Success', 'Event added to your wishlist!', 'success');
                    } else if (data.status === 'removed') {
                        button.classList.remove('active');
                        showToast('Success', 'Event removed from your wishlist.', 'info');
                    }
                } else if (response.status === 403) {
                    showToast('Authentication Required', 'Please log in to add events to your wishlist.', 'warning');
                }
            } catch (err) {
                console.error('Error toggling wishlist:', err);
            }
        });
    });

    // 5. Async Review Liking
    const likeButtons = document.querySelectorAll('.review-likes-action');
    likeButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            const reviewId = button.dataset.reviewId;
            if (!reviewId) return;

            try {
                const response = await fetch(`/reviews/${reviewId}/like/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    button.querySelector('.like-count').textContent = data.likes_count;
                    if (data.status === 'liked') {
                        button.classList.add('liked');
                    } else if (data.status === 'unliked') {
                        button.classList.remove('liked');
                    }
                } else if (response.status === 403) {
                    showToast('Authentication Required', 'Please log in to like reviews.', 'warning');
                }
            } catch (err) {
                console.error('Error liking review:', err);
            }
        });
    });
});

// Helper: Get Cookie Value
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper: Dynamic Toast Notifications
function showToast(title, message, type = 'info') {
    let container = document.querySelector('.messages-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'messages-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `alert-message alert-${type}`;
    toast.innerHTML = `
        <div class="alert-content">
            <strong>${title}</strong>: ${message}
        </div>
        <button class="alert-close">&times;</button>
    `;

    container.appendChild(toast);

    toast.querySelector('.alert-close').addEventListener('click', () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}
