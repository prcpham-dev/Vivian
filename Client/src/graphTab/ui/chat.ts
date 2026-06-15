import { WS_URL, API_BASE } from './api'
import { getSelectedNode } from './graph'

export function initChat() {
  const chatBtn      = document.getElementById('chat-btn')!
  const chatDrawer   = document.getElementById('chat-drawer')!
  const closeChatBtn = document.getElementById('close-chat-btn')!
  const clearChatBtn = document.getElementById('clear-chat-btn')!
  const chatMessages = document.getElementById('chat-messages')!
  const chatInput    = document.getElementById('chat-input') as HTMLTextAreaElement
  const chatSendBtn  = document.getElementById('chat-send-btn') as HTMLButtonElement

  chatBtn.addEventListener('click', () => chatDrawer.classList.toggle('open'))
  closeChatBtn.addEventListener('click', () => chatDrawer.classList.remove('open'))

  clearChatBtn.addEventListener('click', async () => {
    if (!WORKSPACE_ROOT) return;
    try {
      const res = await fetch(`${API_BASE}/chat/clear?workspace_root=${encodeURIComponent(WORKSPACE_ROOT)}`, {
        method: 'POST'
      });
      if (res.ok) {
        chatMessages.innerHTML = '';
        appendStatus('Chat history cleared.');
      }
    } catch (err) {
      appendStatus('Error clearing chat history.');
    }
  });

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
