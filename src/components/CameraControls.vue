<template>
  <div class="controls">
    <div class="button-group">
      <button @click="flip('h')" class="btn btn-primary">
        ↔️ {{ i18n.t('controls.flipH') }}
      </button>
      <button @click="flip('v')" class="btn btn-primary">
        ↕️ {{ i18n.t('controls.flipV') }}
      </button>
      <button @click="rotate(-90)" class="btn btn-secondary">
        ↶ {{ i18n.t('controls.rotateLeft') }}
      </button>
      <button @click="rotate(90)" class="btn btn-secondary">
        ↷ {{ i18n.t('controls.rotateRight') }}
      </button>
      <button @click="reset" class="btn btn-danger">
        🔄 {{ i18n.t('controls.reset') }}
      </button>
    </div>

    <div class="action-group">
      <button @click="toggleRecording" :class="['btn', recording ? 'btn-recording' : 'btn-rec']">
        {{ recording ? '⏹️' : '🔴' }} {{ recording ? i18n.t('controls.stopRecord') : i18n.t('controls.record') }}
      </button>
      <button @click="takeSnapshot" class="btn btn-snapshot">
        📸 {{ i18n.t('controls.snapshot') }}
      </button>
    </div>

    <div class="camera-selector">
      <label for="camera-select">📷 {{ i18n.t('controls.switchCamera') }}:</label>
      <select id="camera-select" v-model="selectedCamera" @change="switchCamera">
        <option v-for="cam in cameras" :key="cam" :value="cam">
          Webcam {{ cam }}
        </option>
      </select>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'

export default {
  name: 'CameraControls',
  props: ['token', 'recording'],
  emits: ['cameraSwitched', 'recordingChanged', 'snapshotTaken'],
  data() {
    return {
      i18n,
      cameras: [],
      selectedCamera: 0
    }
  },
  mounted() {
    this.fetchCameras()
    window.addEventListener('language-changed', this.onLanguageChanged)
  },
  beforeUnmount() {
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  methods: {
    onLanguageChanged() {
      this.$forceUpdate()
    },
    async fetchCameras() {
      try {
        const res = await fetch('/api/cameras')
        this.cameras = await res.json()
        if (this.cameras.length > 0) {
          this.selectedCamera = this.cameras[0]
        }
      } catch (error) {
        console.error('Errore caricamento webcam:', error)
      }
    },
    async apiCall(url, method = 'POST') {
      try {
        const res = await fetch(url, {
          method,
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        return await res.json()
      } catch (error) {
        console.error('Errore API call:', error)
        return null
      }
    },
    flip(axis) {
      if (axis === 'h') this.apiCall('/api/flip_horizontal')
      if (axis === 'v') this.apiCall('/api/flip_vertical')
    },
    rotate(angle) {
      if (angle === -90) this.apiCall('/api/rotate_left')
      if (angle === 90) this.apiCall('/api/rotate_right')
    },
    reset() {
      this.apiCall('/api/reset')
    },
    async switchCamera() {
      try {
        await this.apiCall(`/api/switch_camera/${this.selectedCamera}`)
        this.$emit('cameraSwitched')
      } catch (error) {
        console.error('Errore switch camera:', error)
      }
    },
    async toggleRecording() {
      if (this.recording) {
        const result = await this.apiCall('/api/recording/stop')
        if (result && result.success) {
          this.$emit('recordingChanged', false)
          alert(`Registrazione salvata: ${result.filename}`)
        }
      } else {
        const result = await this.apiCall('/api/recording/start')
        if (result && result.success) {
          this.$emit('recordingChanged', true)
        }
      }
    },
    async takeSnapshot() {
      const result = await this.apiCall('/api/snapshot')
      if (result && result.success) {
        this.$emit('snapshotTaken', result.filename)
        // Download automatico
        const downloadUrl = `/api/snapshot/${result.filename}?token=${this.token}`
        window.open(downloadUrl, '_blank')
      }
    }
  }
}
</script>

<style scoped>
.controls {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
}

.button-group, .action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 20px;
}

.btn {
  padding: 12px 20px;
  font-size: 1em;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 600;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
}

.btn:active {
  transform: translateY(0);
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #48bb78;
  color: white;
}

.btn-secondary:hover {
  background: #38a169;
}

.btn-danger {
  background: #f56565;
  color: white;
}

.btn-danger:hover {
  background: #e53e3e;
}

.btn-rec {
  background: #ef4444;
  color: white;
  min-width: 200px;
  border: 2px solid #991b1b;
  text-shadow: 0 0 8px rgba(0, 0, 0, 0.8), 0 0 4px rgba(0, 0, 0, 0.6);
  filter: drop-shadow(0 0 6px rgba(0, 0, 0, 0.7));
  font-weight: 700;
}

.btn-rec:hover {
  background: #dc2626;
  border-color: #7f1d1d;
  text-shadow: 0 0 10px rgba(0, 0, 0, 0.9), 0 0 5px rgba(0, 0, 0, 0.7);
}


.btn-recording {
  background: #991b1b;
  color: white;
  min-width: 200px;
  animation: pulse-rec 1.5s ease-in-out infinite;
}

.btn-recording:hover {
  background: #7f1d1d;
}

.btn-snapshot {
  background: #8b5cf6;
  color: white;
  min-width: 150px;
}

.btn-snapshot:hover {
  background: #7c3aed;
}

.camera-selector {
  text-align: center;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.camera-selector label {
  display: block;
  margin-bottom: 10px;
  font-weight: bold;
  color: #333;
  font-size: 1.1em;
}

.camera-selector select {
  padding: 10px 15px;
  font-size: 1em;
  border: 2px solid #667eea;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: border-color 0.3s;
  min-width: 200px;
}

.camera-selector select:focus {
  outline: none;
  border-color: #5568d3;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

@keyframes pulse-rec {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@media (max-width: 768px) {
  .button-group, .action-group {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
