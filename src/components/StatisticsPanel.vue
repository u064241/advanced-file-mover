<template>
  <div class="statistics-panel">
    <div class="stats-header">
      <h2>📊 {{ i18n.t('statistics.title') }}</h2>
      <div class="stats-buttons">
        <button @click="downloadJSON" class="btn-export btn-json" title="JSON">
          📥 JSON
        </button>
        <button @click="downloadCSV" class="btn-export btn-csv" title="CSV">
          📥 CSV
        </button>
      </div>
    </div>

    <!-- Tab per Statistiche -->
    <div class="stats-tabs">
      <button 
        class="tab-button" 
        :class="{ active: activeTab === 'general' }"
        @click="activeTab = 'general'"
      >
        📊 Generale
      </button>
      <button 
        class="tab-button" 
        :class="{ active: activeTab === 'per-camera' }"
        @click="activeTab = 'per-camera'"
      >
        📷 Per-Camera
      </button>
    </div>

    <div v-if="loading" class="loading">{{ i18n.t('statistics.loading') }}</div>

    <div v-else class="stats-content">
      <!-- TAB: Statistiche Generali -->
      <div v-if="activeTab === 'general'">
        <!-- Statistiche Generali -->
        <div class="stats-section">
          <h3>{{ i18n.t('statistics.general') }}</h3>
          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-label">⏱️ {{ i18n.t('statistics.uptime') }}</div>
              <div class="stat-value">{{ formatUptime(currentUptimeSeconds) }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">📹 {{ i18n.t('statistics.totalRecordings') }}</div>
              <div class="stat-value">{{ stats.total_recordings || 0 }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">📸 {{ i18n.t('statistics.totalSnapshots') }}</div>
              <div class="stat-value">{{ stats.total_snapshots || 0 }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">📦 {{ i18n.t('statistics.totalSize') }}</div>
              <div class="stat-value">{{ formatSize(stats.total_recording_size) }}</div>
            </div>
          </div>
        </div>

        <!-- Tabella Registrazioni -->
        <div v-if="stats.recordings && stats.recordings.length > 0" class="stats-section">
          <h3>🎬 {{ i18n.t('statistics.recordings') }}</h3>
          <table class="stats-table">
            <thead>
              <tr>
                <th>{{ i18n.t('statistics.filename') }}</th>
                <th>{{ i18n.t('statistics.originalSize') }}</th>
                <th>{{ i18n.t('statistics.compressedSize') }}</th>
                <th>{{ i18n.t('statistics.compression') }}</th>
                <th>{{ i18n.t('statistics.timestamp') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in stats.recordings" :key="rec.filename">
                <td>{{ rec.filename }}</td>
                <td>{{ formatSize(rec.original_size) }}</td>
                <td>{{ formatSize(rec.compressed_size) }}</td>
                <td class="compression-ratio">{{ rec.compression_ratio.toFixed(1) }}%</td>
                <td>{{ formatDate(rec.timestamp) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Tabella Snapshot -->
        <div v-if="stats.snapshots && stats.snapshots.length > 0" class="stats-section">
          <h3>📸 {{ i18n.t('statistics.snapshots') }}</h3>
          <table class="stats-table">
            <thead>
              <tr>
                <th>{{ i18n.t('statistics.filename') }}</th>
                <th>{{ i18n.t('statistics.size') }}</th>
                <th>{{ i18n.t('statistics.timestamp') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="snap in stats.snapshots" :key="snap.filename">
                <td>{{ snap.filename }}</td>
                <td>{{ formatSize(snap.size) }}</td>
                <td>{{ formatDate(snap.timestamp) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!stats.recordings || stats.recordings.length === 0" class="empty-message">
          {{ i18n.t('statistics.noData') }}
        </div>
      </div>

      <!-- TAB: Statistiche Per-Camera -->
      <div v-else-if="activeTab === 'per-camera'">
        <div v-if="perCameraStats && Object.keys(perCameraStats).length > 0">
          <div v-if="perCameraStats['0']" :key="0" class="stats-section camera-section">
            <h3>📷 Camera Attiva</h3>
            <div class="stats-grid">
              <div class="stat-box">
                <div class="stat-label">⏱️ Uptime</div>
                <div class="stat-value">{{ formatUptime(perCameraCurrentUptime['0'] || 0) }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">📹 Registrazioni</div>
                <div class="stat-value">{{ perCameraStats['0'].recording_count }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">📸 Snapshot</div>
                <div class="stat-value">{{ perCameraStats['0'].snapshot_count }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">⏱️ Tempo Registrazione</div>
                <div class="stat-value">{{ perCameraStats['0'].total_recording_time_formatted }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">📊 FPS Medio</div>
                <div class="stat-value">{{ perCameraStats['0'].avg_fps }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">🖼️ Risoluzione</div>
                <div class="stat-value">{{ perCameraStats['0'].avg_resolution }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">💾 Registrazioni</div>
                <div class="stat-value">{{ formatSize(perCameraStats['0'].total_recording_size) }}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">💾 Snapshot</div>
                <div class="stat-value">{{ formatSize(perCameraStats['0'].total_snapshot_size) }}</div>
              </div>
            </div>

            <!-- Registrazioni per camera attiva -->
            <div v-if="perCameraStats['0'] && perCameraStats['0'].recordings && perCameraStats['0'].recordings.length > 0" class="camera-detail">
              <h4>Registrazioni Camera Attiva</h4>
              <table class="stats-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Durata</th>
                    <th>Originale</th>
                    <th>Compresso</th>
                    <th>Compression</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="rec in perCameraStats['0'].recordings" :key="rec.filename">
                    <td>{{ rec.filename }}</td>
                    <td>{{ formatUptime(rec.duration) }}</td>
                    <td>{{ formatSize(rec.original_size) }}</td>
                    <td>{{ formatSize(rec.compressed_size) }}</td>
                    <td class="compression-ratio">{{ rec.compression_ratio.toFixed(1) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Snapshot per camera attiva -->
            <div v-if="perCameraStats['0'] && perCameraStats['0'].snapshots && perCameraStats['0'].snapshots.length > 0" class="camera-detail">
              <h4>Snapshot Camera Attiva</h4>
              <table class="stats-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Dimensione</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="snap in perCameraStats['0'].snapshots" :key="snap.filename">
                    <td>{{ snap.filename }}</td>
                    <td>{{ formatSize(snap.size) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div v-else class="empty-message">
          Nessun dato per-camera disponibile
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'

export default {
  name: 'StatisticsPanel',
  props: {
    token: String
  },
  data() {
    return {
      i18n,
      stats: {},
      perCameraStats: {},
      perCameraBaseUptime: {},
      perCameraCurrentUptime: {},
      loading: true,
      baseUptimeSeconds: 0,
      lastRefreshTime: Date.now(),
      currentUptimeSeconds: 0,
      uptimeInterval: null,
      activeTab: 'general'
    }
  },
  mounted() {
    this.refreshStats()
    // Aggiorna l'uptime ogni secondo (generale e per-camera)
    this.uptimeInterval = setInterval(() => {
      const elapsedSeconds = (Date.now() - this.lastRefreshTime) / 1000
      this.currentUptimeSeconds = this.baseUptimeSeconds + elapsedSeconds
      
      // Aggiorna uptime per ogni camera
      Object.keys(this.perCameraBaseUptime).forEach(cameraIndex => {
        this.perCameraCurrentUptime[cameraIndex] = this.perCameraBaseUptime[cameraIndex] + elapsedSeconds
      })
    }, 1000)
    this.$root.$on('language-changed', () => {
      this.$forceUpdate()
    })
  },
  beforeDestroy() {
    if (this.uptimeInterval) {
      clearInterval(this.uptimeInterval)
    }
  },
  methods: {
    async refreshStats() {
      this.loading = true
      try {
        // Carica statistiche generali
        const response = await fetch('/api/statistics', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (response.ok) {
          this.stats = await response.json()
          this.baseUptimeSeconds = this.stats.uptime_seconds || 0
          this.currentUptimeSeconds = this.baseUptimeSeconds
          this.lastRefreshTime = Date.now()
        }

        // Carica statistiche per-camera
        const perCameraResponse = await fetch('/api/statistics/per-camera', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (perCameraResponse.ok) {
          const perCameraData = await perCameraResponse.json()
          this.perCameraStats = perCameraData.cameras || {}
          
          // Inizializza uptime base per ogni camera
          this.perCameraBaseUptime = {}
          this.perCameraCurrentUptime = {}
          Object.keys(this.perCameraStats).forEach(cameraIndex => {
            const baseUptime = this.perCameraStats[cameraIndex].uptime_seconds || 0
            this.perCameraBaseUptime[cameraIndex] = baseUptime
            this.perCameraCurrentUptime[cameraIndex] = baseUptime
          })
        }
      } catch (error) {
        console.error('Errore caricamento statistiche:', error)
      } finally {
        this.loading = false
      }
    },
    async downloadJSON() {
      try {
        const response = await fetch('/api/statistics/export?format=json', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (response.ok) {
          const blob = await response.blob()
          this.downloadBlob(blob, 'streaming-stats.json')
        }
      } catch (error) {
        console.error('Errore download JSON:', error)
      }
    },
    async downloadCSV() {
      try {
        const response = await fetch('/api/statistics/export?format=csv', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        if (response.ok) {
          const blob = await response.blob()
          this.downloadBlob(blob, 'streaming-stats.csv')
        }
      } catch (error) {
        console.error('Errore download CSV:', error)
      }
    },
    downloadBlob(blob, filename) {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    formatSize(bytes) {
      if (!bytes || bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    },
    formatUptime(seconds) {
      const totalSeconds = Math.floor(seconds || 0)
      const hours = Math.floor(totalSeconds / 3600)
      const minutes = Math.floor((totalSeconds % 3600) / 60)
      const secs = totalSeconds % 60
      
      return `${hours}h ${minutes}m ${secs}s`
    },
    formatDate(dateStr) {
      if (!dateStr) return 'N/A'
      try {
        const date = new Date(dateStr.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, '$1-$2-$3T$4:$5:$6'))
        return date.toLocaleString()
      } catch {
        return dateStr
      }
    }
  }
}
</script>

<style scoped>
.statistics-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 15px;
}

.stats-header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.stats-buttons {
  display: flex;
  gap: 10px;
}

.btn-export, .btn-refresh {
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-json {
  background: #4285f4;
  color: white;
}

.btn-json:hover {
  background: #357ae8;
  transform: translateY(-2px);
}

.btn-csv {
  background: #34a853;
  color: white;
}

.btn-csv:hover {
  background: #2d8659;
  transform: translateY(-2px);
}

/* Tab Styles */
.stats-tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

.tab-button {
  padding: 12px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-button:hover {
  color: #333;
  background: #f5f5f5;
}

.tab-button.active {
  color: #4285f4;
  border-bottom-color: #4285f4;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 16px;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.stats-section {
  background: #fafafa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #4285f4;
}

.stats-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-size: 18px;
}

.camera-section {
  border-left-color: #34a853;
}

.camera-detail {
  margin-top: 20px;
  padding: 15px;
  background: white;
  border-radius: 4px;
}

.camera-detail h4 {
  margin-top: 0;
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-box {
  background: white;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #4285f4;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 6px;
  overflow: hidden;
}

.stats-table thead {
  background: #f0f0f0;
}

.stats-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #ddd;
}

.stats-table td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.stats-table tbody tr:hover {
  background: #fafafa;
}

.compression-ratio {
  font-weight: 600;
  color: #34a853;
}

.empty-message {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}
</style>
