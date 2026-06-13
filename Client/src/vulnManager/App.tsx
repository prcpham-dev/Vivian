import React, { useState } from 'react';
import { AlertTriangle, FileText, CheckCircle, Github } from 'lucide-react';

export default function App() {
  const [currentFileIndex, setCurrentFileIndex] = useState(0);

  const demoFiles = [
    { name: 'auth.ts', path: 'src/lib/auth.ts', status: 'completed', severity: 'high' },
    { name: 'userRoute.ts', path: 'src/api/userRoute.ts', status: 'completed', severity: 'medium' },
    { name: 'utils.ts', path: 'src/lib/utils.ts', status: 'completed', severity: null },
  ];

  const activeFile = demoFiles[currentFileIndex];

  return (
    <div className="scanner-layout">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>Files</h2>
        </div>
        <div className="file-list">
          {demoFiles.map((file, i) => (
            <div 
              key={i} 
              className={`file-item ${i === currentFileIndex ? 'active' : ''}`}
              onClick={() => setCurrentFileIndex(i)}
            >
              <FileText size={14} className="file-icon" />
              <span className="file-name">{file.name}</span>
              {file.severity === 'high' && <AlertTriangle size={14} className="icon-high" />}
              {file.severity === 'medium' && <AlertTriangle size={14} className="icon-medium" />}
              {!file.severity && <CheckCircle size={14} className="icon-safe" />}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        <div className="content-header">
          <div className="path-bar">
            <span className="dot"></span>
            <span className="path-text">{activeFile.path}</span>
          </div>
          <button className="git-button">
            <Github size={14} />
            <span>Sync with GitHub</span>
          </button>
        </div>
        <div className="code-editor-placeholder">
          <div className="code-line"><span className="line-num">1</span> <span className="keyword">import</span> {'{'} signToken {'}'} <span className="keyword">from</span> 'jwt';</div>
          <div className="code-line"><span className="line-num">2</span></div>
          <div className="code-line vulnerability-line">
            <span className="line-num">3</span> <span className="keyword">export function</span> login(req, res) {'{'}
            <div className="vuln-tooltip">
               <strong>Missing Input Validation</strong>
               <p>User input is not validated before processing.</p>
            </div>
          </div>
          <div className="code-line"><span className="line-num">4</span>   <span className="comment">// ...</span></div>
          <div className="code-line"><span className="line-num">5</span> {'}'}</div>
        </div>
      </div>
    </div>
  );
}
