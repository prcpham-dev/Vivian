import { API_BASE, fetchJson, vscode } from './api'

export function initSettings() {
  const apiKeySection   = document.getElementById('api-key-section')!
  const apiKeyInput     = document.getElementById('api-key-input') as HTMLInputElement
  const apiKeySaveBtn   = document.getElementById('api-key-save-btn') as HTMLButtonElement
  const apiKeyStatus    = document.getElementById('api-key-status')!
  const modelSelect     = document.getElementById('model-select') as HTMLSelectElement
  const modelSaveBtn    = document.getElementById('model-save-btn') as HTMLButtonElement
  const chatSettingsBtn = document.getElementById('chat-settings-btn')!
  const openProjectsBtn = document.getElementById('open-projects-btn')!

  chatSettingsBtn.addEventListener('click', () => {
    apiKeySection.style.display = apiKeySection.style.display === 'none' ? 'block' : 'none'
  })

  if (openProjectsBtn) {
    openProjectsBtn.addEventListener('click', () => {
      vscode.postMessage({ command: 'openProjectsFolder' })
    })
  }

  async function loadSettings() {
    try {
      const data = await fetchJson('/settings/api-key')
      if (data.api_key_set) {
        apiKeyStatus.textContent = 'API key is set'
      } else {
        apiKeyStatus.textContent = 'No API key! Enter one to enable chat'
      }
      
      const modelData = await fetchJson('/settings/model')
      if (modelData.model) {
        modelSelect.value = modelData.model
      }
    } catch {
      apiKeyStatus.textContent = ''
    }
  }

  apiKeySaveBtn.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim()
    if (!key) return
    apiKeySaveBtn.disabled = true
    apiKeyStatus.textContent = 'Saving…'
    try {
      const res = await fetch(API_BASE + '/settings/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key }),
      })
      if (res.ok) {
        apiKeyInput.value = ''
        apiKeyStatus.textContent = 'API key saved'
      } else {
        apiKeyStatus.textContent = 'Failed to save key'
      }
    } catch {
      apiKeyStatus.textContent = 'Error: is the server running?'
    } finally {
      apiKeySaveBtn.disabled = false
    }
  })

  apiKeyInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') apiKeySaveBtn.click()
  })

  modelSaveBtn.addEventListener('click', async () => {
    const selectedModel = modelSelect.value
    modelSaveBtn.disabled = true
    apiKeyStatus.textContent = 'Updating model...'
    try {
      const res = await fetch(API_BASE + '/settings/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedModel }),
      })
      if (res.ok) {
        apiKeyStatus.textContent = 'Model updated!'
      } else {
        apiKeyStatus.textContent = 'Failed to update model'
      }
    } catch {
      apiKeyStatus.textContent = 'Error: is the server running?'
    } finally {
      modelSaveBtn.disabled = false
    }
  })

  loadSettings()
}
