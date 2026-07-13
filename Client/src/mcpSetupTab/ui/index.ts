const vscode = (window as any).acquireVsCodeApi?.() || null;

document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.getElementById('copy-config-btn');
  const copyDevBtn = document.getElementById('copy-dev-config-btn');
  const restartBtn = document.getElementById('restart-ide-btn');
  const writeGlobalRulesBtn = document.getElementById('write-global-rules-btn');
  const globalRulesStatus = document.getElementById('global-rules-status');

  const devTime = async () => { return "&nbsp;" }

  if (vscode) {
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        vscode.postMessage({ command: 'copyMcpConfig', type: 'extension' });
      });
    }
    if (copyDevBtn) {
      copyDevBtn.addEventListener('click', () => {
        vscode.postMessage({ command: 'copyMcpConfig', type: 'development' });
      });
    }
    if (restartBtn) {
      restartBtn.addEventListener('click', () => {
        vscode.postMessage({ command: 'restartIde' });
      });
    }
    if (writeGlobalRulesBtn) {
      writeGlobalRulesBtn.addEventListener('click', () => {
        vscode.postMessage({ command: 'writeGlobalRules' });
        if (globalRulesStatus) {
          globalRulesStatus.textContent = 'Writing…';
        }
      });
    }
  }

  // Listen for messages back from the extension
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.command === 'globalRulesResult') {
      if (globalRulesStatus) {
        if (msg.success) {
          globalRulesStatus.textContent = '✅ Written to ~/.gemini/config/AGENTS.md';
          globalRulesStatus.style.color = 'var(--vscode-testing-iconPassed)';
        } else {
          globalRulesStatus.textContent = `❌ Error: ${msg.error}`;
          globalRulesStatus.style.color = 'var(--vscode-testing-iconFailed)';
        }
      }
    }
  });
});
