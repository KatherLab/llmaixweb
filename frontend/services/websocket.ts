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
  // After exhausting the fast retry budget we back off to this slow cadence
  // rather than giving up permanently, so the socket recovers on its own from
  // long outages (e.g. a backend redeploy) without a manual page reload.
  private idleReconnectDelay = 60000 // 1 minute
  private listeners = new Map<string, Set<WsListener>>()
  isConnected = false
  private manualClose = false
  private retryTimeout: ReturnType<typeof setTimeout> | null = null
  // Optional async hook that returns a fresh access token. Registered by the
  // auth store (kept as a hook to avoid a circular import). Used before a
  // reconnect so a dropped socket doesn't keep retrying with an expired token.
  private tokenRefreshHook: (() => Promise<string | null>) | null = null

  /**
   * Register a callback that refreshes and returns a valid access token.
   */
  setTokenRefreshHook(hook: () => Promise<string | null>) {
    this.tokenRefreshHook = hook
  }

  /**
   * Connect to the WebSocket server
   */
  connect() {
    // Return early if a socket is already open OR mid-handshake — guarding only
    // on OPEN lets a reconnect timer and a component watcher each spawn a socket,
    // leaving an orphan whose onmessage still fires (duplicate event delivery).
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return
    }

    // Tear down any lingering socket (e.g. CLOSING) and its handlers before
    // creating a new one, so a stale instance can't feed handleMessage.
    this.teardownSocket()

    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('[WebSocket] No auth token, skipping connection')
      return
    }

    // An explicit connect() clears a prior manual-close so the reconnect loop
    // is allowed to run again (e.g. login after a previous logout).
    this.manualClose = false

    // Build WebSocket URL - always use relative path
    // Both nginx (production) and Vite proxy (dev) will forward to backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/activity`

    try {
      // Pass the JWT via the WebSocket subprotocol header instead of the query
      // string, so it never lands in proxy/access logs the way `?token=` does.
      // The server echoes the `access_token` subprotocol to complete the
      // handshake. Format: ['access_token', '<jwt>'].
      this.ws = new WebSocket(wsUrl, ['access_token', token])

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
   * Schedule a reconnection attempt.
   *
   * Uses an exponential backoff for the first `maxReconnectAttempts`, then
   * falls back to a slow fixed cadence (instead of giving up) so the socket
   * still recovers from outages longer than the fast-retry budget. Before each
   * attempt it refreshes the access token if a hook is registered, so we never
   * spin on an expired token.
   */
  scheduleReconnect() {
    if (this.manualClose) {
      return
    }

    let delay: number
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      // Exhausted the fast budget — keep trying, just slowly.
      this.emit('maxReconnectAttemptsReached', {
        type: 'maxReconnectAttemptsReached',
      })
      delay = this.idleReconnectDelay
    } else {
      this.reconnectAttempts++
      delay = Math.min(
        this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1),
        this.maxReconnectDelay,
      )
    }

    console.log(`[WebSocket] Reconnecting in ${Math.round(delay)}ms`)

    this.retryTimeout = setTimeout(() => {
      void this.reconnectWithFreshToken()
    }, delay)
  }

  /**
   * Refresh the access token (if a hook is registered) then reconnect.
   */
  private async reconnectWithFreshToken() {
    if (this.manualClose) {
      return
    }
    if (this.tokenRefreshHook) {
      try {
        await this.tokenRefreshHook()
      } catch {
        // Ignore — connect() falls back to the stored token; if it's dead the
        // socket close handler will schedule another attempt.
      }
    }
    this.connect()
  }

  /**
   * Remove handlers from and close the current socket without touching
   * manualClose / reconnect scheduling.
   */
  private teardownSocket() {
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.onmessage = null
      try {
        this.ws.close()
      } catch {
        /* already closing/closed */
      }
      this.ws = null
    }
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
    this.teardownSocket()
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
        // Pass eventType as a separate argument rather than interpolating it
        // into the format string — the message type is server-supplied, so
        // embedding it could inject console format specifiers.
        console.error('[WebSocket] Error in listener for event:', eventType, error)
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

// Recover promptly when the network comes back or the tab is refocused after
// a long sleep, instead of waiting out the slow idle-reconnect timer. connect()
// is a no-op when a socket is already open/connecting.
window.addEventListener('online', checkAndConnect)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    checkAndConnect()
  }
})
