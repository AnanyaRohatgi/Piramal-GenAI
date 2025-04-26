const chatBox = document.getElementById('chat-box');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

// Add a message to the chat
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `px-message ${sender}`;

    // Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'px-avatar';
    avatarDiv.textContent = sender === 'user' ? 'You' : 'AI';

    // Bubble
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'px-bubble';
    bubbleDiv.innerHTML = text;  // Use innerHTML to render formatted text

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bubbleDiv);

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Handle form submission (Send button)
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = userInput.value.trim();
    if (!question) return;

    addMessage(question, 'user');
    userInput.value = '';
    addMessage('Thinking...', 'bot');

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        const data = await response.json();

        // Remove the "Thinking..." message
        const thinkingMsg = chatBox.querySelector('.px-message.bot:last-child');
        if (thinkingMsg && thinkingMsg.querySelector('.px-bubble').textContent === 'Thinking...') {
            chatBox.removeChild(thinkingMsg);
        }

        if (data.success) {
            addMessage(formatResponse(data.answer), 'bot'); // Format the response before displaying
        } else {
            addMessage(data.error || 'Sorry, something went wrong.', 'bot');
        }
    } catch (err) {
        addMessage('Network error. Please try again.', 'bot');
    }
});

// Submit on Enter, new line on Shift+Enter
userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.requestSubmit();
    }
});

// --- Document search functionality ---

const docsSearch = document.getElementById('docs-search');
const docsList = document.querySelector('.docs-list');
const docItems = docsList.querySelectorAll('li');

docsSearch.addEventListener('input', function() {
    const query = this.value.toLowerCase();
    docItems.forEach(li => {
        if (li.textContent.toLowerCase().includes(query)) {
            li.style.display = '';
        } else {
            li.style.display = 'none';
        }
    });
});

// --- Optional: Open document on li click if data-url is present ---
docItems.forEach(li => {
    const url = li.getAttribute('data-url');
    if (url) {
        li.style.cursor = 'pointer';
        li.addEventListener('click', function() {
            window.open(url, '_blank');
        });
    }
});

// Function to format the response
function formatResponse(response) {
    // Regex to find numbered points (e.g., "1.", "2.", etc.)
    const formatted = response.replace(/(\d+\.\s*)/g, '<br><b>$1</b>');
    return formatted;
}
