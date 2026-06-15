import { API_BASE, fetchJson } from './api'

export function initSettings() {
  const apiKeySection   = document.getElementById('api-key-section')!
  const apiKeyFormRow   = document.getElementById('api-key-form-row')!
  const apiKeyInput     = document.getElementById('api-key-input') as HTMLInputElement
  const apiKeySaveBtn   = document.getElementById('api-key-save-btn') as HTMLButtonElement
  const apiKeyStatus    = document.getElementById('api-key-status')!
  const apiKeyToggleBtn = document.getElementById('api-key-toggle-btn')!
  const modelSelect     = document.getElementById('model-select') as HTMLSelectElement
  const modelSaveBtn    = document.getElementById('model-save-btn') as HTMLButtonElement
  const modelSelectRow  = document.getElementById('model-select-row')!

  function setKeyFormVisible(visible: boolean) {
    apiKeyFormRow.style.display = visible ? 'flex' : 'none'
    modelSelectRow.style.display = visible ? 'flex' : 'none'
    apiKeyToggleBtn.textContent = visible ? '▲' : '▼'
  }

  async function loadSettings() {
    try {
      const data = await fetchJson('/settings/api-key')
      if (data.api_key_set) {
        apiKeyStatus.textContent = 'API key is set'
        setKeyFormVisible(false)
      } else {
        apiKeyStatus.textContent = 'No API key! Enter one to enable chat'
        setKeyFormVisible(true)
      }
      
      const modelData = await fetchJson('/settings/model')
      if (modelData.model) {
        modelSelect.value = modelData.model
      }
    } catch {
      apiKeyStatus.textContent = ''
    }
  }

  apiKeyToggleBtn.addEventListener('click', () => {
    setKeyFormVisible(apiKeyFormRow.style.display === 'none')
  })

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
        setKeyFormVisible(false)
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
