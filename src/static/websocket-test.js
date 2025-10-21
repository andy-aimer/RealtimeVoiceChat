/**
 * WebSocket Lifecycle Test Script - Phase 2 P3
 * 
 * This script tests the WebSocket reconnection logic without requiring audio capture.
 * Focus: Session management, exponential backoff, and connection persistence.
 */

// =============================================================================
// Exponential Backoff Implementation (matches server-side)
// =============================================================================

class ExponentialBackoff {
  constructor(initialDelay = 1000, maxDelay = 30000, maxAttempts = 10) {
    this.initialDelay = initialDelay;  // milliseconds
    this.maxDelay = maxDelay;
    this.maxAttempts = maxAttempts;
    this.attempt = 0;
  }

  nextDelay() {
    const delay = Math.min(
      this.initialDelay * Math.pow(2, this.attempt),
      this.maxDelay
    );
    this.attempt++;
    return delay;
  }

  shouldGiveUp() {
    return this.attempt >= this.maxAttempts;
  }

  reset() {
    this.attempt = 0;
  }

  getAttempt() {
    return this.attempt;
  }

  getTotalWaitTime() {
    let total = 0;
    for (let i = 0; i < this.attempt; i++) {
      total += Math.min(
        this.initialDelay * Math.pow(2, i),
        this.maxDelay
      );
    }
    return total;
  }
}

// =============================================================================
// WebSocket Client Implementation
// =============================================================================

class WebSocketTestClient {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.backoff = new ExponentialBackoff();
    this.isReconnecting = false;
    this.isManualDisconnect = false;  // Initialize this property
    this.reconnectTimer = null;
    this.messagesSent = 0;
    this.messagesReceived = 0;
    this.connectionAttempts = 0;
    
    // Callbacks
    this.onConnectionChange = null;
    this.onMessage = null;
    this.onSessionCreated = null;
    this.onSessionRestored = null;
  }

  connect() {
    this.connectionAttempts++;
    this.updateConnectionAttempts();
    
    const sessionId = this.getStoredSessionId();
    const wsUrl = sessionId ? `${this.url}?session_id=${sessionId}` : this.url;
    
    this.log(`Connecting to: ${wsUrl}`, 'info');
    this.setStatus('Connecting...', 'connecting');
    
    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      this.log(`Connection failed: ${error.message}`, 'error');
      this.handleConnectionError();
    }
  }

  setupEventHandlers() {
    this.socket.onopen = () => {
      this.log('✅ WebSocket connection opened', 'success');
      this.setStatus('Connected', 'connected');
      this.backoff.reset();
      this.isReconnecting = false;
      this.updateTestResult('test-initial', true);
      
      if (this.onConnectionChange) {
        this.onConnectionChange('connected');
      }
    };

    this.socket.onmessage = (event) => {
      this.messagesReceived++;
      this.updateMessagesReceived();
      this.updateLastActive();
      
      try {
        const data = JSON.parse(event.data);
        this.log(`📨 Received: ${data.type}`, 'info');
        
        if (data.type === 'session_created') {
          this.handleSessionCreated(data.session_id);
        } else if (data.type === 'session_restored') {
          this.handleSessionRestored(data.session_id);
        } else if (data.type === 'echo') {
          this.updateTestResult('test-message', true);
          this.log(`✅ Message echo successful`, 'success');
        }
        
        if (this.onMessage) {
          this.onMessage(data);
        }
      } catch (error) {
        this.log(`❌ Failed to parse message: ${error.message}`, 'error');
      }
    };

    this.socket.onclose = (event) => {
      this.log(`🔌 WebSocket closed (code: ${event.code}, reason: ${event.reason})`, 'warning');
      this.setStatus('Disconnected', 'disconnected');
      
      if (this.onConnectionChange) {
        this.onConnectionChange('disconnected');
      }
      
      // Debug logging for reconnection logic
      this.log(`📊 Reconnection check: isManualDisconnect=${this.isManualDisconnect}, code=${event.code}`, 'info');
      
      // Auto-reconnect if not manually disconnected and not a normal closure
      if (!this.isManualDisconnect && event.code !== 1000) {
        this.log('🔄 Auto-reconnect triggered', 'info');
        this.scheduleReconnect();
      } else {
        this.log('⏹️ No auto-reconnect (manual disconnect or normal closure)', 'info');
      }
    };

    this.socket.onerror = (error) => {
      this.log(`❌ WebSocket error: ${error}`, 'error');
      this.handleConnectionError();
    };
  }

  disconnect() {
    this.isManualDisconnect = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      this.socket.close(1000, 'Manual disconnect');
    }
    
    this.setStatus('Disconnected', 'disconnected');
    this.log('👋 Manually disconnected', 'info');
  }

  scheduleReconnect() {
    if (this.backoff.shouldGiveUp()) {
      this.log('❌ Max reconnection attempts reached', 'error');
      this.setStatus('Reconnect Failed', 'reconnect-failed');
      this.updateTestResult('test-reconnect', false);
      return;
    }

    const delay = this.backoff.nextDelay();
    const attempt = this.backoff.getAttempt();
    
    this.log(`🔄 Reconnecting in ${delay}ms (attempt ${attempt}/${this.backoff.maxAttempts})`, 'warning');
    this.setStatus(`Reconnecting... (${attempt}/${this.backoff.maxAttempts})`, 'reconnecting');
    this.isReconnecting = true;
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
    
    this.updateTestResult('test-reconnect', true);
  }

  handleConnectionError() {
    if (!this.isReconnecting) {
      this.scheduleReconnect();
    }
  }

  sendMessage(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
      this.messagesSent++;
      this.updateMessagesSent();
      this.updateLastActive();
      this.log(`📤 Sent: ${data.type}`, 'info');
      return true;
    } else {
      this.log('⚠️ Cannot send: WebSocket not open', 'warning');
      return false;
    }
  }

  handleSessionCreated(sessionId) {
    this.log(`✨ New session created: ${sessionId}`, 'success');
    this.saveSessionId(sessionId);
    this.updateSessionId(sessionId);
    this.updateTestResult('test-session', true);
    
    if (this.onSessionCreated) {
      this.onSessionCreated(sessionId);
    }
  }

  handleSessionRestored(sessionId) {
    this.log(`🔄 Session restored: ${sessionId}`, 'success');
    this.updateSessionId(sessionId);
    this.updateTestResult('test-restore', true);
    
    if (this.onSessionRestored) {
      this.onSessionRestored(sessionId);
    }
  }

  // Session persistence methods
  saveSessionId(sessionId) {
    localStorage.setItem('websocket_session_id', sessionId);
  }

  getStoredSessionId() {
    return localStorage.getItem('websocket_session_id');
  }

  clearStoredSession() {
    localStorage.removeItem('websocket_session_id');
    this.updateSessionId('None');
    this.log('🗑️ Session cleared from localStorage', 'info');
  }

  // UI update methods
  setStatus(text, className) {
    const indicator = document.getElementById('statusIndicator');
    const details = document.getElementById('statusDetails');
    
    indicator.textContent = text;
    indicator.className = `status-indicator status-${className}`;
    details.textContent = new Date().toLocaleTimeString();
  }

  updateSessionId(sessionId) {
    document.getElementById('sessionId').textContent = sessionId || 'None';
  }

  updateConnectionAttempts() {
    document.getElementById('connectionAttempts').textContent = this.connectionAttempts;
  }

  updateMessagesSent() {
    document.getElementById('messagesSent').textContent = this.messagesSent;
  }

  updateMessagesReceived() {
    document.getElementById('messagesReceived').textContent = this.messagesReceived;
  }

  updateLastActive() {
    document.getElementById('lastActive').textContent = new Date().toLocaleTimeString();
  }

  updateTestResult(testId, passed) {
    const element = document.getElementById(testId);
    if (passed) {
      element.textContent = '✅ Pass';
      element.className = 'test-pass';
    } else {
      element.textContent = '❌ Fail';
      element.className = 'test-fail';
    }
  }

  log(message, type = 'info') {
    const container = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
    
    // Also log to browser console for debugging
    console.log(`[WebSocket Test] ${message}`);
  }
}

// =============================================================================
// Global Variables and UI Control Functions
// =============================================================================

let wsClient = null;

function connect() {
  if (wsClient && wsClient.socket && wsClient.socket.readyState === WebSocket.OPEN) {
    wsClient.log('⚠️ Already connected', 'warning');
    return;
  }
  
  wsClient = new WebSocketTestClient('ws://localhost:8000/ws');
  wsClient.isManualDisconnect = false;
  
  // Setup event handlers
  wsClient.onConnectionChange = (status) => {
    updateButtonStates(status === 'connected');
  };
  
  wsClient.connect();
}

function disconnect() {
  if (wsClient) {
    wsClient.disconnect();
    updateButtonStates(false);
  }
}

function sendTestMessage() {
  if (wsClient) {
    const success = wsClient.sendMessage({
      type: 'test_message',
      data: 'Hello from WebSocket test client!',
      timestamp: new Date().toISOString()
    });
    
    if (!success) {
      wsClient.updateTestResult('test-message', false);
    }
  }
}

function clearSession() {
  if (wsClient) {
    wsClient.clearStoredSession();
  }
}

function clearLogs() {
  const container = document.getElementById('logContainer');
  container.innerHTML = '<div class="log-entry log-info">[Cleared] Log history cleared</div>';
}

function testReconnection() {
  if (wsClient && wsClient.socket && wsClient.socket.readyState === WebSocket.OPEN) {
    wsClient.log('🧪 Testing reconnection - simulating connection loss...', 'info');
    
    // Reset manual disconnect flag and ensure auto-reconnect will work
    wsClient.isManualDisconnect = false;
    
    // Clear any existing reconnect timer
    if (wsClient.reconnectTimer) {
      clearTimeout(wsClient.reconnectTimer);
      wsClient.reconnectTimer = null;
    }
    
    // Close with a code that will trigger reconnection (1006 = abnormal closure)
    wsClient.socket.close(1006, 'Test reconnection');
    
    wsClient.log('🔌 Connection closed for testing - auto-reconnect should start...', 'warning');
  } else {
    console.warn('Cannot test reconnection: WebSocket not connected');
  }
}

function updateButtonStates(connected) {
  document.getElementById('connectBtn').disabled = connected;
  document.getElementById('disconnectBtn').disabled = !connected;
  document.getElementById('sendTestMsg').disabled = !connected;
  document.getElementById('testReconnection').disabled = !connected;
}

// =============================================================================
// Initialize
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Check for existing session
  const existingSession = localStorage.getItem('websocket_session_id');
  if (existingSession) {
    document.getElementById('sessionId').textContent = existingSession;
  }
  
  // Update initial button states
  updateButtonStates(false);
  
  console.log('WebSocket Lifecycle Test Interface loaded');
});