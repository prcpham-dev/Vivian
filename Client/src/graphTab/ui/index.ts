import './style.css'
import { vscode } from './api'
import { initGraph, renderGraph } from './graph'
import { initChat } from './chat'
import { initSettings } from './settings'
import { initTheme } from './themes'

;(function () {
  'use strict'

  window.addEventListener('message', (event) => {
    const msg = event.data
    if (msg.command === 'loadGraph') renderGraph(msg.graph)
  })

  document.getElementById('switch-to-vuln-btn')!.addEventListener('click', () => {
    vscode.postMessage({ command: 'openVulnManager' })
  })

  initGraph()
  initTheme()
  initSettings()
  initChat()

  // Signal to the extension that the webview is ready to receive graph data
  vscode.postMessage({ command: 'webviewReady' })
})()
