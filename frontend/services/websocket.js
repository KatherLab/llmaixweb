/**
 * WebSocket service for real-time task updates.
 * Manages connection, reconnection, and event broadcasting.
 */

import { api } from './api.js'

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 1000 // Start with 1 second
    this.maxReconnectDelay = 30000 // Max 30 seconds
    this.listeners = new Map()
    this.isConnected = false
    this.manualClose = false
    this.retryTimeout = null
  }

  /**
   * Connect to the WebSocket server
   */
  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('[WebSocket] No auth token, skipping connection')
      return
    }

    // Build WebSocket URL - always use relative path
    // Both nginx (production) and Vite proxy (dev) will forward to backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/activity?token=${token}`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.reconnectDelay = 1000
        this.manualClose = false
        this.emit('connected')
      }

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected', event.code, event.reason)
        this.isConnected = false

        if (!this.manualClose) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        this.emit('error', error)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e)
        }
      }
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error)
      this.scheduleReconnect()
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WebSocket] Max reconnection attempts reached')
      this.emit('maxReconnectAttemptsReached')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(
      this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      this.maxReconnectDelay,
    )

    console.log(
      `[WebSocket] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    )

    this.retryTimeout = setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    this.manualClose = true
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout)
      this.retryTimeout = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(data) {
    const { type } = data

    if (!type) {
      console.warn('[WebSocket] Received message without type:', data)
      return
    }

    // Emit event for specific message type
    this.emit(type, data)

    // Also emit generic 'message' event
    this.emit('message', data)
  }

  /**
   * Subscribe to a specific event type
   * @param {string} eventType - 'preprocessing_update', 'trial_update', etc.
   * @param {Function} callback - Function to call when event is received
   * @returns {Function} - Unsubscribe function
   */
  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(callback)
    }
  }

  /**
   * Emit an event to all listeners
   */
  emit(eventType, data) {
    // Emit for specific event type
    this.listeners.get(eventType)?.forEach((callback) => {
      try {
        callback(data)
      } catch (error) {
        console.error(`[WebSocket] Error in ${eventType} listener:`, error)
      }
    })

    // Always emit 'all' events for debugging
    if (this.listeners.has('all')) {
      this.listeners.get('all').forEach((callback) => {
        try {
          callback({ type: eventType, data })
        } catch (error) {
          console.error('[WebSocket] Error in all listener:', error)
        }
      })
    }
  }

  /**
   * Subscribe to all events (useful for debugging)
   */
  subscribeAll(callback) {
    return this.subscribe('all', callback)
  }

  /**
   * Subscribe to preprocessing task updates
   */
  onPreprocessingUpdate(callback) {
    return this.subscribe('preprocessing_update', callback)
  }

  /**
   * Subscribe to trial updates
   */
  onTrialUpdate(callback) {
    return this.subscribe('trial_update', callback)
  }

  /**
   * Send a message to the server
   */
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] Cannot send - not connected')
    }
  }

  /**
   * Ping the server to keep connection alive
   */
  ping() {
    this.send({ type: 'ping' })
  }
}

// Export singleton instance
export const websocketService = new WebSocketService()

// Auto-connect when token becomes available
const checkAndConnect = () => {
  const token = localStorage.getItem('token')
  if (token && !websocketService.isConnected) {
    websocketService.connect()
  }
}

// Check on load
checkAndConnect()

// Listen for storage events (token changes in other tabs)
window.addEventListener('storage', (e) => {
  if (e.key === 'token') {
    if (e.newValue) {
      websocketService.connect()
    } else {
      websocketService.disconnect()
    }
  }
})
