const vscode = (window as any).acquireVsCodeApi?.() || null;

document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.getElementById('copy-config-btn');
  const copyDevBtn = document.getElementById('copy-dev-config-btn');
  const restartBtn = document.getElementById('restart-ide-btn');

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
  }
});
