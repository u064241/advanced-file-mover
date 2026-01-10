<template>
  <div class="change-password-wrapper">
    <button @click="showModal = true" class="btn-change-pw">
      🔐 {{ i18n.t('password.change') }}
    </button>

    <div v-if="showModal" class="modal" @click.self="closeModal">
      <div class="modal-content">
        <h3>🔐 {{ i18n.t('password.change') }}</h3>
        
        <form @submit.prevent="submitChange">
          <div class="form-group">
            <label>{{ i18n.t('password.old') }}:</label>
            <input 
              type="password" 
              v-model="formData.oldPassword"
              :placeholder="i18n.t('password.old')"
              required
            >
          </div>
          
          <div class="form-group">
            <label>{{ i18n.t('password.new') }}:</label>
            <input 
              type="password" 
              v-model="formData.newPassword"
              :placeholder="i18n.t('password.new')"
              @input="validatePassword"
              required
              minlength="6"
            >
            <small v-if="formData.newPassword" :class="['password-strength', strengthClass]">
              {{ passwordStrength }}
            </small>
          </div>
          
          <div class="form-group">
            <label>{{ i18n.t('password.confirm') }}:</label>
            <input 
              type="password" 
              v-model="formData.confirmPassword"
              :placeholder="i18n.t('password.confirm')"
              required
              minlength="6"
            >
            <small v-if="formData.newPassword && formData.confirmPassword && formData.newPassword !== formData.confirmPassword" class="error">
              ❌ {{ i18n.t('password.mismatch') }}
            </small>
            <small v-else-if="formData.newPassword && formData.confirmPassword" class="success">
              ✅ OK
            </small>
          </div>

          <div v-if="error" class="alert alert-error">
            {{ error }}
          </div>

          <div v-if="success" class="alert alert-success">
            ✅ {{ success }}
          </div>

          <div class="modal-actions">
            <button type="submit" :disabled="!isFormValid" class="btn-save">
              {{ isLoading ? '⏳ ' + i18n.t('messages.loading') : '💾 ' + i18n.t('password.save') }}
            </button>
            <button type="button" @click="closeModal" class="btn-cancel">❌ {{ i18n.t('admin.cancel') }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '../i18n/index.js'

export default {
  name: 'ChangePassword',
  props: ['token', 'username'],
  data() {
    return {
      i18n,
      showModal: false,
      formData: {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      error: '',
      success: '',
      isLoading: false,
      passwordStrength: 'Debole',
      strengthClass: 'weak'
    }
  },
  mounted() {
    window.addEventListener('language-changed', this.onLanguageChanged)
  },
  beforeUnmount() {
    window.removeEventListener('language-changed', this.onLanguageChanged)
  },
  computed: {
    isFormValid() {
      return this.formData.oldPassword &&
             this.formData.newPassword &&
             this.formData.confirmPassword &&
             this.formData.newPassword === this.formData.confirmPassword &&
             this.formData.newPassword.length >= 6 &&
             !this.isLoading
    }
  },
  methods: {
    onLanguageChanged() {
      this.$forceUpdate()
    },
    validatePassword() {
      const pwd = this.formData.newPassword
      
      if (pwd.length < 6) {
        this.passwordStrength = 'Troppo corta'
        this.strengthClass = 'weak'
      } else if (pwd.length < 8) {
        this.passwordStrength = 'Debole'
        this.strengthClass = 'weak'
      } else if (/^[a-z0-9]+$/.test(pwd)) {
        this.passwordStrength = 'Media'
        this.strengthClass = 'medium'
      } else if (/[A-Z]/.test(pwd) && /[0-9]/.test(pwd) && /[!@#$%^&*]/.test(pwd)) {
        this.passwordStrength = 'Molto Forte'
        this.strengthClass = 'strong'
      } else if (/[A-Z]/.test(pwd) || /[0-9]/.test(pwd)) {
        this.passwordStrength = 'Forte'
        this.strengthClass = 'strong'
      } else {
        this.passwordStrength = 'Media'
        this.strengthClass = 'medium'
      }
    },
    async submitChange() {
      this.error = ''
      this.success = ''
      this.isLoading = true

      try {
        const res = await fetch('/api/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            old_password: this.formData.oldPassword,
            new_password: this.formData.newPassword
          })
        })

        const data = await res.json()

        if (res.ok) {
          this.success = this.i18n.t('password.success')
          setTimeout(() => {
            this.closeModal()
          }, 1500)
        } else {
          this.error = data.error || this.i18n.t('password.error')
        }
      } catch (error) {
        this.error = 'Errore di connessione'
        console.error('Errore:', error)
      } finally {
        this.isLoading = false
      }
    },
    closeModal() {
      this.showModal = false
      this.formData = {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
      this.error = ''
      this.success = ''
      this.passwordStrength = 'Debole'
      this.strengthClass = 'weak'
    }
  }
}
</script>

<style scoped>
.change-password-wrapper {
  display: inline-block;
}

.btn-change-pw {
  padding: 8px 16px;
  background: #8b5cf6;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  font-size: 0.9em;
}

.btn-change-pw:hover {
  background: #7c3aed;
  transform: translateY(-2px);
}

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
  max-width: 450px;
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

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1em;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.form-group input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 5px;
  font-size: 0.85em;
}

.password-strength {
  font-weight: 600;
}

.password-strength.weak {
  color: #dc2626;
}

.password-strength.medium {
  color: #f59e0b;
}

.password-strength.strong {
  color: #10b981;
}

.success {
  color: #10b981;
  font-weight: 600;
}

.error {
  color: #dc2626;
  font-weight: 600;
}

.alert {
  padding: 12px 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  text-align: center;
  font-weight: 600;
}

.alert-success {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
}

.alert-error {
  background: #fee2e2;
  color: #7f1d1d;
  border: 1px solid #fca5a5;
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

.btn-save:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-2px);
}

.btn-save:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-cancel {
  background: #6b7280;
  color: white;
}

.btn-cancel:hover {
  background: #4b5563;
  transform: translateY(-2px);
}
</style>
