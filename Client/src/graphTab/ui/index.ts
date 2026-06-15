import './style.css';
import { vscode } from './api';
import { initGraph, renderGraph } from './graph';
import { initChat } from './chat';
import { initSettings } from './settings';

(function () {
  'use strict';

  // Listen for messages from VS Code
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.command === 'loadGraph') renderGraph(msg.graph);
  });

  document.getElementById('switch-to-vuln-btn')!.addEventListener('click', () => {
    vscode.postMessage({ command: 'openVulnManager' });
  });

  // Initialize components
  initGraph();
  initSettings();
  initChat();
})();
