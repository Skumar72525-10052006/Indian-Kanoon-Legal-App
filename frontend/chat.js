// Chat functionality
document.addEventListener('DOMContentLoaded', () => {
    initChat();
});

let currentChatSession = null;
let chatSessions = [];
let isTyping = false;

// Initialize chat functionality
function initChat() {
    // Get DOM elements
    const chatToggle = document.getElementById('chatToggle');
    const chatDrawer = document.getElementById('chatbotDrawer');
    const chatOverlay = document.getElementById('chatbotOverlay');
    const chatCloseBtn = document.getElementById('chatCloseBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const chatBackBtn = document.getElementById('chatBackBtn');
    const chatInput = document.getElementById('chatInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const attachCaseBtn = document.getElementById('attachCaseBtn');

    // Add event listeners
    chatToggle?.addEventListener('click', toggleChatDrawer);
    chatOverlay?.addEventListener('click', closeChatDrawer);
    chatCloseBtn?.addEventListener('click', closeChatDrawer);
    newChatBtn?.addEventListener('click', startNewChat);
    chatBackBtn?.addEventListener('click', goBackToSidebar);
    chatInput?.addEventListener('input', handleInputChange);
    chatInput?.addEventListener('keydown', handleInputKeydown);
    sendMessageBtn?.addEventListener('click', sendMessage);
    attachCaseBtn?.addEventListener('click', handleAttachCase);

    // Load chat sessions if user is logged in
    if (typeof authToken !== 'undefined' && authToken) {
        loadChatSessions();
    }

    // Load saved active session
    const savedSessionId = localStorage.getItem('activeChatSessionId');
    if (savedSessionId) {
        currentChatSession = savedSessionId;
    }

    // Add authentication hooks
    setupChatAuthHooks();
}

// Authentication hooks
function setupChatAuthHooks() {
    // Hook into logout to clear chat session
    const originalHandleLogout = window.handleLogout;
    if (originalHandleLogout) {
        window.handleLogout = function() {
            clearChatSession();
            originalHandleLogout();
        };
    }
    
    // Hook into login to load sessions
    const originalUpdateUIForLoggedInUser = window.updateUIForLoggedInUser;
    if (originalUpdateUIForLoggedInUser) {
        window.updateUIForLoggedInUser = function() {
            originalUpdateUIForLoggedInUser();
            loadChatSessions();
        };
    }
}

// Chat drawer management
function toggleChatDrawer() {
    const chatDrawer = document.getElementById('chatbotDrawer');
    
    // Check if user is authenticated
    if (!authToken) {
        showNotification('Please log in to use the AI assistant', 'info');
        openModal('loginModal');
        return;
    }
    
    chatDrawer.classList.toggle('active');
    
    if (chatDrawer.classList.contains('active')) {
        loadChatSessions();
    }
}

function closeChatDrawer() {
    const chatDrawer = document.getElementById('chatbotDrawer');
    chatDrawer.classList.remove('active');
}

// Chat session management
async function loadChatSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            chatSessions = await response.json();
            renderChatSessions();
        } else if (response.status === 401) {
            handleTokenExpiry();
        } else {
            console.error('Failed to load chat sessions:', response.status);
        }
    } catch (error) {
        console.error('Error loading chat sessions:', error);
        showNotification('Failed to load chat sessions', 'error');
    }
}

function renderChatSessions() {
    const sessionsList = document.getElementById('chatSessionsList');
    
    if (!sessionsList) return;
    
    if (chatSessions.length === 0) {
        sessionsList.innerHTML = `
            <div class="chat-empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <p>No conversations yet</p>
                <span>Start a new chat to begin</span>
            </div>
        `;
        return;
    }
    
    sessionsList.innerHTML = chatSessions.map(session => `
        <div class="chat-session-item ${session.id === currentChatSession ? 'active' : ''}" 
             data-session-id="${session.id}">
            <div class="chat-session-title">${escapeHtml(session.title || 'New Chat')}</div>
            <div class="chat-session-preview">${escapeHtml(session.last_message || 'No messages yet')}</div>
            <div class="chat-session-time">${formatTime(session.updated_at)}</div>
        </div>
    `).join('');
    
    // Add click listeners to session items
    sessionsList.querySelectorAll('.chat-session-item').forEach(item => {
        item.addEventListener('click', () => {
            const sessionId = item.dataset.sessionId;
            selectChatSession(sessionId);
        });
    });
}

function selectChatSession(sessionId) {
    if (sessionId === currentChatSession) return;
    
    currentChatSession = sessionId;
    localStorage.setItem('activeChatSessionId', sessionId);
    
    // Update UI
    document.querySelectorAll('.chat-session-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-session-id="${sessionId}"]`)?.classList.add('active');
    
    // Load messages
    loadChatMessages(sessionId);
}

async function startNewChat() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: 'New Chat'
            })
        });

        if (response.ok) {
            const newSession = await response.json();
            chatSessions.unshift(newSession);
            currentChatSession = newSession.id;
            localStorage.setItem('activeChatSessionId', currentChatSession);
            
            renderChatSessions();
            loadChatMessages(currentChatSession);
            clearChatInput();
        } else if (response.status === 401) {
            handleTokenExpiry();
        } else {
            console.error('Failed to create new chat session');
        }
    } catch (error) {
        console.error('Error creating new chat session:', error);
        showNotification('Failed to start new chat', 'error');
    }
}

function goBackToSidebar() {
    const chatSidebar = document.getElementById('chatSidebar');
    chatSidebar.classList.remove('mobile-open');
}

// Message management
async function loadChatMessages(sessionId) {
    const chatMessages = document.getElementById('chatMessages');
    const chatWelcome = document.getElementById('chatWelcome');
    const chatLoading = document.getElementById('chatLoading');
    
    if (!chatMessages) return;
    
    try {
        chatLoading.style.display = 'flex';
        chatWelcome.style.display = 'none';
        chatMessages.innerHTML = '';
        
        const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const messages = await response.json();
            
            chatLoading.style.display = 'none';
            
            if (messages.length === 0) {
                chatWelcome.style.display = 'block';
                return;
            }
            
            chatWelcome.style.display = 'none';
            renderMessages(messages);
        } else if (response.status === 401) {
            handleTokenExpiry();
        } else {
            chatLoading.style.display = 'none';
            showNotification('Failed to load messages', 'error');
        }
    } catch (error) {
        chatLoading.style.display = 'none';
        console.error('Error loading messages:', error);
        showNotification('Failed to load messages', 'error');
    }
}

function renderMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    chatMessages.innerHTML = messages.map(message => {
        const messageClass = message.role === 'user' ? 'user' : 'assistant';
        const avatarClass = message.role === 'user' ? 'user' : 'assistant';
        const timeFormatted = formatTime(message.created_at);
        
        let referencePills = '';
        if (message.references && message.references.length > 0) {
            referencePills = `
                <div class="reference-pills">
                    ${message.references.map(ref => `
                        <a href="${ref.url}" target="_blank" class="reference-pill">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                <polyline points="15,3 21,3 21,9"/>
                                <line x1="10" y1="14" x2="21" y2="3"/>
                            </svg>
                            ${escapeHtml(ref.title)}
                        </a>
                    `).join('')}
                </div>
            `;
        }
        
        return `
            <div class="chat-message ${messageClass}">
                <div class="message-avatar ${avatarClass}">
                    ${message.role === 'user' ? 'U' : 'AI'}
                </div>
                <div class="message-content">
                    ${escapeHtml(message.content)}
                    ${referencePills}
                </div>
            </div>
            <div class="message-time">${timeFormatted}</div>
        `;
    }).join('');
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendMessageBtn');
    
    if (!chatInput || !currentChatSession) return;
    
    const message = chatInput.value.trim();
    if (!message) return;
    
    try {
        // Add optimistic UI
        const optimisticMessage = {
            id: `temp-${Date.now()}`,
            content: message,
            role: 'user',
            created_at: new Date().toISOString(),
            references: []
        };
        
        // Show loading state
        sendBtn.disabled = true;
        chatInput.disabled = true;
        showChatLoading();
        
        // Add user message to UI immediately
        addOptimisticMessage(optimisticMessage);
        clearChatInput();
        
        const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${currentChatSession}/message`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message
            })
        });

        if (response.ok) {
            const result = await response.json();
            
            // Remove optimistic message and add real messages
            removeOptimisticMessage(optimisticMessage.id);
            
            if (result.user_message) {
                addRealMessage(result.user_message);
            }
            
            if (result.assistant_message) {
                addRealMessage(result.assistant_message);
            }
            
            // Update session in sidebar
            updateChatSession(result.session);
            
        } else if (response.status === 401) {
            removeOptimisticMessage(optimisticMessage.id);
            handleTokenExpiry();
        } else {
            removeOptimisticMessage(optimisticMessage.id);
            const error = await response.json();
            showNotification(error.detail || 'Failed to send message', 'error');
        }
    } catch (error) {
        removeOptimisticMessage(optimisticMessage.id);
        console.error('Error sending message:', error);
        showNotification('Failed to send message', 'error');
    } finally {
        sendBtn.disabled = false;
        chatInput.disabled = false;
        hideChatLoading();
        chatInput.focus();
    }
}

function addOptimisticMessage(message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    chatMessages.insertAdjacentHTML('beforeend', `
        <div class="chat-message user" data-temp-id="${message.id}">
            <div class="message-avatar user">U</div>
            <div class="message-content">${escapeHtml(message.content)}</div>
        </div>
        <div class="message-time">${formatTime(message.created_at)}</div>
    `);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeOptimisticMessage(tempId) {
    const chatMessages = document.getElementById('chatMessages');
    const optimisticMessage = chatMessages.querySelector(`[data-temp-id="${tempId}"]`);
    
    if (optimisticMessage) {
        optimisticMessage.parentNode.remove();
        const timeElement = optimisticMessage.nextElementSibling;
        if (timeElement && timeElement.classList.contains('message-time')) {
            timeElement.remove();
        }
    }
}

function addRealMessage(message) {
    const messageClass = message.role === 'user' ? 'user' : 'assistant';
    const avatarClass = message.role === 'user' ? 'user' : 'assistant';
    const timeFormatted = formatTime(message.created_at);
    
    let referencePills = '';
    if (message.references && message.references.length > 0) {
        referencePills = `
            <div class="reference-pills">
                ${message.references.map(ref => `
                    <a href="${ref.url}" target="_blank" class="reference-pill">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15,3 21,3 21,9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        ${escapeHtml(ref.title)}
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    chatMessages.insertAdjacentHTML('beforeend', `
        <div class="chat-message ${messageClass}">
            <div class="message-avatar ${avatarClass}">
                ${message.role === 'user' ? 'U' : 'AI'}
            </div>
            <div class="message-content">
                ${escapeHtml(message.content)}
                ${referencePills}
            </div>
        </div>
        <div class="message-time">${timeFormatted}</div>
    `);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Utility functions
function handleInputChange(e) {
    const sendBtn = document.getElementById('sendMessageBtn');
    const chatInput = e.target;
    
    // Auto-resize textarea
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    
    // Enable/disable send button
    sendBtn.disabled = !chatInput.value.trim();
}

function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function clearChatInput() {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = '';
        chatInput.style.height = 'auto';
        document.getElementById('sendMessageBtn').disabled = true;
    }
}

function showChatLoading() {
    const chatLoading = document.getElementById('chatLoading');
    const chatWelcome = document.getElementById('chatWelcome');
    
    if (chatWelcome) chatWelcome.style.display = 'none';
    if (chatLoading) chatLoading.style.display = 'flex';
    
    isTyping = true;
}

function hideChatLoading() {
    const chatLoading = document.getElementById('chatLoading');
    if (chatLoading) chatLoading.style.display = 'none';
    
    isTyping = false;
}

// Case attachment functionality
function handleAttachCase() {
    // This will be implemented to attach cases from search results
    showNotification('Attach case functionality coming soon', 'info');
}

// Search integration
function startChatWithCase(docId, query, title) {
    // Check if chat drawer is open, if not open it
    const chatDrawer = document.getElementById('chatbotDrawer');
    if (!chatDrawer.classList.contains('active')) {
        toggleChatDrawer();
    }
    
    // If we have a case to attach, start a new chat with context
    if (docId) {
        startNewChatWithCase(docId, query, title);
    }
}

async function startNewChatWithCase(docId, query, title) {
    try {
        await startNewChat();
        
        // Add system message with case context
        const systemMessage = `I'm interested in understanding this legal case: "${title}". Query: "${query}". Please provide an analysis.`;
        
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = systemMessage;
            handleInputChange({ target: chatInput });
            sendMessage();
        }
    } catch (error) {
        console.error('Error starting chat with case:', error);
        showNotification('Failed to start case-specific chat', 'error');
    }
}

// Update session in sidebar
function updateChatSession(updatedSession) {
    const sessionIndex = chatSessions.findIndex(s => s.id === updatedSession.id);
    if (sessionIndex >= 0) {
        chatSessions[sessionIndex] = updatedSession;
    } else {
        chatSessions.unshift(updatedSession);
    }
    renderChatSessions();
}

// Token expiry handling
function handleTokenExpiry() {
    clearChatSession();
    showNotification('Session expired. Please log in again.', 'error');
    
    // Trigger logout
    if (window.handleLogout) {
        window.handleLogout();
    }
}

function clearChatSession() {
    currentChatSession = null;
    localStorage.removeItem('activeChatSessionId');
    
    // Clear chat UI
    const chatMessages = document.getElementById('chatMessages');
    const chatWelcome = document.getElementById('chatWelcome');
    const chatLoading = document.getElementById('chatLoading');
    
    if (chatMessages) chatMessages.innerHTML = '';
    if (chatWelcome) chatWelcome.style.display = 'block';
    if (chatLoading) chatLoading.style.display = 'none';
}

// Format time utility
function formatTime(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Use the existing notification system from auth.js
    if (window.showToast) {
        window.showToast(message, type);
    } else {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Export functions for use in other scripts
window.ChatAPI = {
    startChatWithCase,
    toggleChatDrawer
};