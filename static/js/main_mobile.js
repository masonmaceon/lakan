/**
 * Main Mobile Application Controller
 * Handles initialization and coordination of all mobile app features
 */

console.log('🚀 Starting Mobile Campus Navigation...');

// Global state
let mapController = null;
let navigationEngine = null;
let isInitialized = false;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('📱 DOM loaded, initializing mobile app...');
        
        // Initialize map controller
        mapController = new CampusMapController('map');
        await mapController.initialize();
        
        // Initialize navigation engine
        navigationEngine = new CampusNavigationEngine();
        await navigationEngine.initialize();
        
        // Setup chatbot
        setupChatbot();
        
        // Setup chatbot toggle
        setupChatbotToggle();
        
        // Hide loading overlay
        hideLoadingOverlay();
        
        isInitialized = true;
        console.log('✅ Mobile app initialized successfully!');
        
    } catch (error) {
        console.error('❌ Initialization failed:', error);
        hideLoadingOverlay();
        addMessage('bot', 'Sorry, there was an error loading the navigation system. Please refresh the page.');
    }
});

/**
 * Setup chatbot functionality
 */
function setupChatbot() {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    
    // Send message on button click
    sendBtn.addEventListener('click', () => {
        sendMessage();
    });
    
    // Send message on Enter key
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

/**
 * Setup chatbot toggle (minimize/maximize)
 */
function setupChatbotToggle() {
    const chatToggle = document.getElementById('chatToggle');
    const chatbotContainer = document.getElementById('chatbotContainer');
    
    if (chatToggle && chatbotContainer) {
        chatToggle.addEventListener('click', () => {
            chatbotContainer.classList.toggle('minimized');
            // Force map to recalculate size
            setTimeout(() => {
                if (window.map) window.map.invalidateSize();
            }, 350);
        });
    }
}

/**
 * Send user message
 */
async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessage('user', message);
    userInput.value = '';
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        // Send to chatbot API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        // Add bot response
        addMessage('bot', data.response || 'Sorry, I couldn\'t understand that.');
        
        // If there's a destination, show navigation
        if (data.destination) {
            showNavigation(data.start || 'Gate 1', data.destination);
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator(typingId);
        addMessage('bot', 'Sorry, there was an error processing your message.');
    }
}

/**
 * Add message to chat
 */
function addMessage(type, text) {
    const chatMessages = document.getElementById('chatMessages') || document.getElementById('chat-messages');
    if (!chatMessages) return;    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = type === 'bot' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    if (type === 'bot') { content.innerHTML = text; } else { content.textContent = text; }    
    if (type === 'user') {
        messageDiv.appendChild(content);
        messageDiv.appendChild(avatar);
    } else {
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Add typing indicator
 */
function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages') || document.getElementById('chat-messages');
    if (!chatMessages) return null;
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.id = 'typing-' + Date.now();
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = '<i class="fas fa-ellipsis-h"></i>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return typingDiv.id;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

function showNavigation(start, destination) {
    console.log(`📍 Navigation: ${start} → ${destination}`);
    
    if (!navigationEngine || !mapController) {
        console.error('Navigation engine or map controller not initialized');
        return;
    }
    
    try {
        // Check if admin mode is enabled and use custom location
        let actualStart = start;
        
        if (window.adminMode && window.adminMode.enabled && window.adminMode.customLocation) {
            // Find the nearest pathway node to the admin location
            const customLoc = window.adminMode.customLocation;
            const result = navigationEngine.findNearestNode([customLoc.lat, customLoc.lng]);  // ← Array!
            
            if (result && result.nodeId) {  // ← Check for nodeId
                actualStart = result.nodeId;  // ← Use nodeId
                console.log(`🔧 Using nearest pathway node: ${result.nodeId}`);
            } else {
                console.log('⚠️ Could not find nearest node, using default start');
            }
        }
        
        // Clear previous route
        mapController.clearRoute();
        
        // Find route using navigation engine
        const route = navigationEngine.findShortestPath(actualStart, destination);
        
        if (route && route.coordinates) {
            // Show route on map
            mapController.drawRoute(route);
            mapController.addStartEndMarkers(route);
            mapController.fitToRoute(route);
            const cancelBtn = document.getElementById('cancelNavBtn');
            if (cancelBtn) cancelBtn.style.display = 'block';
            const mins = route.estimatedTime || Math.ceil(route.totalDistance / 80);
            const meters = route.totalDistance || 0;
            addMessage('bot', `🗺️ Route found! About ${meters}m · ~${mins} min walk.`);
            
            // Expand chatbot if minimized
            const chatbotContainer = document.getElementById('chatbotContainer');
            if (chatbotContainer.classList.contains('minimized')) {
                chatbotContainer.classList.remove('minimized');
            }
        } else {
            addMessage('bot', `Sorry, I couldn't find a route from your location to ${destination}.`);
        }
        
    } catch (error) {
        console.error('Navigation error:', error);
        addMessage('bot', 'Sorry, there was an error showing the route.');
    }
}

/**
 * Cancel active navigation and clear the route from the map
 */
function cancelNavigation() {
    if (mapController) {
        mapController.clearRoute();
    }
    const cancelBtn = document.getElementById('cancelNavBtn');
    if (cancelBtn) cancelBtn.style.display = 'none';
    addMessage('bot', '🗺️ Navigation cancelled.');
}

// Expose globally so the onclick in mobile_app.html can reach it
window.cancelNavigation = cancelNavigation;

/**
 * Hide loading overlay
 */
function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 500);
    }
}

// Expose functions globally for other modules
window.mobileApp = {
    addMessage,
    showNavigation,
    isInitialized: () => isInitialized,
    getNavigationEngine: () => navigationEngine,
    getMapController: () => mapController
};

console.log('✅ Mobile interface ready');
