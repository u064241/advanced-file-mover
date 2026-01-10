<template>
  <div class="ai-controls">
    <h3>🤖 {{ i18n.t('ai.title') }}</h3>
    
    <!-- Face Detection -->
    <div class="ai-section">
      <div class="ai-header">
        <h4>👤 {{ i18n.t('ai.faceDetection') }}</h4>
        <label class="toggle-switch">
          <input type="checkbox" v-model="faceDetection.enabled" @change="toggleFaceDetection">
          <span class="slider"></span>
        </label>
      </div>
      <div v-if="faceDetection.enabled" class="ai-info">
        <span class="badge">{{ i18n.t('ai.facesDetected') }}: {{ faceDetection.count }}</span>
        <span v-if="!faceDetection.available" class="badge badge-warning">{{ i18n.t('ai.unavailable') }}</span>
      </div>
    </div>

    <!-- Motion Detection -->
    <div class="ai-section">
      <div class="ai-header">
        <h4>🎬 {{ i18n.t('ai.motionDetection') }}</h4>
        <label class="toggle-switch">
          <input type="checkbox" v-model="motionDetection.enabled" @change="toggleMotionDetection">
          <span class="slider"></span>
        </label>
      </div>
      
      <div v-if="motionDetection.enabled" class="ai-config">
        <!-- Auto-record -->
        <div class="config-item">
          <label>
            <input type="checkbox" v-model="motionDetection.autoRecord" @change="updateMotionSettings">
            {{ i18n.t('ai.autoRecord') }}
          </label>
        </div>
        
        <!-- Sensitivity -->
        <div class="config-item">
          <label>{{ i18n.t('ai.sensitivity') }}: {{ motionDetection.threshold }}</label>
          <input 
            type="range" 
            min="0" 
            max="100" 
            v-model="motionDetection.threshold" 
            @change="updateMotionSettings"
            class="slider-input"
          >
        </div>
        
        <!-- Stop Delay -->
        <div class="config-item">
          <label>{{ i18n.t('ai.stopDelay') }}: {{ motionDetection.stopDelay }}s</label>
          <input 
            type="range" 
            min="1" 
            max="60" 
            v-model="motionDetection.stopDelay" 
            @change="updateMotionSettings"
            class="slider-input"
          >
        </div>
        
        <!-- Status -->
        <div class="ai-info">
          <span :class="['badge', motionDetection.motionDetected ? 'badge-success-pulse' : 'badge-danger-muted']">
            {{ motionDetection.motionDetected ? i18n.t('ai.motionActive') : i18n.t('ai.noMotion') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'

export default {
  name: 'AIControls',
  props: ['token'],
  data() {
    return {
      i18n,
      faceDetection: {
        enabled: false,
        available: false,
        count: 0
      },
      motionDetection: {
        enabled: false,
        autoRecord: false,
        threshold: 25,
        stopDelay: 5,
        motionDetected: false
      },
      statusInterval: null
    }
  },
  mounted() {
    this.loadFaceDetectionStatus()
    this.loadMotionDetectionStatus()
    
    // Aggiorna status ogni 2 secondi
    this.statusInterval = setInterval(() => {
      if (this.faceDetection.enabled) {
        this.loadFaceDetectionStatus()
      }
      if (this.motionDetection.enabled) {
        this.loadMotionDetectionStatus()
      }
    }, 2000)
    
    window.addEventListener('language-changed', this.onLanguageChanged)
  },
  beforeUnmount() {
    if (this.statusInterval) {
      clearInterval(this.statusInterval)
    }
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  methods: {
    onLanguageChanged() {
      this.$forceUpdate()
    },
    async apiCall(url, method = 'GET', body = null) {
      try {
        const options = {
          method,
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          }
        }
        if (body) {
          options.body = JSON.stringify(body)
        }
        const res = await fetch(url, options)
        return await res.json()
      } catch (error) {
        console.error('Errore API call:', error)
        return null
      }
    },
    async loadFaceDetectionStatus() {
      const data = await this.apiCall('/api/face-detection/status')
      if (data) {
        this.faceDetection.enabled = data.enabled
        this.faceDetection.available = data.available
        this.faceDetection.count = data.faces_detected || 0
      }
    },
    async toggleFaceDetection() {
      const data = await this.apiCall('/api/face-detection/toggle', 'POST', {
        enabled: this.faceDetection.enabled
      })
      if (data) {
        this.faceDetection.available = data.available
      }
    },
    async loadMotionDetectionStatus() {
      const data = await this.apiCall('/api/motion-detection/status')
      if (data) {
        this.motionDetection.enabled = data.enabled
        this.motionDetection.autoRecord = data.auto_record
        this.motionDetection.threshold = data.threshold
        this.motionDetection.stopDelay = data.stop_delay
        this.motionDetection.motionDetected = data.motion_detected
      }
    },
    async toggleMotionDetection() {
      await this.updateMotionSettings()
    },
    async updateMotionSettings() {
      const data = await this.apiCall('/api/motion-detection/toggle', 'POST', {
        enabled: this.motionDetection.enabled,
        auto_record: this.motionDetection.autoRecord,
        threshold: parseInt(this.motionDetection.threshold),
        stop_delay: parseInt(this.motionDetection.stopDelay)
      })
      if (data) {
        this.motionDetection.enabled = data.enabled
        this.motionDetection.autoRecord = data.auto_record
      }
    }
  }
}
</script>

<style scoped>
.ai-controls {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin: 15px 0;
}

.ai-controls h3 {
  margin: 0 0 15px 0;
  font-size: 1.2em;
  color: #333;
}

.ai-section {
  background: white;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 15px;
  border: 1px solid #e0e0e0;
}

.ai-section:last-child {
  margin-bottom: 0;
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.ai-header h4 {
  margin: 0;
  font-size: 1em;
  color: #555;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #4CAF50;
}

input:checked + .slider:before {
  transform: translateX(26px);
}

/* AI Config */
.ai-config {
  margin-top: 10px;
}

.config-item {
  margin-bottom: 12px;
}

.config-item label {
  display: block;
  margin-bottom: 5px;
  font-size: 0.9em;
  color: #666;
}

.slider-input {
  width: 100%;
  height: 6px;
  border-radius: 5px;
  background: #ddd;
  outline: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.slider-input:hover {
  opacity: 1;
}

.slider-input::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
}

.slider-input::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
}

/* AI Info */
.ai-info {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.badge {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 600;
  background: #e3f2fd;
  color: #1976d2;
}

.badge-success {
  background: #e8f5e9;
  color: #388e3c;
}

.badge-success-pulse {
  background: #2e7d32;
  color: white;
  font-weight: 700;
  animation: pulse-green 1s infinite;
}

.badge-danger {
  background: #ffebee;
  color: #d32f2f;
  animation: pulse 1s infinite;
}

.badge-danger-muted {
  background: #c62828;
  color: white;
  font-weight: 700;
}

.badge-warning {
  background: #fff3e0;
  color: #f57c00;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes pulse-green {
  0%, 100% { 
    opacity: 1;
    transform: scale(1);
  }
  50% { 
    opacity: 0.6;
    transform: scale(1.05);
  }
}
</style>
