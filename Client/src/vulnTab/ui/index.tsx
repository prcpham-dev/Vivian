import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';

const vscode = typeof (window as any).acquireVsCodeApi === 'function' ? (window as any).acquireVsCodeApi() : null;
(window as any).vscode = vscode;

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<App />);
}
