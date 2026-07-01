const vscode = (window as any).acquireVsCodeApi?.() || null;

document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.getElementById('copy-config-btn');
  if (copyBtn && vscode) {
    copyBtn.addEventListener('click', () => {
      vscode.postMessage({ command: 'copyMcpConfig' });
    });
  }
});
