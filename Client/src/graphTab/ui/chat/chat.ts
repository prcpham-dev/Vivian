import './chat.css'
import { WS_URL, vscode } from '../api'
import { getSelectedNode } from '../graph/graph'

export function initChat() {
  const chatBtn = document.getElementById('chat-btn')!

  const chatDrawer = document.getElementById('chat-drawer')!
  const closeChatBtn = document.getElementById('close-chat-btn')!
  const clearChatBtn = document.getElementById('clear-chat-btn')!
  const chatMessages = document.getElementById('chat-messages')!
  const chatInput = document.getElementById('chat-input') as HTMLTextAreaElement
  const chatSendBtn = document.getElementById('chat-send-btn') as HTMLButtonElement
  const chatSettingsBtn = document.getElementById('chat-settings-btn')!
  const chatInputArea = document.getElementById('chat-input-area')!

  chatBtn.addEventListener('click', () => chatDrawer.classList.toggle('open'))
  closeChatBtn.addEventListener('click', () => chatDrawer.classList.remove('open'))

  const aiProviderCheckbox = document.getElementById('ai-provider-checkbox') as HTMLInputElement
  if (aiProviderCheckbox) {
    aiProviderCheckbox.checked = ((window as any).AI_PROVIDER !== 'External MCP Client')
    aiProviderCheckbox.addEventListener('change', () => {
      if (vscode) {
        const newVal = aiProviderCheckbox.checked ? 'Internal Vivian API' : 'External MCP Client'
        vscode.postMessage({ command: 'updateSetting', key: 'vivian.aiProvider', value: newVal })
      }
    })
  }

  if ((window as any).AI_PROVIDER === 'External MCP Client') {
    if (chatInputArea) chatInputArea.style.display = 'none'
    if (clearChatBtn) clearChatBtn.style.display = 'none'

    const div = document.createElement('div')
    div.className = 'chat-msg ai'
    div.innerHTML = `<div style="display:flex;flex-direction:column;gap:6px;align-items:start;white-space:normal;">
        <i style="color:var(--vscode-descriptionForeground);">Vivian's Built-in AI is currently disabled.</i>
        
        <h4 style="margin:6px 0 0 0;color:var(--vscode-foreground);font-size:12px;">External MCP Connection</h4>
        <p style="margin:4px 0;color:var(--vscode-descriptionForeground);font-size:11px;">You can connect Vivian to your external AI agent using the FastMCP server.</p>
        <button id="open-mcp-setup-btn" style="background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:none;padding:6px 12px;border-radius:2px;font-size:11px;cursor:pointer;margin-top:4px;">
          View Setup Instructions
        </button>
      </div>`
    chatMessages.appendChild(div)

    const setupBtn = div.querySelector('#open-mcp-setup-btn')
    if (setupBtn && vscode) {
      setupBtn.addEventListener('click', () => {
        vscode.postMessage({ command: 'openMcpSetup' })
      })
    }

    return
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      chatMessages.innerHTML = ''
    })
  }

  let ws: WebSocket | null = null
  let wsReady = false
  let currentAiMsg: HTMLElement | null = null

  function appendMsg(role: string, text: string) {
    const div = document.createElement('div')
    div.className = 'chat-msg ' + role
    div.textContent = text
    chatMessages.appendChild(div)
    chatMessages.scrollTop = chatMessages.scrollHeight
    return div
  }

  function appendStatus(text: string) {
    const div = document.createElement('div')
    div.className = 'chat-status'
    div.textContent = text
    chatMessages.appendChild(div)
    chatMessages.scrollTop = chatMessages.scrollHeight
    return div
  }

  function setSendEnabled(enabled: boolean) {
    chatSendBtn.disabled = !enabled
    chatInput.disabled = !enabled
  }

  function connectWs() {
    const statusEl = appendStatus('Connecting…')
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      ws!.send(JSON.stringify({ event: 'init' }))
    }

    ws.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      if (data.event === 'ready') {
        statusEl.remove()
        setSendEnabled(true)
        wsReady = true
      } else if (data.event === 'chatResponse') {
        if (!currentAiMsg) {
          currentAiMsg = appendMsg('ai', '')
          currentAiMsg.classList.add('streaming')
        }
        if (data.done) {
          currentAiMsg.classList.remove('streaming')
          currentAiMsg = null
          setSendEnabled(true)
        } else {
          currentAiMsg.textContent += data.text
          chatMessages.scrollTop = chatMessages.scrollHeight
        }
      } else if (data.event === 'error') {
        if (currentAiMsg) {
          currentAiMsg.classList.remove('streaming')
          currentAiMsg = null
        }
        appendMsg('ai', 'Error: ' + (data.message || 'unknown'))
        setSendEnabled(true)
      }
    }

    ws.onclose = () => {
      wsReady = false
      setSendEnabled(false)
      if (currentAiMsg) {
        currentAiMsg.classList.remove('streaming')
        currentAiMsg = null
      }
      appendStatus('Disconnected... reconnecting…')
      setTimeout(connectWs, 3000)
    }

    ws.onerror = () => ws!.close()
  }

  function sendMessage() {
    const text = chatInput.value.trim()
    if (!text || !wsReady || !ws) return
    appendMsg('user', text)
    chatInput.value = ''
    setSendEnabled(false)
    currentAiMsg = null

    const selectedNode = getSelectedNode()
    const node = selectedNode
      ? { id: selectedNode.id, label: selectedNode.label }
      : null

    ws.send(JSON.stringify({
      event: 'chat',
      workspace_root: WORKSPACE_ROOT,
      text: text,
      selected_node: node,
    }))
  }

  chatSendBtn.addEventListener('click', sendMessage)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  })

  setSendEnabled(false)
  connectWs()
}
