import it from './it.json'
import en from './en.json'
import fr from './fr.json'
import de from './de.json'
import es from './es.json'

const messages = {
  it,
  en,
  fr,
  de,
  es
}

class I18n {
  constructor(locale = 'it') {
    this.locale = localStorage.getItem('app_language') || locale
    this.messages = messages
  }

  t(key) {
    const keys = key.split('.')
    let value = this.messages[this.locale]
    
    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k]
      } else {
        return key // Fallback: ritorna la chiave se non trovata
      }
    }
    
    return value || key
  }

  setLocale(locale) {
    if (this.messages[locale]) {
      this.locale = locale
      localStorage.setItem('app_language', locale)
      // Trigger reactivity in Vue
      window.dispatchEvent(new Event('language-changed'))
      return true
    }
    return false
  }

  getLocale() {
    return this.locale
  }

  getAvailableLocales() {
    return Object.keys(this.messages)
  }
}

export default new I18n()
