// Utility Functions
const formatDate = (date) => {
    return new Date(date).toLocaleDateString();
};

const formatTime = (date) => {
    return new Date(date).toLocaleTimeString();
};

const formatDateTime = (date) => {
    return new Date(date).toLocaleString();
};

// Form Validation
const validateForm = (formId) => {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
};

// Password Validation
const validatePassword = (password) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    return {
        isValid: password.length >= minLength && hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar,
        errors: {
            length: password.length < minLength,
            upperCase: !hasUpperCase,
            lowerCase: !hasLowerCase,
            numbers: !hasNumbers,
            specialChar: !hasSpecialChar
        }
    };
};

// Flash Message Handling
const showFlashMessage = (message, type = 'success') => {
    const flashContainer = document.getElementById('flash-messages');
    if (!flashContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    flashContainer.appendChild(alert);

    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
};

// Map Initialization
const initMap = (elementId, center, markers = []) => {
    const mapElement = document.getElementById(elementId);
    if (!mapElement) return null;

    const map = new google.maps.Map(mapElement, {
        center: center,
        zoom: 12,
        styles: [
            {
                featureType: 'poi',
                elementType: 'labels',
                stylers: [{ visibility: 'off' }]
            }
        ]
    });

    markers.forEach(marker => {
        new google.maps.Marker({
            position: marker.position,
            map: map,
            title: marker.title,
            icon: marker.icon
        });
    });

    return map;
};

// Calendar Initialization
const initCalendar = (elementId, events = []) => {
    const calendarElement = document.getElementById(elementId);
    if (!calendarElement) return null;

    const calendar = new FullCalendar.Calendar(calendarElement, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: events,
        eventClick: function(info) {
            showEventDetails(info.event);
        }
    });

    calendar.render();
    return calendar;
};

// API Request Handler
const apiRequest = async (url, method = 'GET', data = null) => {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || 'An error occurred');
        }

        return result;
    } catch (error) {
        console.error('API Request Error:', error);
        showFlashMessage(error.message, 'danger');
        throw error;
    }
};

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!validateForm(form.id)) {
                e.preventDefault();
                showFlashMessage('Please fill in all required fields', 'danger');
            }
        });
    });

    // Password validation
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', (e) => {
            const validation = validatePassword(e.target.value);
            const feedback = input.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.innerHTML = Object.entries(validation.errors)
                    .filter(([_, hasError]) => hasError)
                    .map(([key]) => `Password must contain ${key}`)
                    .join('<br>');
            }
        });
    });

    // Driver dropdown population
    const driverDropdown = document.getElementById('driver');

    fetch('/drivers')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch drivers');
            }
            return response.json();
        })
        .then(data => {
            data.drivers.forEach(driver => {
                const option = document.createElement('option');
                option.value = driver.id;
                option.textContent = driver.name;
                driverDropdown.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error fetching drivers:', error);
        });
});