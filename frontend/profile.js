// Constants
const API_BASE_URL = 'https://cardiomedai-api.onrender.com';
const USER_ID = 1; // Default user ID for demo

// Initialize page when loaded
document.addEventListener('DOMContentLoaded', function() {
    loadUserData();
    setupFormHandling();
});

// Load user data
async function loadUserData() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/${USER_ID}`);
        const userData = await response.json();

        // Populate form fields
        document.getElementById('fullName').value = userData.full_name;
        document.getElementById('age').value = userData.age;
        document.getElementById('gender').value = userData.gender;
        document.getElementById('height').value = userData.height;
        document.getElementById('weight').value = userData.weight;
        document.getElementById('medicalConditions').value = userData.medical_conditions || '';
        document.getElementById('medications').value = userData.medications || '';

        // Update header
        document.getElementById('user-name').textContent = `Welcome, ${userData.full_name}`;

    } catch (error) {
        console.error('Error loading user data:', error);
        showMessage('Error loading user data. Please try again later.', 'error');
    }
}

// Setup form handling
function setupFormHandling() {
    const form = document.getElementById('profileForm');
    
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        const saveBtn = form.querySelector('.save-btn');
        const originalBtnContent = saveBtn.innerHTML;
        
        try {
            // Show loading state
            saveBtn.disabled = true;
            saveBtn.classList.add('loading');
            saveBtn.innerHTML = '<i class="fas fa-spinner"></i> Saving...';

            // Get form data
            const formData = {
                full_name: document.getElementById('fullName').value,
                age: parseInt(document.getElementById('age').value),
                gender: document.getElementById('gender').value,
                height: parseFloat(document.getElementById('height').value),
                weight: parseFloat(document.getElementById('weight').value),
                medical_conditions: document.getElementById('medicalConditions').value || null,
                medications: document.getElementById('medications').value || null
            };

            // Send update request
            const response = await fetch(`${API_BASE_URL}/users/${USER_ID}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                throw new Error('Failed to update profile');
            }

            const updatedUser = await response.json();

            // Show success message
            showMessage('✅ Profile updated successfully!', 'success');

            // Update header with new name
            document.getElementById('user-name').textContent = `Welcome, ${updatedUser.full_name}`;

            // Reset button state
            saveBtn.disabled = false;
            saveBtn.classList.remove('loading');
            saveBtn.innerHTML = originalBtnContent;

        } catch (error) {
            console.error('Error updating profile:', error);
            showMessage('Error updating profile. Please try again.', 'error');
            
            // Reset button state
            saveBtn.disabled = false;
            saveBtn.classList.remove('loading');
            saveBtn.innerHTML = originalBtnContent;
        }
    });
}

// Show message function
function showMessage(message, type = 'success') {
    // Remove any existing message
    const existingMessage = document.querySelector('.success-message, .error-message');
    if (existingMessage) {
        existingMessage.remove();
    }

    // Create new message element
    const messageElement = document.createElement('div');
    messageElement.className = type === 'success' ? 'success-message' : 'error-message';
    messageElement.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
    `;

    // Insert message before the form
    const form = document.getElementById('profileForm');
    form.parentNode.insertBefore(messageElement, form);

    // Remove message after 5 seconds
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}
