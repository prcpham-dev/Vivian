import React, { useState, useEffect, useMemo } from 'react';
import { AlertTriangle, FileText, CheckCircle, Folder, ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import { DEFAULT_PORT } from '../utils/constants';

const getVscode = () => (window as any).vscode;

// Utility to build a tree from flat paths
function buildTree(paths: string[], rootName: string) {
  const root: any = { name: rootName, children: {}, isDir: true, path: '' };
  paths.forEach(p => {
    const parts = p.split('/');
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!current.children[part]) {
        const isDir = i < parts.length - 1;
        current.children[part] = {
          name: part,
          path: parts.slice(0, i + 1).join('/'),
          isDir,
          children: {}
        };
      }
      current = current.children[part];
    }
  });

  function sortNode(node: any) {
    if (!node.children) return;
    const sortedKeys = Object.keys(node.children).sort((a, b) => {
      const childA = node.children[a];
      const childB = node.children[b];
      if (childA.isDir && !childB.isDir) return -1;
      if (!childA.isDir && childB.isDir) return 1;
      return a.localeCompare(b);
    });
    node.sortedChildren = sortedKeys.map(k => node.children[k]);
    node.sortedChildren.forEach(sortNode);
  }
  
  sortNode(root);
  return root;
}

const TreeNode = ({ node, level, onCheck, checkedFiles, scannedFiles, onFileClick, activeFile }: any) => {
  const [expanded, setExpanded] = useState(level === 0);
  const isChecked = checkedFiles.has(node.path);

  if (node.isDir) {
    return (
      <div className="tree-node">
        <div className="tree-row" style={{ paddingLeft: level * 12 + 'px' }} onClick={() => setExpanded(!expanded)}>
          {expanded ? <ChevronDown size={14} className="folder-icon" /> : <ChevronRight size={14} className="folder-icon" />}
          <Folder size={14} className="folder-icon" />
          <span className="file-name">{node.name}</span>
        </div>
        {expanded && (
          <div className="tree-children">
            {(node.sortedChildren || []).map((child: any) => (
              <TreeNode key={child.path} node={child} level={level + 1} onCheck={onCheck} checkedFiles={checkedFiles} scannedFiles={scannedFiles} onFileClick={onFileClick} activeFile={activeFile} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const highestSeverityColor = React.useMemo(() => {
    if (!Array.isArray(node.findings) || node.findings.length === 0) {
      if (scannedFiles && scannedFiles.has(node.path)) return '#4cf177';
      return null;
    }
    let hasHigh = false;
    let hasMedium = false;
    for (const f of node.findings) {
      const sev = f.severity?.toLowerCase() || 'high';
      if (sev === 'critical' || sev === 'high') hasHigh = true;
      else if (sev === 'medium') hasMedium = true;
    }
    if (hasHigh) return '#f14c4c';
    if (hasMedium) return '#f1b24c';
    return '#4cf177';
  }, [node.findings, scannedFiles, node.path]);

  return (
    <div className={`tree-row file-item ${activeFile === node.path ? 'active' : ''}`} style={{ paddingLeft: level * 12 + 16 + 'px' }} onClick={() => onFileClick(node.path)}>
      <FileText size={14} className="file-icon" />
      <span className="file-name">{node.name}</span>
      {highestSeverityColor && <span style={{ width: '8px', height: '8px', backgroundColor: highestSeverityColor, borderRadius: '50%', flexShrink: 0, marginRight: '6px' }}></span>}
      <input type="checkbox" className="tree-checkbox" checked={isChecked} onChange={(e) => onCheck(node.path, e.target.checked)} onClick={e => e.stopPropagation()} />
    </div>
  );
}

const FindingCard = ({ finding }: { finding: any }) => {
  const [expanded, setExpanded] = useState(false);
  const sev = finding.severity?.toLowerCase() || 'high'; // Default to high if unknown
  const color = (sev === 'high' || sev === 'critical') ? '#f14c4c' : (sev === 'medium' ? '#f1b24c' : '#4cf177');
  
  return (
    <div 
      style={{ margin: '4px 0 8px 30px', padding: '6px 10px', borderLeft: `3px solid ${color}`, backgroundColor: 'rgba(255,255,255,0.05)', cursor: 'pointer', borderRadius: '0 4px 4px 0', maxWidth: '80%' }} 
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {color === '#f14c4c' || color === '#f1b24c' ? <AlertTriangle size={14} color={color} /> : <CheckCircle size={14} color={color} />}
        <strong style={{ color, fontSize: '12px' }}>{finding.title || 'Finding'}</strong>
        <span style={{ fontSize: '9px', color: '#888', marginLeft: 'auto' }}>{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
        <div style={{ marginTop: '8px' }}>
          <p style={{ margin: 0, fontSize: '11px', color: '#ccc', lineHeight: '1.4' }}>{finding.description}</p>
          {finding.recommendation && <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#aaa', lineHeight: '1.4' }}><strong>Fix: </strong>{finding.recommendation}</p>}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [activeTab, setActiveTab] = useState<'files' | 'git'>('files');
  const [files, setFiles] = useState<string[]>([]);
  const [gitChanges, setGitChanges] = useState<string[]>([]);
  const [checkedFiles, setCheckedFiles] = useState<Set<string>>(new Set());
  const [scannedFiles, setScannedFiles] = useState<Set<string>>(new Set());
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState<string>('Workspace');
  const [workspaceRoot, setWorkspaceRoot] = useState<string>('');

  // New state
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [findings, setFindings] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);

  const [gitDiffContent, setGitDiffContent] = useState<string>('');
  const [gitFindings, setGitFindings] = useState<any[]>([]);
  const [scanningGit, setScanningGit] = useState(false);

  useEffect(() => {
    const handleMessage = (event: any) => {
      const msg = event.data;
      if (msg.command === 'filesLoaded') {
        setFiles(msg.files.sort());
        if (msg.workspaceName) setWorkspaceName(msg.workspaceName);
        if (msg.workspaceRoot) setWorkspaceRoot(msg.workspaceRoot);
      } else if (msg.command === 'gitChangesLoaded') {
        setGitChanges(msg.files.sort());
      } else if (msg.command === 'fileContent') {
        if (msg.filePath === activeFile) {
          setFileContent(msg.content);
        }
      } else if (msg.command === 'gitDiffContent') {
        setGitDiffContent(msg.diff);
      }
    };
    window.addEventListener('message', handleMessage);
    
    getVscode()?.postMessage({ command: 'requestFiles' });
    getVscode()?.postMessage({ command: 'requestGitChanges' });
    getVscode()?.postMessage({ command: 'getGitDiff' });
    
    return () => window.removeEventListener('message', handleMessage);
  }, [activeFile]);

  const tree = useMemo(() => {
    const t = buildTree(files, workspaceName);
    // Inject findings into the tree nodes
    const injectFindings = (node: any) => {
      node.findings = findings.filter(f => {
         const p = f.file || f.path || '';
         return p === node.path || p.endsWith(node.path);
      });
      if (node.children) {
        Object.values(node.children).forEach(injectFindings);
      }
    };
    injectFindings(t);
    return t;
  }, [files, workspaceName, findings]);

  const toggleCheck = (path: string, checked: boolean) => {
    const next = new Set(checkedFiles);
    if (checked) next.add(path);
    else next.delete(path);
    setCheckedFiles(next);
  };

  const handleFileClick = (path: string) => {
    setActiveFile(path);
    setFileContent(null);
    getVscode()?.postMessage({ command: 'requestFileContent', filePath: path });
  };

  const openDiff = (path: string) => {
    getVscode()?.postMessage({ command: 'openDiff', filePath: path });
  };

  const handleScan = async () => {
    if (checkedFiles.size === 0) return;
    setScanning(true);
    setFindings([]);
    try {
      const res = await fetch(`http://localhost:${DEFAULT_PORT}/scan/directory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_root: workspaceRoot, nodes: Array.from(checkedFiles) })
      });
      const data = await res.json();
      if (data.findings) setFindings(data.findings);
      setScannedFiles(new Set(checkedFiles));
    } catch (e) {
      console.error(e);
    } finally {
      setScanning(false);
    }
  };

  const handleGitScan = async () => {
    if (!gitDiffContent) return;
    setScanningGit(true);
    setGitFindings([]);
    try {
      const res = await fetch(`http://localhost:${DEFAULT_PORT}/scan/diff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diff: gitDiffContent })
      });
      const data = await res.json();
      if (data.findings) setGitFindings(data.findings);
    } catch (e) {
      console.error(e);
    } finally {
      setScanningGit(false);
    }
  };

  return (
    <div className="scanner-layout">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header tabs">
          <button className={`tab ${activeTab === 'files' ? 'active' : ''}`} onClick={() => setActiveTab('files')}>Files</button>
          <button className={`tab ${activeTab === 'git' ? 'active' : ''}`} onClick={() => setActiveTab('git')}>Git Diff</button>
        </div>
        
        <div className="file-list" style={{ display: 'flex', flexDirection: 'column' }}>
          {activeTab === 'files' && (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
               <div className="tree-container" style={{ flex: 1, overflowY: 'auto' }}>
                 {files.length === 0 ? <div className="loading" style={{padding: '8px', fontSize: '11px', color: '#888'}}>Loading files...</div> : (
                   <TreeNode node={tree} level={0} onCheck={toggleCheck} checkedFiles={checkedFiles} scannedFiles={scannedFiles} onFileClick={handleFileClick} activeFile={activeFile} />
                 )}
               </div>
               <div style={{ padding: '8px', borderTop: '1px solid var(--vscode-panel-border)' }}>
                 <button className="git-button" style={{ width: '100%', justifyContent: 'center' }} onClick={handleScan} disabled={scanning || checkedFiles.size === 0}>
                   {scanning ? <><Loader2 size={14} className="spin" /> Scanning...</> : 'Scan Selected'}
                 </button>
               </div>
             </div>
          )}
          
          {activeTab === 'git' && (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
               <div className="git-container" style={{ flex: 1, overflowY: 'auto' }}>
                 {gitChanges.length === 0 ? <div className="loading" style={{padding: '8px', fontSize: '11px', color: '#888'}}>No changes found.</div> : gitChanges.map(file => (
                   <div key={file} className={`tree-row file-item`} onClick={() => openDiff(file)}>
                     <FileText size={14} className="file-icon" />
                     <span className="file-name">{file}</span>
                   </div>
                 ))}
               </div>
               <div style={{ padding: '8px', borderTop: '1px solid var(--vscode-panel-border)' }}>
                 <button className="git-button" style={{ width: '100%', justifyContent: 'center' }} onClick={handleGitScan} disabled={scanningGit || !gitDiffContent}>
                   {scanningGit ? <><Loader2 size={14} className="spin" /> Scanning Diff...</> : 'Scan Vulnerabilities'}
                 </button>
               </div>
             </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        <div className="content-header">
          <div className="path-bar">
            {activeFile && (
               <>
                 <span className="dot"></span>
                 <span className="path-text">{activeFile}</span>
               </>
            )}
            {!activeFile && gitFindings.length > 0 && (
               <>
                 <span className="dot" style={{ backgroundColor: '#f1b24c' }}></span>
                 <span className="path-text">Git Scan Results</span>
               </>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="git-button" onClick={() => getVscode()?.postMessage({ command: 'openGraph' })}>
              <span>Code Graph</span>
            </button>
          </div>
        </div>
        <div className="code-editor-placeholder">
            {activeFile && fileContent !== null ? (
             <>
               {fileContent.split('\n').map((line, idx) => {
                 const lineFindings = findings.filter((f: any) => {
                   const p = f.file || f.path || '';
                   const isFileMatch = p === activeFile || activeFile.endsWith(p);
                   return isFileMatch && f.line === idx + 1;
                 });
                 const fileLevelFindings = idx === 0 ? findings.filter((f: any) => {
                   const p = f.file || f.path || '';
                   const isFileMatch = p === activeFile || activeFile.endsWith(p);
                   return isFileMatch && !f.line;
                 }) : [];

                 return (
                   <React.Fragment key={idx}>
                     {fileLevelFindings.map((finding: any, i: number) => (
                       <FindingCard key={`file-${i}`} finding={finding} />
                     ))}
                     <div className="code-line">
                       <span className="line-num">{idx + 1}</span>
                       <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{line}</span>
                     </div>
                     {lineFindings.map((finding: any, i: number) => (
                       <FindingCard key={`line-${i}`} finding={finding} />
                     ))}
                   </React.Fragment>
                 );
               })}
             </>
           ) : !activeFile && gitFindings.length > 0 ? (
             <div style={{ padding: '16px' }}>
               <h3 style={{ color: '#fff', marginBottom: '16px' }}>Diff Vulnerability Scan</h3>
               {gitFindings.map((finding: any, i: number) => (
                 <FindingCard key={i} finding={finding} />
               ))}
             </div>
           ) : (
             <div className="code-line"><span className="comment">{activeFile ? 'Loading file...' : 'Select a file from the sidebar to begin, or use Git Diff tools.'}</span></div>
           )}
        </div>
      </div>
    </div>
  );
}
