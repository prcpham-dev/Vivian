import './base.css'
import { vscode } from './api'
import { initGraph, renderGraph } from './graph/graph'
import { initChat } from './chat/chat'
import { initSettings } from './settings/settings'
import { initTheme } from './themes/themes'

  ; (function () {
    'use strict'

    window.addEventListener('message', (event) => {
      const msg = event.data
      if (msg.command === 'loadGraph') renderGraph(msg.graph)
    })

    const vulnBtn = document.getElementById('switch-to-vuln-btn')!
    vulnBtn.addEventListener('click', () => {
      vscode.postMessage({ command: 'openVulnManager' })
    })

    initGraph()
    initTheme()
    initSettings()
    initChat()

    vscode.postMessage({ command: 'webviewReady' })
  })()
