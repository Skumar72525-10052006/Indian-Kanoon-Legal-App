// Authentication JavaScript
const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

// State management
let currentUser = null;
let authToken = null;
let otpVerified = false;

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    setupEventListeners();
    setupPasswordToggles();
});

// Initialize authentication
function initAuth() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');

    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);
        updateUIForLoggedInUser();
    }
}

// Setup event listeners
function setupEventListeners() {
    // Modal controls
    document.getElementById('loginBtn')?.addEventListener('click', () => openModal('loginModal'));
    document.getElementById('showSignupModal')?.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('loginModal');
        openModal('signupModal');
    });
    document.getElementById('showLoginModal')?.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('signupModal');
        openModal('loginModal');
    });
    document.getElementById('showForgotPasswordModal')?.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('loginModal');
        openModal('forgotPasswordModal');
    });
    document.getElementById('backToLogin')?.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('forgotPasswordModal');
        closeModal('resetPasswordModal');
        openModal('loginModal');
    });

    // Close modals
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modalId = e.target.getAttribute('data-modal');
            closeModal(modalId);
        });
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    // Form submissions
    document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
    document.getElementById('signupForm')?.addEventListener('submit', handleSignup);
    document.getElementById('forgotPasswordForm')?.addEventListener('submit', handleForgotPassword);
    document.getElementById('resetPasswordForm')?.addEventListener('submit', handleResetPassword);

    // OTP button
    document.getElementById('sendOtpBtn')?.addEventListener('click', handleSendOTP);

    // Logout
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);

    // User menu toggle
    document.getElementById('userBtn')?.addEventListener('click', () => {
        const dropdown = document.getElementById('userDropdown');
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });

    // Profile
    document.getElementById('profileBtn')?.addEventListener('click', openProfileModal);
    document.getElementById('profileForm')?.addEventListener('submit', handleProfileUpdate);

}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Handle Send OTP
async function handleSendOTP(e) {
    e.preventDefault();
    const email = document.getElementById('signupEmail').value;

    if (!email) {
        showNotification('Please enter email address', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('OTP sent to your email!', 'success');
            document.getElementById('otpGroup').style.display = 'block';
            document.getElementById('sendOtpBtn').disabled = true;
            document.getElementById('sendOtpBtn').textContent = 'OTP Sent';

            // Enable verify button
            document.getElementById('signupOtp').addEventListener('input', async (e) => {
                if (e.target.value.length === 6) {
                    await verifyOTP(email, e.target.value);
                }
            });
        } else {
            showNotification(data.detail || 'Failed to send OTP', 'error');
        }
    } catch (error) {
        showNotification('Error sending OTP', 'error');
        console.error(error);
    }
}

// Verify OTP
async function verifyOTP(email, otp) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('OTP verified successfully!', 'success');
            otpVerified = true;
            document.getElementById('signupSubmitBtn').disabled = false;
            document.getElementById('signupOtp').style.borderColor = 'green';
        } else {
            showNotification(data.detail || 'Invalid OTP', 'error');
            document.getElementById('signupOtp').style.borderColor = 'red';
        }
    } catch (error) {
        showNotification('Error verifying OTP', 'error');
        console.error(error);
    }
}

// Handle Login
async function handleLogin(e) {
    e.preventDefault();
    const identifier = document.getElementById('loginIdentifier').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier, password })
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('user', JSON.stringify(currentUser));

            showNotification('Login successful!', 'success');
            closeModal('loginModal');
            updateUIForLoggedInUser();
        } else {
            showNotification(data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        showNotification('Error during login', 'error');
        console.error(error);
    }
}

// Handle Signup
async function handleSignup(e) {
    e.preventDefault();

    if (!otpVerified) {
        showNotification('Please verify OTP first', 'error');
        return;
    }

    const formData = {
        full_name: document.getElementById('signupFullName').value,
        username: document.getElementById('signupUsername').value,
        email: document.getElementById('signupEmail').value,
        mobile_number: document.getElementById('signupMobile').value,
        password: document.getElementById('signupPassword').value,
        user_type: document.getElementById('signupUserType').value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('user', JSON.stringify(currentUser));

            showNotification('Account created successfully!', 'success');
            closeModal('signupModal');
            updateUIForLoggedInUser();
        } else {
            showNotification(data.detail || 'Signup failed', 'error');
        }
    } catch (error) {
        showNotification('Error during signup', 'error');
        console.error(error);
    }
}

// Handle Forgot Password
async function handleForgotPassword(e) {
    e.preventDefault();
    const identifier = document.getElementById('forgotIdentifier').value;

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('OTP sent to your email and mobile', 'success');
            document.getElementById('resetIdentifier').value = identifier;
            closeModal('forgotPasswordModal');
            openModal('resetPasswordModal');
        } else {
            showNotification(data.detail || 'Failed to send OTP', 'error');
        }
    } catch (error) {
        showNotification('Error sending OTP', 'error');
        console.error(error);
    }
}

// Handle Reset Password
async function handleResetPassword(e) {
    e.preventDefault();
    const identifier = document.getElementById('resetIdentifier').value;
    const otp = document.getElementById('resetOtp').value;
    const newPassword = document.getElementById('resetNewPassword').value;

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier, otp, new_password: newPassword })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Password reset successfully!', 'success');
            closeModal('resetPasswordModal');
            openModal('loginModal');
        } else {
            showNotification(data.detail || 'Failed to reset password', 'error');
        }
    } catch (error) {
        showNotification('Error resetting password', 'error');
        console.error(error);
    }
}

// Open profile modal and populate with current user data
function openProfileModal() {
    if (!currentUser) return;

    document.getElementById('profileFullName').value = currentUser.full_name || '';
    document.getElementById('profileUsername').value = currentUser.username || '';
    document.getElementById('profileEmail').value = currentUser.email || '';
    document.getElementById('profileMobile').value = currentUser.mobile_number || '';
    document.getElementById('profileUserType').value = currentUser.user_type || 'citizen';

    openModal('profileModal');
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) dropdown.style.display = 'none';
}

// Handle profile update submission
async function handleProfileUpdate(e) {
    e.preventDefault();

    if (!authToken) {
        showNotification('You must be logged in to update your profile', 'error');
        return;
    }

    const updates = {
        full_name: document.getElementById('profileFullName').value.trim(),
        mobile_number: document.getElementById('profileMobile').value.trim(),
        user_type: document.getElementById('profileUserType').value,
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify(updates),
        });

        const data = await response.json();

        if (!response.ok) {
            showNotification(data.detail || 'Failed to update profile', 'error');
            return;
        }

        // Update local user state from server response
        currentUser = data.user || data;
        localStorage.setItem('user', JSON.stringify(currentUser));

        showNotification('Profile updated successfully', 'success');
        closeModal('profileModal');
        updateUIForLoggedInUser();
    } catch (error) {
        console.error('Error updating profile:', error);
        showNotification('Error updating profile. Please try again.', 'error');
    }
}

// Handle Logout
function handleLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');

    showNotification('Logged out successfully', 'success');
    updateUIForLoggedOutUser();
}

// Update UI for logged in user
function updateUIForLoggedInUser() {
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('userMenu').style.display = 'block';
    document.getElementById('userName').textContent = currentUser.full_name;
    document.getElementById('userEmail').textContent = currentUser.email;
    document.getElementById('userBadge').textContent = currentUser.user_type.charAt(0).toUpperCase() + currentUser.user_type.slice(1);
}

// Update UI for logged out user
function updateUIForLoggedOutUser() {
    document.getElementById('loginBtn').style.display = 'block';
    document.getElementById('userMenu').style.display = 'none';
    document.getElementById('userDropdown').style.display = 'none';
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => notification.classList.add('show'), 10);

    // Hide and remove notification
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Get auth token for API requests
function getAuthToken() {
    return authToken;
}

// Get the current user object (for other scripts like script.js)
function getCurrentUser() {
    return currentUser;
}

// Check if user is authenticated
function isAuthenticated() {
    return authToken !== null && currentUser !== null;
}


// Password visibility toggle handlers
function setupPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.password-toggle');

    toggleButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const targetId = button.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (!input) return;

            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            button.textContent = isPassword ? 'Hide' : 'Show';
        });
    });
}

