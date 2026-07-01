/**
 * WebSocket service for real-time task updates.
 * Manages connection, reconnection, and event broadcasting.
 */
import type { WsListener, WsMessage } from '@/types'

class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000 // Start with 1 second
  private maxReconnectDelay = 30000 // Max 30 seconds
  private listeners = new Map<string, Set<WsListener>>()
  isConnected = false
  private manualClose = false
  private retryTimeout: ReturnType<typeof setTimeout> | null = null

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
        this.emit('connected', { type: 'connected' })
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
        this.emit('error', { type: 'error', error })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WsMessage
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
      this.emit('maxReconnectAttemptsReached', {
        type: 'maxReconnectAttemptsReached',
      })
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
  handleMessage(data: WsMessage) {
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
   * @param eventType - 'preprocessing_update', 'trial_update', etc.
   * @param callback - Function to call when event is received
   * @returns Unsubscribe function
   */
  subscribe(eventType: string, callback: WsListener): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)?.add(callback)

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(callback)
    }
  }

  /**
   * Emit an event to all listeners
   */
  emit(eventType: string, data: WsMessage) {
    this.listeners.get(eventType)?.forEach((callback) => {
      try {
        callback(data)
      } catch (error) {
        console.error(`[WebSocket] Error in ${eventType} listener:`, error)
      }
    })
  }

  /**
   * Subscribe to preprocessing task updates
   */
  onPreprocessingUpdate(callback: WsListener): () => void {
    return this.subscribe('preprocessing_update', callback)
  }

  /**
   * Subscribe to trial updates
   */
  onTrialUpdate(callback: WsListener): () => void {
    return this.subscribe('trial_update', callback)
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
