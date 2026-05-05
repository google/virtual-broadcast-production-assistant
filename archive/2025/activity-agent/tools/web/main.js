import './style.css'

class BroadcastFeed {
  constructor() {
    this.ws = null
    this.activities = []
    this.isConnected = false
    
    this.init()
  }

  init() {
    this.connectWebSocket()
    this.setupEventListeners()
    this.loadInitialActivities()
  }

  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}`
    
    this.ws = new WebSocket(wsUrl)
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.isConnected = true
      this.updateConnectionStatus(true)
    }
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.handleWebSocketMessage(message)
    }
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.isConnected = false
      this.updateConnectionStatus(false)
      
      // Reconnect after 3 seconds
      setTimeout(() => this.connectWebSocket(), 3000)
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  handleWebSocketMessage(message) {
    switch (message.type) {
      case 'initial_activities':
        this.activities = message.data
        this.renderActivities()
        break
        
      case 'new_activity':
        this.addActivity(message.data)
        break
        
      case 'activities_cleared':
        this.activities = []
        this.renderActivities()
        break
    }
  }

  addActivity(activity) {
    // Add to beginning with animation
    this.activities.unshift(activity)
    
    // Keep only last 100 activities in memory
    if (this.activities.length > 100) {
      this.activities = this.activities.slice(0, 100)
    }
    
    this.renderNewActivity(activity)
  }

  renderNewActivity(activity) {
    const feed = document.getElementById('activity-feed')
    const activityElement = this.createActivityElement(activity)
    
    // Add with animation
    activityElement.style.opacity = '0'
    activityElement.style.transform = 'translateY(-20px)'
    
    feed.insertBefore(activityElement, feed.firstChild)
    
    // Animate in
    requestAnimationFrame(() => {
      activityElement.style.transition = 'all 0.3s ease-out'
      activityElement.style.opacity = '1'
      activityElement.style.transform = 'translateY(0)'
    })
    
    this.hideEmptyState()
  }

  renderActivities() {
    const feed = document.getElementById('activity-feed')
    const loading = document.getElementById('loading')
    
    loading.classList.add('hidden')
    
    if (this.activities.length === 0) {
      this.showEmptyState()
      return
    }
    
    this.hideEmptyState()
    
    feed.innerHTML = ''
    this.activities.forEach(activity => {
      const element = this.createActivityElement(activity)
      feed.appendChild(element)
    })
  }

  createActivityElement(activity) {
    const div = document.createElement('div')
    
    const typeColors = {
      graphics: 'border-blue-500 bg-blue-500/10',
      vision: 'border-green-500 bg-green-500/10', 
      sofie: 'border-purple-500 bg-purple-500/10',
      system: 'border-red-500 bg-red-500/10',
      user: 'border-yellow-500 bg-yellow-500/10'
    }
    
    const typeIcons = {
      graphics: '🎨',
      vision: '👁️',
      sofie: '📋',
      system: '⚙️',
      user: '👤'
    }
    
    const priorityClasses = {
      critical: 'ring-2 ring-red-400 animate-pulse',
      high: 'ring-1 ring-yellow-400',
      normal: '',
      low: 'opacity-75'
    }
    
    const timeAgo = this.formatTimeAgo(activity.timestamp)
    const colorClass = typeColors[activity.type] || typeColors.system
    const icon = typeIcons[activity.type] || typeIcons.system
    const priorityClass = priorityClasses[activity.priority] || ''
    
    div.className = `
      p-4 rounded-xl border backdrop-blur-sm transition-all hover:scale-[1.02]
      ${colorClass} ${priorityClass}
    `
    
    div.innerHTML = `
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <div class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
            <span class="text-lg">${icon}</span>
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold px-2 py-1 rounded-full bg-gray-700 text-gray-300 uppercase">
                ${activity.type}
              </span>
              ${activity.priority === 'critical' ? '<span class="text-xs font-bold text-red-400">CRITICAL</span>' : ''}
              ${activity.priority === 'high' ? '<span class="text-xs font-semibold text-yellow-400">HIGH</span>' : ''}
            </div>
            <span class="text-xs text-gray-500">${timeAgo}</span>
          </div>
          <h4 class="text-sm font-semibold text-white mb-1">${this.escapeHtml(activity.title)}</h4>
          <p class="text-sm text-gray-300 leading-relaxed">${this.escapeHtml(activity.message)}</p>
          ${activity.agent !== 'unknown' ? `
            <div class="mt-2 text-xs text-gray-500">
              by ${this.escapeHtml(activity.agent)}
            </div>
          ` : ''}
          ${Object.keys(activity.metadata || {}).length > 0 ? `
            <details class="mt-2">
              <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                Show metadata
              </summary>
              <pre class="text-xs text-gray-500 mt-1 bg-gray-800 p-2 rounded overflow-x-auto">
${JSON.stringify(activity.metadata, null, 2)}
              </pre>
            </details>
          ` : ''}
        </div>
      </div>
    `
    
    return div
  }

  formatTimeAgo(timestamp) {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now - time
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)
    
    if (diffSecs < 60) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return time.toLocaleDateString()
  }

  escapeHtml(text) {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status')
    const dot = status.querySelector('div')
    const text = status.querySelector('span')
    
    if (connected) {
      dot.className = 'w-2 h-2 bg-green-400 rounded-full animate-pulse'
      text.textContent = 'Connected'
    } else {
      dot.className = 'w-2 h-2 bg-red-400 rounded-full'
      text.textContent = 'Disconnected'
    }
  }

  showEmptyState() {
    document.getElementById('empty-state').classList.remove('hidden')
  }

  hideEmptyState() {
    document.getElementById('empty-state').classList.add('hidden')
  }

  async loadInitialActivities() {
    try {
      const response = await fetch('/api/activities')
      const activities = await response.json()
      this.activities = activities
      this.renderActivities()
    } catch (error) {
      console.error('Failed to load activities:', error)
      document.getElementById('loading').classList.add('hidden')
      this.showEmptyState()
    }
  }

  setupEventListeners() {
    // Clear button
    document.getElementById('clear-btn').addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear all activities?')) {
        try {
          await fetch('/api/activities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              type: 'system',
              title: 'Feed Cleared',
              message: 'Activity feed was cleared by user',
              metadata: { action: 'clear' }
            })
          })
        } catch (error) {
          console.error('Failed to clear activities:', error)
        }
      }
    })

    // Test buttons
    document.querySelectorAll('.test-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const type = btn.dataset.type
        await this.postTestActivity(type)
      })
    })
  }

  async postTestActivity(type) {
    const testMessages = {
      graphics: {
        title: 'Name strap updated',
        message: 'Added name graphic for John Smith, News Anchor',
        metadata: { person: 'John Smith', role: 'News Anchor' }
      },
      vision: {
        title: 'Screenshot analyzed',
        message: 'Detected person speaking in bottom-left corner of screen',
        metadata: { detected: 'person', location: 'bottom-left', confidence: 0.95 }
      },
      sofie: {
        title: 'Rundown activated',
        message: 'Evening News rundown is now live and ready for playout',
        metadata: { rundown: 'evening-news', segments: 8, duration: '30:00' }
      },
      system: {
        title: 'System Alert',
        message: 'Camera 2 signal lost - switching to backup feed',
        metadata: { camera: 2, action: 'backup_switch', severity: 'warning' }
      }
    }

    const testData = testMessages[type]
    if (!testData) return

    try {
      await fetch('/api/activities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: type,
          title: testData.title,
          message: testData.message,
          metadata: testData.metadata,
          priority: type === 'system' ? 'high' : 'normal',
          agent: 'test-interface'
        })
      })
    } catch (error) {
      console.error('Failed to post test activity:', error)
    }
  }
}

// Initialize the app
new BroadcastFeed()