import Pusher from 'pusher-js';

const PUSHER_KEY = import.meta.env.VITE_PUSHER_KEY;
const PUSHER_CLUSTER = import.meta.env.VITE_PUSHER_CLUSTER;

class PusherService {
  constructor() {
    this.pusher = null;
    this.channel = null;
    this.listeners = new Map();
  }

  connect(formId) {
    // Initialize Pusher
    this.pusher = new Pusher(PUSHER_KEY, {
      cluster: PUSHER_CLUSTER,
      encrypted: true
    });

    // Subscribe to form-specific channel
    this.channel = this.pusher.subscribe(`form-${formId}`);

    console.log(`✅ Connected to Pusher channel: form-${formId}`);

    // Bind to live-update event
    this.channel.bind('live-update', (data) => {
      console.log('📨 Live update received:', data);
      this.triggerListeners('live-update', data);
    });

    // Bind to prediction-update event
    this.channel.bind('prediction-update', (data) => {
      console.log('📊 Prediction update:', data);
      this.triggerListeners('prediction-update', data);
    });

    // Bind to notification event
    this.channel.bind('notification', (data) => {
      console.log('🔔 Notification:', data);
      this.triggerListeners('notification', data);
    });

    // Connection state changes
    this.pusher.connection.bind('connected', () => {
      console.log('✅ Pusher connected');
      this.triggerListeners('connection', { status: 'connected' });
    });

    this.pusher.connection.bind('disconnected', () => {
      console.log('❌ Pusher disconnected');
      this.triggerListeners('disconnection', { status: 'disconnected' });
    });

    this.pusher.connection.bind('error', (err) => {
      console.error('Pusher error:', err);
      this.triggerListeners('error', { error: err });
    });
  }

  disconnect() {
    if (this.channel) {
      this.channel.unbind_all();
      this.pusher.unsubscribe(this.channel.name);
    }

    if (this.pusher) {
      this.pusher.disconnect();
    }

    this.listeners.clear();
    console.log('❌ Disconnected from Pusher');
  }

  // Event listener system
  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  off(eventType, callback) {
    if (this.listeners.has(eventType)) {
      const callbacks = this.listeners.get(eventType);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  triggerListeners(eventType, data) {
    if (this.listeners.has(eventType)) {
      this.listeners.get(eventType).forEach((callback) => {
        callback(data);
      });
    }
  }

  isConnected() {
    return this.pusher && this.pusher.connection.state === 'connected';
  }
}

// Create singleton instance
const pusherService = new PusherService();

export default pusherService;