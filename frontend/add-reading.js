// Constants
const API_BASE_URL = 'http://localhost:8000';
const USER_ID = 1; // Default user ID for demo

// Initialize form when page loads
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('bpForm');
    const systolicInput = document.getElementById('systolic');
    const diastolicInput = document.getElementById('diastolic');
    const statusDiv = document.getElementById('readingStatus');

    // Add input event listeners for real-time status updates
    systolicInput.addEventListener('input', updateReadingStatus);
    diastolicInput.addEventListener('input', updateReadingStatus);

    // Form submission handler
    form.addEventListener('submit', handleSubmit);
});

// Update reading status in real-time
function updateReadingStatus() {
    const systolic = parseInt(document.getElementById('systolic').value);
    const diastolic = parseInt(document.getElementById('diastolic').value);
    const statusDiv = document.getElementById('readingStatus');

    // Only show status if both values are valid
    if (!isNaN(systolic) && !isNaN(diastolic)) {
        const status = interpretBloodPressure(systolic, diastolic);
        statusDiv.style.display = 'block';
        statusDiv.className = `reading-status ${status.class}`;
        statusDiv.innerHTML = `
            <i class="${status.icon}"></i>
            <strong>${status.text}</strong>
            ${status.message}
        `;
    } else {
        statusDiv.style.display = 'none';
    }
}

// Interpret blood pressure readings
function interpretBloodPressure(systolic, diastolic) {
    if (systolic > 180 || diastolic > 120) {
        return {
            text: 'Hypertensive Crisis',
            class: 'high',
            icon: 'fas fa-exclamation-triangle',
            message: 'Seek emergency medical attention immediately!'
        };
    } else if (systolic >= 140 || diastolic >= 90) {
        return {
            text: 'Stage 2 Hypertension',
            class: 'high',
            icon: 'fas fa-exclamation-circle',
            message: 'Consult your healthcare provider as soon as possible.'
        };
    } else if ((systolic >= 130 && systolic <= 139) || (diastolic >= 80 && diastolic <= 89)) {
        return {
            text: 'Stage 1 Hypertension',
            class: 'high',
            icon: 'fas fa-exclamation',
            message: 'Consider lifestyle changes and consult your healthcare provider.'
        };
    } else if (systolic >= 120 && systolic <= 129 && diastolic < 80) {
        return {
            text: 'Elevated Blood Pressure',
            class: 'elevated',
            icon: 'fas fa-arrow-up',
            message: 'Consider making lifestyle modifications to lower your blood pressure.'
        };
    } else if (systolic < 120 && diastolic < 80) {
        return {
            text: 'Normal Blood Pressure',
            class: 'normal',
            icon: 'fas fa-check-circle',
            message: 'Keep up the good work!'
        };
    } else {
        return {
            text: 'Invalid Reading',
            class: 'elevated',
            icon: 'fas fa-question-circle',
            message: 'Please check your measurements and try again.'
        };
    }
}

// Handle form submission
async function handleSubmit(event) {
    event.preventDefault();

    const saveBtn = document.querySelector('.save-btn');
    const originalBtnContent = saveBtn.innerHTML;
    
    try {
        // Show loading state
        saveBtn.disabled = true;
        saveBtn.classList.add('loading');
        saveBtn.innerHTML = '<i class="fas fa-spinner"></i> Saving...';

        // Get form data
        const formData = {
            systolic: parseInt(document.getElementById('systolic').value),
            diastolic: parseInt(document.getElementById('diastolic').value),
            pulse: parseInt(document.getElementById('pulse').value),
            device_id: document.getElementById('device').value || null,
            notes: document.getElementById('notes').value || null
        };

        // Validate readings
        if (formData.systolic < 70 || formData.systolic > 250) {
            throw new Error('Invalid systolic reading (must be between 70 and 250)');
        }
        if (formData.diastolic < 40 || formData.diastolic > 150) {
            throw new Error('Invalid diastolic reading (must be between 40 and 150)');
        }
        if (formData.pulse < 30 || formData.pulse > 220) {
            throw new Error('Invalid pulse reading (must be between 30 and 220)');
        }

        // Send data to API
        const response = await fetch(`${API_BASE_URL}/bp/readings/?user_id=${USER_ID}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error('Failed to save reading');
        }

        const savedReading = await response.json();

        // Show success message
        const status = interpretBloodPressure(savedReading.systolic, savedReading.diastolic);
        const message = `
            ✅ Blood Pressure Reading Saved Successfully!

            Systolic: ${savedReading.systolic} mmHg
            Diastolic: ${savedReading.diastolic} mmHg
            Pulse: ${savedReading.pulse} BPM
            Status: ${status.text}

            Redirecting to dashboard...
        `;

        alert(message);

        // Redirect to dashboard
        window.location.href = 'index.html';

    } catch (error) {
        console.error('Error saving reading:', error);
        alert('Error: ' + error.message);
        
        // Reset button state
        saveBtn.disabled = false;
        saveBtn.classList.remove('loading');
        saveBtn.innerHTML = originalBtnContent;
    }
}
