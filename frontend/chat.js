// Chat-specific JavaScript
// API_BASE_URL and USER_ID are defined in script.js

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
});

function initializeChat() {
    // Auto-resize textarea
    const textarea = document.getElementById('message-input');
    textarea.addEventListener('input', autoResizeTextarea);

    // Focus on input
    textarea.focus();

    // Load user name
    document.getElementById('user-name').textContent = 'Kofi'; // You can load this from API
}

function setupEventListeners() {
    const textarea = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');

    // Handle Enter key (send message) and Shift+Enter (new line)
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Enable/disable send button based on input
    textarea.addEventListener('input', function() {
        const hasText = textarea.value.trim().length > 0;
        sendBtn.disabled = !hasText;
    });

    // Initialize send button state
    sendBtn.disabled = true;
}

function autoResizeTextarea() {
    const textarea = document.getElementById('message-input');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

async function sendMessage() {
    console.log('sendMessage called'); // Debug log

    const textarea = document.getElementById('message-input');
    const message = textarea.value.trim();

    console.log('Message:', message); // Debug log

    if (!message) {
        console.log('No message to send');
        return;
    }

    // Clear input and reset height
    textarea.value = '';
    textarea.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;

    // Add user message to chat
    console.log('Adding user message to chat');
    addMessage(message, 'user');

    // Show typing indicator
    showTypingIndicator();

    // Get include context setting
    const includeContext = document.getElementById('include-context').checked;
    console.log('Include context:', includeContext);

    try {
        console.log('Sending request to API...');

        const requestBody = {
            user_id: USER_ID,
            question: message,
            include_user_context: includeContext
        };

        console.log('Request body:', requestBody);
        console.log('API URL:', `${API_BASE_URL}/knowledge-agent/ask`);

        const response = await fetch(`${API_BASE_URL}/knowledge-agent/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response data:', data);

        // Hide typing indicator
        hideTypingIndicator();

        // Add AI response
        if (data.answer) {
            addMessage(data.answer, 'agent');
        } else {
            addMessage('Sorry, I could not process your question right now. Please try again.', 'agent');
        }

    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();

        // More detailed error message
        let errorMessage = 'Sorry, I\'m having trouble connecting right now. ';

        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage += 'Please make sure the CardioMed AI server is running on http://localhost:8000';
        } else if (error.message.includes('CORS')) {
            errorMessage += 'There\'s a CORS issue. Please serve the files through a web server.';
        } else {
            errorMessage += `Error: ${error.message}`;
        }

        addMessage(errorMessage, 'agent');
    }

    // Focus back on input
    textarea.focus();
}

function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const avatarIcon = sender === 'user' ? 'fas fa-user' : 'fas fa-graduation-cap';

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="${avatarIcon}"></i>
        </div>
        <div class="message-content">
            <div class="message-text">
                ${formatMessageText(text)}
            </div>
            <div class="message-time">${currentTime}</div>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Hide quick questions after first user message
    if (sender === 'user') {
        hideQuickQuestions();
    }
}

function formatMessageText(text) {
    // Convert line breaks to <br> tags
    text = text.replace(/\n/g, '<br>');

    // Convert **bold** to <strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert *italic* to <em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Convert numbered lists
    text = text.replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>');
    if (text.includes('<li>')) {
        text = text.replace(/(<li>.*<\/li>)/s, '<ol>$1</ol>');
    }

    // Convert bullet points
    text = text.replace(/^[-•]\s(.+)$/gm, '<li>$1</li>');
    if (text.includes('<li>') && !text.includes('<ol>')) {
        text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }

    return text;
}

function showTypingIndicator() {
    document.getElementById('typing-indicator').classList.add('show');
}

function hideTypingIndicator() {
    document.getElementById('typing-indicator').classList.remove('show');
}

function askQuickQuestion(question) {
    const textarea = document.getElementById('message-input');
    textarea.value = question;
    autoResizeTextarea();
    document.getElementById('send-btn').disabled = false;
    textarea.focus();

    // Optionally auto-send the question
    setTimeout(() => {
        sendMessage();
    }, 500);
}

function toggleQuickQuestions() {
    const quickQuestions = document.getElementById('quick-questions');
    quickQuestions.classList.toggle('collapsed');
}

function hideQuickQuestions() {
    const quickQuestions = document.getElementById('quick-questions');
    if (!quickQuestions.classList.contains('collapsed')) {
        quickQuestions.classList.add('collapsed');
    }
}

function clearChat() {
    const messagesContainer = document.getElementById('chat-messages');

    // Keep only the welcome message
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    messagesContainer.innerHTML = '';
    if (welcomeMessage) {
        messagesContainer.appendChild(welcomeMessage);
    }

    // Show quick questions again
    const quickQuestions = document.getElementById('quick-questions');
    quickQuestions.classList.remove('collapsed');

    // Focus on input
    document.getElementById('message-input').focus();
}

function toggleUserContext() {
    const checkbox = document.getElementById('include-context');
    const button = document.getElementById('context-btn');

    checkbox.checked = !checkbox.checked;

    if (checkbox.checked) {
        button.classList.add('active');
        button.title = 'Including Your Data';
    } else {
        button.classList.remove('active');
        button.title = 'Include My Data';
    }
}

function goHome() {
    window.location.href = 'index.html';
}

// Handle context checkbox change
document.addEventListener('DOMContentLoaded', function() {
    const checkbox = document.getElementById('include-context');
    const button = document.getElementById('context-btn');

    checkbox.addEventListener('change', function() {
        if (this.checked) {
            button.classList.add('active');
            button.title = 'Including Your Data';
        } else {
            button.classList.remove('active');
            button.title = 'Include My Data';
        }
    });
});

// Add some sample conversation starters
const conversationStarters = [
    "What are the different stages of hypertension?",
    "How can I lower my blood pressure naturally?",
    "What foods should I eat for better heart health?",
    "When should I take my blood pressure medication?",
    "How often should I check my blood pressure?",
    "What are the warning signs of a hypertensive crisis?"
];

// Function to add a conversation starter (can be called from UI)
function addConversationStarter() {
    const randomStarter = conversationStarters[Math.floor(Math.random() * conversationStarters.length)];
    document.getElementById('message-input').value = randomStarter;
    autoResizeTextarea();
    document.getElementById('send-btn').disabled = false;
}

// Test function to check if basic functionality works
function testChat() {
    console.log('Testing chat functionality...');
    addMessage('This is a test user message', 'user');
    setTimeout(() => {
        addMessage('This is a test agent response', 'agent');
    }, 1000);
}

// Add test button to page (for debugging)
function addTestButton() {
    const testBtn = document.createElement('button');
    testBtn.textContent = 'Test Chat';
    testBtn.onclick = testChat;
    testBtn.style.position = 'fixed';
    testBtn.style.top = '10px';
    testBtn.style.right = '10px';
    testBtn.style.zIndex = '9999';
    testBtn.style.background = '#e74c3c';
    testBtn.style.color = 'white';
    testBtn.style.border = 'none';
    testBtn.style.padding = '10px';
    testBtn.style.borderRadius = '5px';
    document.body.appendChild(testBtn);
}

// Call this in console if needed: addTestButton()
