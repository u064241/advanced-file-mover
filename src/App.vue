<template>
  <div id="app">
    <div class="header">
      <h1>🎥 {{ i18n.t('app.title') }}</h1>
      <div class="user-info">
        <span>👤 {{ username }}</span>
        <div class="language-switcher">
          <button 
            @click="toggleLanguageMenu"
            class="btn-language"
            :title="`${currentLanguageName}`"
          >
            <img :src="currentLanguageFlag" :alt="currentLanguageName" class="flag-img">
          </button>
          <div v-if="showLanguageMenu" class="language-menu">
            <button 
              v-for="lang in availableLanguages"
              :key="lang.code"
              @click="switchLanguage(lang.code)"
              :class="{ active: i18n.getLocale() === lang.code }"
              class="lang-option"
            >
              <img :src="lang.flag" :alt="lang.code" class="flag-img-small">
              {{ lang.name }}
            </button>
          </div>
        </div>
        <ChangePassword :token="token" :username="username" />
        <button v-if="isAdmin" @click="showAdminPanel = !showAdminPanel" class="btn-admin">
          {{ showAdminPanel ? '📹 ' + i18n.t('header.camera') : i18n.t('header.admin') }}
        </button>
        <button @click="handleLogout" class="btn-logout">{{ i18n.t('header.logout') }}</button>
      </div>
    </div>

    <AdminPanel v-if="showAdminPanel" :token="token" />

    <div v-else>
      <div class="stream-container">
        <img v-if="!useWebSocket" :src="streamUrl" :alt="i18n.t('streaming.streamError')" @error="onStreamError" />
        <canvas v-else ref="wsCanvas" class="ws-canvas"></canvas>
        <div class="recording-indicator" v-if="recording">
          <span class="recording-dot"></span> {{ i18n.t('streaming.rec') }}
        </div>
      </div>

      <StreamSettings 
        :token="token" 
        :fps="fps" 
        :quality="quality"
        @settings-changed="onSettingsChanged" 
      />

      <CameraControls 
        :token="token" 
        :recording="recording"
        @camera-switched="onCameraSwitched"
        @recording-changed="onRecordingChanged"
        @snapshot-taken="onSnapshotTaken"
      />

      <AIControls :token="token" />
    </div>
  </div>
</template>

<script>
import CameraControls from './components/CameraControls.vue'
import StreamSettings from './components/StreamSettings.vue'
import AdminPanel from './components/AdminPanel.vue'
import ChangePassword from './components/ChangePassword.vue'
import AIControls from './components/AIControls.vue'
import i18n from './i18n/index.js'
import io from 'socket.io-client'

// Importa le bandiere
import itFlag from './assets/flags/it.png'
import enFlag from './assets/flags/en.png'
import frFlag from './assets/flags/fr.png'
import deFlag from './assets/flags/de.png'
import esFlag from './assets/flags/es.png'

export default {
  name: 'App',
  components: {
    CameraControls,
    StreamSettings,
    AdminPanel,
    ChangePassword,
    AIControls
  },
  data() {
    const token = (window.__APP_CONFIG__ && window.__APP_CONFIG__.token) || new URLSearchParams(window.location.search).get("token") || '';
    return {
      i18n,
      token: token,
      username: (window.__APP_CONFIG__ && window.__APP_CONFIG__.username) || 'User',
      isAdmin: (window.__APP_CONFIG__ && !!window.__APP_CONFIG__.is_admin) || new URLSearchParams(window.location.search).get("is_admin") === 'true',
      streamUrl: `/stream?token=${token}`,
      useWebSocket: false,
      socket: null,
      recording: false,
      fps: 30,
      quality: 70,
      showAdminPanel: false,
      showLanguageMenu: false,
      availableLanguages: [
        { code: 'it', name: 'Italiano', flag: itFlag },
        { code: 'en', name: 'English', flag: enFlag },
        { code: 'fr', name: 'Français', flag: frFlag },
        { code: 'de', name: 'Deutsch', flag: deFlag },
        { code: 'es', name: 'Español', flag: esFlag }
      ]
    }
  },
  computed: {
    currentLanguageFlag() {
      const lang = this.availableLanguages.find(l => l.code === this.i18n.getLocale())
      return lang ? lang.flag : itFlag
    },
    currentLanguageName() {
      const lang = this.availableLanguages.find(l => l.code === this.i18n.getLocale())
      return lang ? lang.name : 'Italiano'
    }
  },
  mounted() {
    this.loadSettings()
    this.checkRecordingStatus()
    // Ascolta cambiamenti di lingua
    window.addEventListener('language-changed', this.onLanguageChanged)
    // Uncomment to enable WebSocket streaming
    // this.initWebSocket()
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.disconnect()
    }
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  methods: {
    toggleLanguageMenu() {
      this.showLanguageMenu = !this.showLanguageMenu
    },
    switchLanguage(code) {
      this.i18n.setLocale(code)
      this.showLanguageMenu = false
      this.$forceUpdate()
    },
    onLanguageChanged() {
      this.$forceUpdate()
    },
    async loadSettings() {
      try {
        const res = await fetch('/api/settings', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        const data = await res.json()
        this.fps = data.fps
        this.quality = data.quality
      } catch (error) {
        console.error('Errore caricamento impostazioni:', error)
      }
    },
    async checkRecordingStatus() {
      try {
        const res = await fetch('/api/recording/status', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        const data = await res.json()
        this.recording = data.recording
      } catch (error) {
        console.error('Errore controllo stato registrazione:', error)
      }
    },
    initWebSocket() {
      this.socket = io('http://localhost:5000')
      
      this.socket.on('connect', () => {
        console.log('WebSocket connesso')
        this.socket.emit('start_stream', { token: this.token })
      })
      
      this.socket.on('frame', (data) => {
        const canvas = this.$refs.wsCanvas
        if (!canvas) return
        
        const ctx = canvas.getContext('2d')
        const img = new Image()
        img.onload = () => {
          canvas.width = img.width
          canvas.height = img.height
          ctx.drawImage(img, 0, 0)
        }
        img.src = 'data:image/jpeg;base64,' + data.data
      })
      
      this.socket.on('error', (data) => {
        console.error('WebSocket error:', data.message)
      })
      
      this.useWebSocket = true
    },
    onCameraSwitched() {
      this.streamUrl = `/stream?token=${this.token}&t=${Date.now()}`
    },
    onRecordingChanged(isRecording) {
      this.recording = isRecording
    },
    onSettingsChanged(settings) {
      this.fps = settings.fps
      this.quality = settings.quality
    },
    onSnapshotTaken(filename) {
      alert(`Snapshot salvato: ${filename}`)
    },
    onStreamError() {
      console.error('Errore caricamento stream')
    },
    handleLogout() {
      // Chiudi WebSocket se attivo
      if (this.socket) {
        this.socket.disconnect()
        this.socket = null
      }
      
      // Attendi un momento per chiudere connessioni pulite
      setTimeout(() => {
        window.location.href = '/logout'
      }, 100)
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

#app {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 30px;
  max-width: 1200px;
  width: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #eee;
}

h1 {
  color: #333;
  font-size: 2em;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-info span {
  color: #666;
  font-weight: 500;
}

.btn-language {
  padding: 8px 12px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-language:hover {
  background: #059669;
  transform: translateY(-2px);
}

.flag-img {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: block;
  outline: none;
  border: none;
  box-shadow: none;
}

.flag-img-small {
  width: 24px;
  height: 24px;
  border-radius: 3px;
  display: block;
  outline: none;
  border: none;
  box-shadow: none;
}

.language-switcher {
  position: relative;
}

.language-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 5px;
  margin-top: 5px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  min-width: 180px;
}

.lang-option {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 10px 15px;
  background: white;
  border: none;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: 500;
  gap: 10px;
}

.lang-option:hover {
  background: #f0fdf4;
}

.lang-option.active {
  background: #d1fae5;
  font-weight: 700;
  color: #059669;
}

/* Base per tutti i bottoni/link stile bottone: bordo trasparente per evitare shift al hover */
button,
a[class^="btn-"],
a[class*=" btn-"],
.tab-button,
.lang-option {
  border: 2px solid transparent;
  box-sizing: border-box;
  transition: border-color 0.08s linear, box-shadow 0.08s linear;
}

.lang-option:first-child {
  border-radius: 5px 5px 0 0;
}

.lang-option:last-child {
  border-radius: 0 0 5px 5px;
}

.btn-admin {
  padding: 8px 16px;
  background: #f59e0b;
  color: white;
  border: 2px solid transparent;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.btn-admin:hover {
  background: #d97706;
  transform: none;
}

.btn-logout {
  padding: 8px 16px;
  background: #ef4444;
  color: white;
  text-decoration: none;
  border: 2px solid transparent;
  border-radius: 5px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.btn-logout:hover {
  background: #dc2626;
  transform: none;
}

button:not(:disabled):hover,
a[class^="btn-"]:hover,
a[class*=" btn-"]:hover,
.tab-button:hover,
.lang-option:hover {
  outline: none !important;
  border-color: #ffffff !important;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.5) !important;
  transform: none !important;
}

/* Stato focus: mantiene il bordo bianco finché il bottone resta attivo/focusato (comportamento simile alle textbox di login) */
button:not(:disabled):focus-visible,
a[class^="btn-"]:focus-visible,
a[class*=" btn-"]:focus-visible,
.tab-button:focus-visible,
.lang-option:focus-visible {
  outline: none !important;
  border-color: #ffffff !important;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.5) !important;
  transform: none !important;
}

.stream-container {
  position: relative;
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  margin-bottom: 20px;
}

.stream-container img,
.ws-canvas {
  width: 100%;
  height: auto;
  display: block;
}

.recording-indicator {
  position: absolute;
  top: 15px;
  right: 15px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: pulse 1.5s ease-in-out infinite;
}

.recording-dot {
  width: 12px;
  height: 12px;
  background: white;
  border-radius: 50%;
  animation: blink 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
