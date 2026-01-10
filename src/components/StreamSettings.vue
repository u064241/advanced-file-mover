<template>
  <div class="settings">
    <h3>⚙️ {{ i18n.t('admin.users') }}</h3>
    
    <!-- FPS & Quality Settings -->
    <div class="setting-item">
      <label for="fps-slider">
        {{ i18n.t('settings.fps') }}: <strong>{{ localFps }}</strong>
      </label>
      <input 
        id="fps-slider"
        type="range" 
        min="1" 
        max="60" 
        v-model.number="localFps"
        @change="updateSettings"
        class="slider"
      />
      <span class="slider-labels">
        <span>1</span>
        <span>30</span>
        <span>60</span>
      </span>
    </div>

    <div class="setting-item">
      <label for="quality-slider">
        {{ i18n.t('settings.quality') }}: <strong>{{ localQuality }}%</strong>
      </label>
      <input 
        id="quality-slider"
        type="range" 
        min="10" 
        max="100" 
        v-model.number="localQuality"
        @change="updateSettings"
        class="slider"
      />
      <span class="slider-labels">
        <span>10%</span>
        <span>55%</span>
        <span>100%</span>
      </span>
    </div>

    <!-- Camera Properties Section -->
    <div class="camera-properties-section">
      <h4>📷 {{ i18n.t('settings.cameraProperties') }}</h4>
      
      <!-- LED Control Section (Always Visible) -->
      <div class="setting-item">
        <label>💡 {{ i18n.t('settings.ledControl') }}</label>
        <div class="led-controls">
          <button 
            @click="toggleLed" 
            :class="['btn-led', ledStatus === true ? 'led-on' : ledStatus === false ? 'led-off' : 'led-not-supported']"
            :disabled="ledStatus === null"
          >
            <span v-if="ledStatus === true" class="led-indicator on"></span>
            <span v-else-if="ledStatus === false" class="led-indicator off"></span>
            {{ 
              ledStatus === true ? '✓ ' + i18n.t('settings.ledOn') : 
              ledStatus === false ? '✗ ' + i18n.t('settings.ledOff') : 
              i18n.t('settings.ledNotSupported')
            }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading-text">
        {{ i18n.t('messages.loading') }}
      </div>

      <div v-else>
        <!-- Risoluzione -->
        <div class="setting-item">
          <label>📐 {{ i18n.t('settings.resolution') }}</label>
          <div class="resolution-controls">
            <input 
              type="number" 
              v-model.number="properties.width" 
              placeholder="Larghezza"
              min="320"
              max="3840"
              class="input-small"
            />
            <span class="x-separator">×</span>
            <input 
              type="number" 
              v-model.number="properties.height" 
              placeholder="Altezza"
              min="240"
              max="2160"
              class="input-small"
            />
            <button @click="setResolution" class="btn-apply">{{ i18n.t('settings.apply') }}</button>
          </div>
          <div class="preset-buttons">
            <button @click="applyPreset(640, 480)" class="btn-preset">VGA</button>
            <button @click="applyPreset(800, 600)" class="btn-preset">SVGA</button>
            <button @click="applyPreset(1280, 720)" class="btn-preset">720p</button>
            <button @click="applyPreset(1920, 1080)" class="btn-preset">1080p</button>
          </div>
        </div>

        <!-- Luminosità -->
        <div class="setting-item">
          <label>
            💡 {{ i18n.t('settings.brightness') }}: <strong>{{ properties.brightness }}</strong>
          </label>
          <input 
            type="range" 
            v-model.number="properties.brightness" 
            min="-127" 
            max="127"
            @change="updateBrightness"
            class="slider"
          />
          <span class="slider-labels">
            <span>-127</span>
            <span>0</span>
            <span>127</span>
          </span>
        </div>

        <!-- Contrasto -->
        <div class="setting-item">
          <label>
            🎨 {{ i18n.t('settings.contrast') }}: <strong>{{ properties.contrast }}</strong>
          </label>
          <input 
            type="range" 
            v-model.number="properties.contrast" 
            min="0" 
            max="127"
            @change="updateContrast"
            class="slider"
          />
          <span class="slider-labels">
            <span>0</span>
            <span>64</span>
            <span>127</span>
          </span>
        </div>

        <!-- Saturazione -->
        <div class="setting-item">
          <label>
            🌈 {{ i18n.t('settings.saturation') }}: <strong>{{ properties.saturation }}%</strong>
          </label>
          <input 
            type="range" 
            v-model.number="properties.saturation" 
            min="0" 
            max="100"
            @change="updateSaturation"
            class="slider"
          />
          <span class="slider-labels">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </span>
        </div>

        <!-- Esposizione -->
        <div class="setting-item">
          <label>
            📸 {{ i18n.t('settings.exposure') }}: <strong>{{ properties.exposure }}</strong>
          </label>
          <input 
            type="range" 
            v-model.number="properties.exposure" 
            min="-13" 
            max="0"
            @change="updateExposure"
            class="slider"
          />
          <span class="slider-labels">
            <span>-13</span>
            <span>-6</span>
            <span>0</span>
          </span>
        </div>

        <!-- Guadagno -->
        <div class="setting-item">
          <label>
            🔊 {{ i18n.t('settings.gain') }}: <strong>{{ properties.gain }}%</strong>
          </label>
          <input 
            type="range" 
            v-model.number="properties.gain" 
            min="0" 
            max="100"
            @change="updateGain"
            class="slider"
          />
          <span class="slider-labels">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </span>
        </div>

        <!-- Reset Button -->
        <div class="setting-item">
          <button @click="resetToDefaults" class="btn-reset">
            🔄 {{ i18n.t('common.reset') }}
          </button>
        </div>

        <!-- Status Message -->
        <div v-if="statusMessage" :class="['status-message', statusMessage.type]">
          {{ statusMessage.text }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'

export default {
  name: 'StreamSettings',
  props: ['token', 'fps', 'quality'],
  emits: ['settingsChanged'],
  data() {
    return {
      i18n,
      localFps: this.fps,
      localQuality: this.quality,
      loading: true,
      ledStatus: null,  // true = on, false = off, null = not supported
      properties: {
        width: 640,
        height: 480,
        brightness: 0,
        contrast: 0,
        saturation: 0,
        exposure: 0,
        gain: 0
      },
      statusMessage: null
    }
  },
  mounted() {
    this.loadProperties()
    this.loadLedStatus()
    window.addEventListener('language-changed', this.onLanguageChanged)
  },
  beforeUnmount() {
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  watch: {
    fps(newVal) {
      this.localFps = newVal
    },
    quality(newVal) {
      this.localQuality = newVal
    }
  },
  methods: {
    onLanguageChanged() {
      this.$forceUpdate()
    },
    async updateSettings() {
      try {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            fps: this.localFps,
            quality: this.localQuality
          })
        })
        
        const data = await res.json()
        if (data.success) {
          this.$emit('settingsChanged', {
            fps: data.fps,
            quality: data.quality
          })
        }
      } catch (error) {
        console.error('Errore aggiornamento impostazioni:', error)
      }
    },
    async loadProperties() {
      this.loading = true
      try {
        const res = await fetch('/api/camera/properties', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.success && data.properties) {
            const props = data.properties
            this.properties = {
              width: props.resolution?.width || 640,
              height: props.resolution?.height || 480,
              brightness: Math.round(props.brightness || 0),
              contrast: Math.round(props.contrast || 0),
              saturation: Math.round(props.saturation || 0),
              exposure: Math.round(props.exposure || 0),
              gain: Math.round(props.gain || 0)
            }
          }
        }
      } catch (error) {
        console.error('Errore caricamento proprietà:', error)
        this.showStatus('Errore caricamento proprietà', 'error')
      } finally {
        this.loading = false
      }
    },
    async setResolution() {
      try {
        const res = await fetch('/api/camera/resolution', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            width: this.properties.width,
            height: this.properties.height
          })
        })
        const data = await res.json()
        if (data.success) {
          this.properties.width = data.width
          this.properties.height = data.height
          this.showStatus(`${this.i18n.t('settings.resolution')}: ${data.width}x${data.height}`, 'success')
        } else {
          this.showStatus(this.i18n.t('messages.error'), 'error')
        }
      } catch (error) {
        console.error('Errore impostazione risoluzione:', error)
        this.showStatus(this.i18n.t('messages.error'), 'error')
      }
    },
    applyPreset(width, height) {
      this.properties.width = width
      this.properties.height = height
      this.setResolution()
    },
    async updateBrightness() {
      await this.updateProperty('brightness', this.properties.brightness)
    },
    async updateContrast() {
      await this.updateProperty('contrast', this.properties.contrast)
    },
    async updateSaturation() {
      await this.updateProperty('saturation', this.properties.saturation)
    },
    async updateExposure() {
      await this.updateProperty('exposure', this.properties.exposure)
    },
    async updateGain() {
      await this.updateProperty('gain', this.properties.gain)
    },
    async updateProperty(propName, value) {
      try {
        const res = await fetch(`/api/camera/${propName}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({ value })
        })
        const data = await res.json()
        if (data.success) {
          this.properties[propName] = Math.round(data[propName])
        }
      } catch (error) {
        console.error(`Errore aggiornamento ${propName}:`, error)
      }
    },
    async resetToDefaults() {
      try {
        // Reset brightness
        await this.updateProperty('brightness', 0)
        // Reset contrast al valore neutro della webcam (32)
        await this.updateProperty('contrast', 32)
        // Reset saturation al valore neutro (50)
        await this.updateProperty('saturation', 50)
        // Reset exposure
        await this.updateProperty('exposure', 0)
        // Reset gain
        await this.updateProperty('gain', 0)
        
        // Ricarica i valori effettivi dalla camera
        await this.loadProperties()
        
        this.showStatus(this.i18n.t('messages.success'), 'success')
      } catch (error) {
        console.error('Errore ripristino:', error)
        this.showStatus(this.i18n.t('messages.error'), 'error')
      }
    },
    async loadLedStatus() {
      try {
        const res = await fetch('/api/camera/led', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.supported) {
            this.ledStatus = data.led_enabled
          } else {
            this.ledStatus = null  // Not supported
          }
        }
      } catch (error) {
        console.error('Errore caricamento stato LED:', error)
        this.ledStatus = null
      }
    },
    async toggleLed() {
      try {
        const newState = !this.ledStatus
        const res = await fetch('/api/camera/led', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({ enabled: newState })
        })
        
        if (res.ok) {
          const data = await res.json()
          if (data.supported) {
            this.ledStatus = data.led_enabled
            this.showStatus(data.message, 'success')
          } else {
            this.ledStatus = null
            this.showStatus(this.i18n.t('settings.ledNotSupported'), 'error')
          }
        } else {
          this.showStatus(this.i18n.t('messages.error'), 'error')
        }
      } catch (error) {
        console.error('Errore controllo LED:', error)
        this.showStatus(this.i18n.t('messages.error'), 'error')
      }
    },
    showStatus(message, type = 'success') {
      this.statusMessage = { text: message, type }
      setTimeout(() => {
        this.statusMessage = null
      }, 3000)
    }
  }
}
</script>

<style scoped>
.settings {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
}

h3 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

h4 {
  color: #34a853;
  margin: 25px 0 15px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #34a853;
  font-size: 16px;
}

.setting-item {
  margin-bottom: 25px;
}

label {
  display: block;
  margin-bottom: 10px;
  color: #555;
  font-size: 1em;
  font-weight: 600;
}

label strong {
  color: #667eea;
  font-size: 1.1em;
}

.slider {
  width: 100%;
  height: 8px;
  border-radius: 5px;
  background: #ddd;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  margin-bottom: 5px;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  transition: all 0.2s ease;
}

.slider::-webkit-slider-thumb:hover {
  background: #5568d3;
  transform: scale(1.2);
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.slider::-moz-range-thumb:hover {
  background: #5568d3;
  transform: scale(1.2);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.85em;
  color: #888;
}

.camera-properties-section {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 2px solid #ddd;
}

.loading-text {
  text-align: center;
  color: #666;
  padding: 20px;
}

.resolution-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.input-small {
  width: 100px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.x-separator {
  color: #999;
  font-weight: bold;
}

.btn-apply {
  padding: 8px 15px;
  background: #4285f4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s ease;
}

.btn-apply:hover {
  background: #357ae8;
}

.preset-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-preset {
  padding: 6px 12px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-preset:hover {
  background: #e0e0e0;
  border-color: #999;
}

.btn-reset {
  width: 100%;
  padding: 10px 15px;
  background: #ea4335;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s ease;
}

.btn-reset:hover {
  background: #d33425;
}

.status-message {
  padding: 12px 15px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  animation: slideIn 0.3s ease;
  margin-top: 15px;
}

.status-message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.led-controls {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.btn-led {
  padding: 10px 20px;
  border: 2px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 150px;
}

.btn-led.led-on {
  background: #c8e6c9;
  color: #2e7d32;
  border-color: #2e7d32;
}

.btn-led.led-on:hover {
  background: #a5d6a7;
  transform: scale(1.05);
}

.btn-led.led-off {
  background: #ffcdd2;
  color: #c62828;
  border-color: #c62828;
}

.btn-led.led-off:hover {
  background: #ef9a9a;
  transform: scale(1.05);
}

.btn-led.led-not-supported {
  background: #eeeeee;
  color: #666;
  border-color: #bdbdbd;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-led:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.led-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.led-indicator.on {
  background: #4caf50;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.8);
  animation: pulse 1.5s ease-in-out infinite;
}

.led-indicator.off {
  background: #f44336;
  box-shadow: 0 0 4px rgba(244, 67, 54, 0.4);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}
</style>
