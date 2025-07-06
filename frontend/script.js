// API Base URL
const API_BASE_URL = 'https://cardiomedai-api.onrender.com';
const USER_ID = 1; // Default user ID for demo

// Initialize the dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only run dashboard functions if we're on the homepage
    if (document.getElementById('systolic')) {
        loadLatestReading();
        getDailyInsight();
        loadWeeklySummary();
    }
});

// Load the latest blood pressure reading
async function loadLatestReading() {
    try {
        const response = await fetch(`${API_BASE_URL}/bp/readings/${USER_ID}`);
        const readings = await response.json();

        if (readings && readings.length > 0) {
            const latest = readings[0]; // Assuming readings are sorted by date desc

            // Update BP display
            document.getElementById('systolic').textContent = latest.systolic;
            document.getElementById('diastolic').textContent = latest.diastolic;
            document.getElementById('pulse').textContent = `${latest.pulse} BPM`;

            // Update status based on reading
            const status = getBPStatus(latest.systolic, latest.diastolic);
            const statusElement = document.getElementById('bp-status');
            statusElement.textContent = status.text;
            statusElement.className = `bp-status ${status.class}`;

            // Update timestamp
            const timestamp = new Date(latest.reading_time).toLocaleString();
            document.getElementById('last-reading-time').textContent = timestamp;
        }
    } catch (error) {
        console.error('Error loading latest reading:', error);
        // Show placeholder data if API fails
        showPlaceholderData();
    }
}

// Get daily insight from Health Advisor
async function getDailyInsight() {
    const insightElement = document.getElementById('daily-insight');

    // Check if element exists (only on homepage)
    if (!insightElement) return;

    try {
        // Show loading state
        insightElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting your daily insight...';

        const response = await fetch(`${API_BASE_URL}/health-advisor/advice/${USER_ID}`, {
            method: 'GET'
        });

        const data = await response.json();

        if (data && data.advisor_response) {
            insightElement.innerHTML = `<i class="fas fa-user-md"></i> ${data.advisor_response}`;
        } else {
            insightElement.innerHTML = '<i class="fas fa-info-circle"></i> Great job staying on top of your health! Keep monitoring your blood pressure regularly.';
        }
    } catch (error) {
        console.error('Error getting daily insight:', error);
        if (insightElement) {
            insightElement.innerHTML = '<i class="fas fa-info-circle"></i> Great job staying on top of your health! Keep monitoring your blood pressure regularly.';
        }
    }
}

// Load weekly summary statistics
async function loadWeeklySummary() {
    try {
        const response = await fetch(`${API_BASE_URL}/bp/readings/stats/${USER_ID}`);
        const stats = await response.json();

        if (stats) {
            document.getElementById('readings-count').textContent = stats.total_readings || '16';
            document.getElementById('avg-systolic').textContent = Math.round(stats.avg_systolic) || '125';
            document.getElementById('avg-diastolic').textContent = Math.round(stats.avg_diastolic) || '82';

            // Simple trend calculation (you can enhance this)
            const trend = stats.avg_systolic < 130 ? '↓' : stats.avg_systolic > 140 ? '↑' : '→';
            const trendElement = document.getElementById('trend');
            trendElement.textContent = trend;
            trendElement.className = `stat-number ${trend === '↓' ? 'good' : ''}`;
        }
    } catch (error) {
        console.error('Error loading weekly summary:', error);
        // Keep placeholder data if API fails
    }
}

// Determine BP status based on readings
function getBPStatus(systolic, diastolic) {
    if (systolic < 120 && diastolic < 80) {
        return { text: 'Normal', class: 'normal' };
    } else if (systolic >= 120 && systolic <= 129 && diastolic < 80) {
        return { text: 'Elevated', class: 'elevated' };
    } else if ((systolic >= 130 && systolic <= 139) || (diastolic >= 80 && diastolic <= 89)) {
        return { text: 'Stage 1 High', class: 'high' };
    } else if (systolic >= 140 || diastolic >= 90) {
        return { text: 'Stage 2 High', class: 'high' };
    } else {
        return { text: 'Check Reading', class: 'elevated' };
    }
}

// Show placeholder data when API is not available
function showPlaceholderData() {
    const systolic = document.getElementById('systolic');
    const diastolic = document.getElementById('diastolic');
    const pulse = document.getElementById('pulse');
    const bpStatus = document.getElementById('bp-status');
    const lastReadingTime = document.getElementById('last-reading-time');

    if (systolic) systolic.textContent = '123';
    if (diastolic) diastolic.textContent = '80';
    if (pulse) pulse.textContent = '72 BPM';
    if (bpStatus) {
        bpStatus.textContent = 'Normal';
        bpStatus.className = 'bp-status normal';
    }
    if (lastReadingTime) lastReadingTime.textContent = 'Today, 8:30 AM';
}

// Action functions for quick action cards
function addReading() {
    // Navigate to add reading page
    window.location.href = 'add-reading.html';
}

function scanDevice() {
    // Navigate to camera/OCR page
    alert('Scan Device functionality - Open camera for OCR');
    // In a real app, you might navigate to: window.location.href = '/scan-device.html';
}

function uploadBPImage() {
    // Create file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.style.display = 'none';

    fileInput.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Show loading modal
        showUploadModal(file);
    };

    // Trigger file selection
    document.body.appendChild(fileInput);
    fileInput.click();
    document.body.removeChild(fileInput);
}

function viewHistory() {
    // Navigate to history page
    window.location.href = 'history.html';
}

function askAI() {
    // Navigate to dedicated chat page
    window.location.href = 'chat.html';
}

// Show AI Knowledge Agent modal
function showAIModal() {
    const modal = document.createElement('div');
    modal.className = 'ai-modal';
    modal.innerHTML = `
        <div class="ai-modal-content">
            <div class="ai-modal-header">
                <h3><i class="fas fa-robot"></i> Ask CardioMed AI</h3>
                <button onclick="closeAIModal()" class="close-btn">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="ai-modal-body">
                <div class="ai-chat-area" id="ai-chat-area">
                    <div class="ai-message">
                        <i class="fas fa-robot"></i>
                        <span>Hi! I'm your CardioMed AI assistant. Ask me anything about hypertension, blood pressure management, or your health data!</span>
                    </div>
                </div>
                <div class="ai-input-area">
                    <input type="text" id="ai-question" placeholder="Ask about blood pressure, medications, lifestyle..." />
                    <button onclick="askAIQuestion()" class="ask-btn">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Add modal styles
    const style = document.createElement('style');
    style.textContent = `
        .ai-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .ai-modal-content {
            background: white;
            border-radius: 20px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow: hidden;
        }
        .ai-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .ai-modal-body {
            padding: 20px;
        }
        .ai-chat-area {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .ai-message {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 15px;
        }
        .ai-message i {
            color: #667eea;
            margin-top: 3px;
        }
        .ai-input-area {
            display: flex;
            gap: 10px;
        }
        .ai-input-area input {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 25px;
            outline: none;
        }
        .ask-btn {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            width: 45px;
            height: 45px;
            cursor: pointer;
        }
        .close-btn {
            background: none;
            border: none;
            font-size: 1.2rem;
            cursor: pointer;
            color: #999;
        }
    `;
    document.head.appendChild(style);

    // Focus on input
    document.getElementById('ai-question').focus();

    // Allow Enter key to submit
    document.getElementById('ai-question').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            askAIQuestion();
        }
    });
}

// Close AI modal
function closeAIModal() {
    const modal = document.querySelector('.ai-modal');
    if (modal) {
        modal.remove();
    }
}

// Ask AI a question
async function askAIQuestion() {
    const questionInput = document.getElementById('ai-question');
    const question = questionInput.value.trim();

    if (!question) return;

    const chatArea = document.getElementById('ai-chat-area');

    // Add user message
    const userMessage = document.createElement('div');
    userMessage.className = 'ai-message user-message';
    userMessage.innerHTML = `
        <i class="fas fa-user"></i>
        <span>${question}</span>
    `;
    chatArea.appendChild(userMessage);

    // Clear input
    questionInput.value = '';

    // Add loading message
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'ai-message loading-message';
    loadingMessage.innerHTML = `
        <i class="fas fa-robot"></i>
        <span><i class="fas fa-spinner fa-spin"></i> Thinking...</span>
    `;
    chatArea.appendChild(loadingMessage);

    // Scroll to bottom
    chatArea.scrollTop = chatArea.scrollHeight;

    try {
        const response = await fetch(`${API_BASE_URL}/knowledge-agent/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: USER_ID,
                question: question,
                include_user_context: true
            })
        });

        const data = await response.json();

        // Remove loading message
        loadingMessage.remove();

        // Add AI response
        const aiMessage = document.createElement('div');
        aiMessage.className = 'ai-message';
        aiMessage.innerHTML = `
            <i class="fas fa-robot"></i>
            <span>${data.answer || 'Sorry, I could not process your question right now.'}</span>
        `;
        chatArea.appendChild(aiMessage);

    } catch (error) {
        console.error('Error asking AI:', error);

        // Remove loading message
        loadingMessage.remove();

        // Add error message
        const errorMessage = document.createElement('div');
        errorMessage.className = 'ai-message';
        errorMessage.innerHTML = `
            <i class="fas fa-robot"></i>
            <span>Sorry, I'm having trouble connecting right now. Please try again later.</span>
        `;
        chatArea.appendChild(errorMessage);
    }

    // Scroll to bottom
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Show upload modal for BP image OCR
function showUploadModal(file) {
    const modal = document.createElement('div');
    modal.className = 'upload-modal';
    modal.innerHTML = `
        <div class="upload-modal-content">
            <div class="upload-modal-header">
                <h3><i class="fas fa-upload"></i> Upload BP Monitor Image</h3>
                <button onclick="closeUploadModal()" class="close-btn">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="upload-modal-body">
                <div class="image-preview">
                    <img id="preview-image" src="" alt="BP Monitor Preview" />
                </div>
                <div class="upload-info">
                    <p><strong>File:</strong> ${file.name}</p>
                    <p><strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div class="form-group">
                    <label for="upload-notes">
                        <i class="fas fa-sticky-note"></i> Notes
                    </label>
                    <textarea id="upload-notes" rows="3"
                              placeholder="Add any notes about this reading (optional)"></textarea>
                </div>
                <div class="upload-status" id="upload-status">
                    <i class="fas fa-info-circle"></i>
                    Ready to process image with OCR
                </div>
                <div class="upload-actions" id="upload-actions">
                    <button onclick="closeUploadModal()" class="cancel-btn">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                    <button onclick="processOCR()" class="process-btn" id="process-btn">
                        <i class="fas fa-magic"></i> Process with OCR
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Add modal styles
    const style = document.createElement('style');
    style.textContent = `
        .upload-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .upload-modal-content {
            background: white;
            border-radius: 20px;
            width: 90%;
            max-width: 500px;
            max-height: 85vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        .upload-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #eee;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        .upload-modal-body {
            padding: 20px;
            flex: 1;
            overflow-y: auto;
        }
        .image-preview {
            text-align: center;
            margin-bottom: 20px;
            border: 2px dashed #ddd;
            border-radius: 10px;
            padding: 20px;
        }
        .image-preview img {
            max-width: 100%;
            max-height: 200px;
            border-radius: 10px;
        }
        .upload-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .upload-info p {
            margin: 5px 0;
            color: #555;
        }
        .upload-status {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            background: #e8f4fd;
            color: #2c3e50;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .upload-status.processing {
            background: #fef9e7;
            color: #f39c12;
        }
        .upload-status.success {
            background: #d5f4e6;
            color: #27ae60;
        }
        .upload-status.error {
            background: #fadbd8;
            color: #e74c3c;
        }
        .upload-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
            background: white;
            position: sticky;
            bottom: 0;
        }
        .upload-actions button {
            padding: 12px 20px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cancel-btn {
            background: #95a5a6;
            color: white;
        }
        .process-btn {
            background: #667eea;
            color: white;
        }
        .process-btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
        }
        .success-btn {
            background: #27ae60 !important;
            animation: pulse-success 2s infinite;
        }
        .save-btn {
            background: #27ae60 !important;
            animation: pulse-success 2s infinite;
        }
        .save-btn:hover {
            background: #229954 !important;
            transform: scale(1.05);
        }
        @keyframes pulse-success {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .close-btn {
            background: none;
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
        }
    `;
    document.head.appendChild(style);

    // Show image preview
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('preview-image').src = e.target.result;
    };
    reader.readAsDataURL(file);

    // Store file for processing
    window.currentUploadFile = file;
}

// Close upload modal
function closeUploadModal() {
    const modal = document.querySelector('.upload-modal');
    if (modal) {
        modal.remove();
    }
    window.currentUploadFile = null;
}



// Process OCR on uploaded image
async function processOCR() {
    const file = window.currentUploadFile;
    if (!file) return;

    const statusElement = document.getElementById('upload-status');
    const processBtn = document.getElementById('process-btn');

    try {
        // Update UI to show processing
        statusElement.className = 'upload-status processing';
        statusElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing image with OCR...';
        processBtn.disabled = true;

        // Create FormData for file upload
        const formData = new FormData();
        formData.append('user_id', USER_ID);
        formData.append('image', file);
        // Get notes from textarea
        const notes = document.getElementById('upload-notes').value;
        formData.append('notes', notes || `Uploaded via web interface - ${file.name}`);

        // Send to OCR preview endpoint (doesn't save to database)
        const response = await fetch(`${API_BASE_URL}/bp/ocr-preview/`, {
            method: 'POST',
            body: formData // Don't set Content-Type header, let browser set it with boundary
        });

        const data = await response.json();

        if (response.ok && data.systolic && data.diastolic) {
            // Success - show extracted data for user approval
            statusElement.className = 'upload-status success';
            statusElement.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <strong>OCR Success!</strong><br>
                <p style="margin: 8px 0; color: #2c3e50; font-size: 0.9em;">Please review before saving:</p>
                <div style="margin: 10px 0; font-size: 1em; background: #f8f9fa; padding: 12px; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <strong>Systolic:</strong> <span style="color: #e74c3c; font-weight: bold;">${data.systolic} mmHg</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <strong>Diastolic:</strong> <span style="color: #3498db; font-weight: bold;">${data.diastolic} mmHg</span>
                    </div>
                    ${data.pulse ? `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <strong>Pulse:</strong> <span style="color: #f39c12; font-weight: bold;">${data.pulse} BPM</span>
                    </div>
                    ` : ''}
                    <div style="display: flex; justify-content: space-between;">
                        <strong>Status:</strong> <span style="color: #27ae60; font-weight: bold;">${data.interpretation || 'Processed'}</span>
                    </div>
                </div>
                <p style="margin: 8px 0; font-size: 0.85em; color: #7f8c8d;">
                    <i class="fas fa-info-circle"></i> Verify numbers before saving.
                </p>
            `;

            // Replace the Process button with approval buttons
            const actionsContainer = document.getElementById('upload-actions');
            console.log('Actions container found:', actionsContainer);

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button onclick="cancelOCR()" class="cancel-btn">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                    <button onclick="saveOCRReading()" class="save-btn" id="save-btn">
                        <i class="fas fa-save"></i> Save Reading
                    </button>
                `;
                console.log('Buttons replaced successfully');
            } else {
                console.error('Upload actions container not found!');
                // Fallback: try to find by class
                const fallbackContainer = document.querySelector('.upload-actions');
                if (fallbackContainer) {
                    fallbackContainer.innerHTML = `
                        <button onclick="cancelOCR()" class="cancel-btn">
                            <i class="fas fa-times"></i> Cancel
                        </button>
                        <button onclick="saveOCRReading()" class="save-btn" id="save-btn">
                            <i class="fas fa-save"></i> Save Reading
                        </button>
                    `;
                    console.log('Buttons replaced using fallback method');
                }
            }

            // Store the OCR data for saving later
            window.pendingOCRData = data;
            console.log('OCR data stored:', data);

        } else {
            // Error
            statusElement.className = 'upload-status error';
            statusElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> OCR failed: ${data.detail || 'Could not extract BP readings from image'}`;
            processBtn.disabled = false;
        }

    } catch (error) {
        console.error('OCR processing error:', error);
        statusElement.className = 'upload-status error';
        statusElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`;
        processBtn.disabled = false;
    }
}

// OCR Approval Functions
function cancelOCR() {
    // Clear pending data and close modal
    window.pendingOCRData = null;
    closeUploadModal();
}

async function saveOCRReading() {
    const data = window.pendingOCRData;
    if (!data) {
        alert('No OCR data to save');
        return;
    }

    const saveBtn = document.getElementById('save-btn');
    const originalContent = saveBtn.innerHTML;

    try {
        // Show saving state
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        saveBtn.disabled = true;

        // Save the approved OCR data to database
        const response = await fetch(`${API_BASE_URL}/bp/save-ocr/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const savedData = await response.json();

            // Close the modal
            closeUploadModal();

            // Refresh the homepage
            if (document.getElementById('systolic')) {
                loadLatestReading();
            }

            // Show success notification
            setTimeout(() => {
                alert(`✅ Blood Pressure Reading Saved Successfully!\n\nSystolic: ${savedData.systolic} mmHg\nDiastolic: ${savedData.diastolic} mmHg${savedData.pulse ? `\nPulse: ${savedData.pulse} BPM` : ''}\nStatus: ${savedData.interpretation || 'Processed'}\n\nCheck your dashboard for the updated reading!`);
            }, 500);

            // Clear pending data
            window.pendingOCRData = null;
        } else {
            throw new Error(`Failed to save reading: ${response.status}`);
        }

    } catch (error) {
        console.error('Error saving OCR reading:', error);
        saveBtn.innerHTML = originalContent;
        saveBtn.disabled = false;
        alert('Error saving reading. Please try again.');
    }
}

// OCR Upload functionality complete - using FormData for proper file upload
