<template>
  <div class="admin-panel">
    <div class="admin-tabs">
      <button 
        @click="activeTab = 'users'" 
        :class="['tab-button', { active: activeTab === 'users' }]"
      >
        👥 {{ i18n.t('admin.users') }}
      </button>
      <button 
        @click="activeTab = 'statistics'" 
        :class="['tab-button', { active: activeTab === 'statistics' }]"
      >
        📊 {{ i18n.t('statistics.title') }}
      </button>
      <button 
        @click="activeTab = 'storage'" 
        :class="['tab-button', { active: activeTab === 'storage' }]"
      >
        💾 Storage
      </button>
    </div>

    <!-- TAB: Utenti -->
    <div v-if="activeTab === 'users'" class="admin-content">
      <h2>⚙️ {{ i18n.t('admin.users') }}</h2>
      
      <div class="admin-section">
        <h3>👥 {{ i18n.t('admin.users') }}</h3>
        
        <div class="user-table">
          <table>
            <thead>
              <tr>
                <th>{{ i18n.t('admin.username') }}</th>
                <th>{{ i18n.t('admin.role') }}</th>
                <th>{{ i18n.t('admin.forceChange') }}</th>
                <th>{{ i18n.t('messages.unknownError') === 'Errore sconosciuto' ? 'Azioni' : 'Actions' }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.username">
                <td>{{ user.username }}</td>
                <td>
                  <span :class="['role-badge', user.role]">
                    {{ user.role === 'admin' ? '👑 ' + i18n.t('admin.admin') : '👤 ' + i18n.t('admin.user') }}
                  </span>
                </td>
                <td>
                  <span :class="['flag-badge', user.must_change_password ? 'on' : 'off']">
                    {{ user.must_change_password ? i18n.t('messages.success') : 'No' }}
                  </span>
                </td>
                <td>
                  <button @click="editUser(user)" class="btn-edit">✏️ {{ i18n.t('admin.editUser') }}</button>
                  <button @click="deleteUser(user.username)" class="btn-delete">🗑️ {{ i18n.t('admin.deleteUser') }}</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <button @click="showAddUser = true" class="btn-add">➕ {{ i18n.t('admin.addUser') }}</button>
      </div>

      <!-- Modal Aggiungi/Modifica Utente -->
      <div v-if="showAddUser || editingUser" class="modal" @click.self="closeModal">
        <div class="modal-content">
          <h3>{{ editingUser ? '✏️ ' + i18n.t('admin.editUser') : '➕ ' + i18n.t('admin.addUser') }}</h3>
          
          <form @submit.prevent="saveUser">
            <div class="form-group">
              <label>{{ i18n.t('admin.username') }}:</label>
              <input 
                type="text" 
                v-model="userForm.username" 
                :disabled="!!editingUser"
                required
              />
            </div>
          
            <div class="form-group">
              <label>{{ i18n.t('password.new') }} (reset):</label>
              <input 
                type="password" 
                v-model="userForm.password" 
                :placeholder="editingUser ? i18n.t('admin.close') : i18n.t('password.new')"
                :required="!editingUser"
              />
              <small v-if="editingUser" class="hint">{{ i18n.t('admin.forceChange') }}</small>
            </div>

            <div class="form-group inline">
              <label class="inline-label">
                <input type="checkbox" v-model="userForm.must_change_password" />
                {{ i18n.t('admin.forceChange') }}
              </label>
            </div>
          
            <div class="form-group">
              <label>{{ i18n.t('admin.role') }}:</label>
              <select v-model="userForm.role" required>
                <option value="user">👤 {{ i18n.t('admin.user') }}</option>
                <option value="admin">👑 {{ i18n.t('admin.admin') }}</option>
              </select>
            </div>
          
            <div class="modal-actions">
              <button type="submit" class="btn-save">💾 {{ i18n.t('admin.save') }}</button>
              <button type="button" @click="closeModal" class="btn-cancel">❌ {{ i18n.t('admin.cancel') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- TAB: Statistiche -->
    <div v-if="activeTab === 'statistics'" class="admin-content">
      <StatisticsPanel :token="token" />
    </div>

    <!-- TAB: Storage -->
    <div v-if="activeTab === 'storage'" class="admin-content">
      <div class="storage-panel">
        <h2>💾 Storage & Disk Management</h2>
        
        <div class="storage-info">
          <div v-if="diskStatus" class="disk-status-card">
            <h3>Stato Disco</h3>
            
            <!-- Status Badge -->
            <div class="status-badge" :class="diskStatus.disk_status.toLowerCase()">
              {{ diskStatus.disk_status === 'OK' ? '✅ OK' : 
                 diskStatus.disk_status === 'WARNING' ? '⚠️ WARNING' : '🔴 CRITICAL' }}
            </div>
            
            <!-- Warning Message -->
            <div v-if="diskStatus.warning" class="warning-message">
              {{ diskStatus.warning }}
            </div>
            
            <!-- Storage Info Grid -->
            <div class="storage-grid">
              <div class="storage-item">
                <div class="label">Spazio Libero</div>
                <div class="value">{{ formatBytes(diskStatus.disk_free) }}</div>
                <div class="percent">{{ diskStatus.percent_free }}% libero</div>
              </div>
              
              <div class="storage-item">
                <div class="label">Spazio Totale</div>
                <div class="value">{{ formatBytes(diskStatus.disk_total) }}</div>
              </div>
              
              <div class="storage-item">
                <div class="label">Registrazioni</div>
                <div class="value">{{ formatBytes(diskStatus.recordings_used) }}</div>
              </div>
              
              <div class="storage-item">
                <div class="label">Snapshot</div>
                <div class="value">{{ formatBytes(diskStatus.snapshots_used) }}</div>
              </div>
            </div>
            
            <!-- Disk Usage Bar -->
            <div class="disk-usage-bar">
              <div class="usage" :style="{ width: diskStatus.percent_used + '%' }"></div>
            </div>
            <div class="usage-text">
              Usato: {{ diskStatus.percent_used }}% ({{ formatBytes(diskStatus.disk_total - diskStatus.disk_free) }} / {{ formatBytes(diskStatus.disk_total) }})
            </div>
          </div>
        </div>
        
        <!-- Cleanup Controls -->
        <div class="cleanup-section">
          <h3>🧹 Pulizia Files</h3>
          <p>Rimuovi file più vecchi di 30 giorni</p>
          <button @click="triggerCleanup" :disabled="cleaning" class="btn-cleanup">
            {{ cleaning ? '⏳ In corso...' : '🧹 Pulisci Files Vecchi' }}
          </button>
          <div v-if="cleanupResult" class="cleanup-result" :class="cleanupResult.success ? 'success' : 'error'">
            {{ cleanupResult.message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'
import StatisticsPanel from './StatisticsPanel.vue'

export default {
  name: 'AdminPanel',
  components: {
    StatisticsPanel
  },
  props: ['token'],
  data() {
    return {
      i18n,
      activeTab: 'users',
      users: [],
      showAddUser: false,
      editingUser: null,
      diskStatus: null,
      cleaning: false,
      cleanupResult: null,
      userForm: {
        username: '',
        password: '',
        role: 'user',
        must_change_password: false
      }
    }
  },
  mounted() {
    this.loadUsers()
    this.loadDiskStatus()
    window.addEventListener('language-changed', this.onLanguageChanged)
  },
  beforeUnmount() {
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  methods: {
    onLanguageChanged() {
      this.$forceUpdate()
    },
    async loadDiskStatus() {
      try {
        const res = await fetch('/api/disk-status', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        this.diskStatus = await res.json()
      } catch (error) {
        console.error('Errore caricamento disk status:', error)
      }
    },
    async loadUsers() {
      try {
        const res = await fetch('/api/admin/users', {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        const data = await res.json()
        this.users = data.users
      } catch (error) {
        console.error('Errore caricamento utenti:', error)
      }
    },
    formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    },
    async triggerCleanup() {
      this.cleaning = true
      this.cleanupResult = null
      
      try {
        const res = await fetch('/api/disk-cleanup', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ days: 30 })
        })
        
        const data = await res.json()
        
        if (data.success) {
          this.cleanupResult = {
            success: true,
            message: `✅ Ripuliti ${data.removed_count} file (${this.formatBytes(data.removed_size)} liberati)`
          }
          // Ricarica lo stato disco
          setTimeout(() => this.loadDiskStatus(), 1000)
        } else {
          this.cleanupResult = {
            success: false,
            message: '❌ Errore durante la pulizia'
          }
        }
      } catch (error) {
        console.error('Errore cleanup:', error)
        this.cleanupResult = {
          success: false,
          message: `❌ Errore: ${error.message}`
        }
      } finally {
        this.cleaning = false
      }
    },
    editUser(user) {
      this.editingUser = user
      this.userForm = {
        username: user.username,
        password: '',
        role: user.role,
        must_change_password: !!user.must_change_password
      }
    },
    closeModal() {
      this.showAddUser = false
      this.editingUser = null
      this.userForm = {
        username: '',
        password: '',
        role: 'user',
        must_change_password: false
      }
    },
    async saveUser() {
      try {
        let url, method, body
        
        if (this.editingUser) {
          // Modifica utente
          url = `/api/admin/users/${this.userForm.username}`
          method = 'PUT'
          body = {
            role: this.userForm.role,
            must_change_password: this.userForm.must_change_password
          }
          if (this.userForm.password) {
            body.password = this.userForm.password
          }
        } else {
          // Nuovo utente
          url = '/api/admin/users'
          method = 'POST'
          body = {
            username: this.userForm.username,
            password: this.userForm.password,
            role: this.userForm.role,
            must_change_password: this.userForm.must_change_password
          }
        }
        
        const res = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify(body)
        })
        
        const data = await res.json()
        
        if (res.ok) {
          this.closeModal()
          this.loadUsers()
        }
      } catch (error) {
        console.error('Errore salvataggio utente:', error)
      }
    },
    async deleteUser(username) {
      try {
        const res = await fetch(`/api/admin/users/${username}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        
        if (res.ok) {
          this.loadUsers()
        }
      } catch (error) {
        console.error('Errore eliminazione utente:', error)
      }
    }
  }
}
</script>

<style scoped>
.admin-panel {
  background: #f8f9fa;
  padding: 30px;
  border-radius: 10px;
}

.admin-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
  border-bottom: 2px solid #ddd;
}

.tab-button {
  padding: 12px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-button:hover {
  color: #333;
}

.tab-button.active {
  color: #4285f4;
  border-bottom-color: #4285f4;
}

.admin-content {
  background: white;
  padding: 25px;
  border-radius: 10px;
}

h2 {
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.admin-section {
  background: white;
  padding: 25px;
  border-radius: 10px;
}

h3 {
  color: #555;
  margin-bottom: 20px;
}

.user-table {
  overflow-x: auto;
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #667eea;
  color: white;
}

th, td {
  padding: 15px;
  text-align: left;
}

th {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.9em;
}

tbody tr {
  border-bottom: 1px solid #eee;
}

tbody tr:hover {
  background: #f8f9fa;
}

.role-badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 15px;
  font-size: 0.9em;
  font-weight: 600;
}

.role-badge.admin {
  background: #f59e0b;
  color: white;
}

.role-badge.user {
  background: #667eea;
  color: white;
}

.flag-badge {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.9em;
}

.flag-badge.on {
  background: #10b981;
  color: white;
}

.flag-badge.off {
  background: #e5e7eb;
  color: #374151;
}

.btn-edit, .btn-delete, .btn-add {
  padding: 8px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  margin-right: 10px;
}

.btn-edit {
  background: #3b82f6;
  color: white;
}

.btn-edit:hover {
  background: #2563eb;
  transform: translateY(-2px);
}

.btn-delete {
  background: #ef4444;
  color: white;
}

.btn-delete:hover {
  background: #dc2626;
  transform: translateY(-2px);
}

.btn-add {
  background: #10b981;
  color: white;
  padding: 12px 24px;
  font-size: 1em;
}

.btn-add:hover {
  background: #059669;
  transform: translateY(-2px);
}

/* Modal */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 15px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal-content h3 {
  margin-bottom: 25px;
  color: #333;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group.inline {
  display: flex;
  align-items: center;
}

.inline-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #444;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 600;
}

.hint {
  display: block;
  color: #6b7280;
  margin-top: 6px;
  font-size: 0.85em;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1em;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.modal-actions {
  display: flex;
  gap: 15px;
  margin-top: 25px;
}

.btn-save, .btn-cancel {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1em;
  transition: all 0.3s ease;
}

.btn-save {
  background: #10b981;
  color: white;
}

.btn-save:hover {
  background: #059669;
  transform: translateY(-2px);
}

.btn-cancel {
  background: #6b7280;
  color: white;
}

.btn-cancel:hover {
  background: #4b5563;
  transform: translateY(-2px);
}

/* Storage Panel Styles */
.storage-panel {
  max-width: 900px;
}

.storage-info {
  margin-bottom: 30px;
}

.disk-status-card {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.disk-status-card h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
  font-size: 20px;
}

.status-badge {
  display: inline-block;
  padding: 10px 20px;
  border-radius: 20px;
  font-weight: 700;
  font-size: 1.1em;
  margin-bottom: 15px;
}

.status-badge.ok {
  background: #10b981;
  color: white;
}

.status-badge.warning {
  background: #f59e0b;
  color: white;
}

.status-badge.critical {
  background: #ef4444;
  color: white;
  animation: pulse-critical 2s ease-in-out infinite;
}

@keyframes pulse-critical {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.warning-message {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 6px;
  color: #92400e;
  font-weight: 600;
}

.storage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 25px;
}

.storage-item {
  background: #f9fafb;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.storage-item .label {
  font-size: 0.9em;
  color: #6b7280;
  margin-bottom: 8px;
  font-weight: 600;
}

.storage-item .value {
  font-size: 1.5em;
  font-weight: 700;
  color: #111827;
  margin-bottom: 5px;
}

.storage-item .percent {
  font-size: 0.85em;
  color: #10b981;
  font-weight: 600;
}

.disk-usage-bar {
  width: 100%;
  height: 30px;
  background: #e5e7eb;
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 10px;
}

.disk-usage-bar .usage {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #3b82f6);
  transition: width 0.5s ease;
}

.usage-text {
  text-align: center;
  color: #6b7280;
  font-weight: 600;
  font-size: 0.9em;
}

.cleanup-section {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.cleanup-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
}

.cleanup-section p {
  color: #6b7280;
  margin-bottom: 20px;
}

.btn-cleanup {
  background: #f59e0b;
  color: white;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1em;
  transition: all 0.3s ease;
}

.btn-cleanup:hover:not(:disabled) {
  background: #d97706;
  transform: translateY(-2px);
}

.btn-cleanup:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.cleanup-result {
  margin-top: 15px;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 600;
}

.cleanup-result.success {
  background: #d1fae5;
  color: #065f46;
  border-left: 4px solid #10b981;
}

.cleanup-result.error {
  background: #fee2e2;
  color: #991b1b;
  border-left: 4px solid #ef4444;
}
</style>
