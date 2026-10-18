import React, { useState, useRef } from 'react';

/**
 * Accessible AI Agent Tool Call Execution & Human-in-the-Loop (HITL) Modal
 * Demonstrates:
 * 1. Tool execution as ordinary, on-demand text before the final answer.
 * 2. Silent incremental logs without headings or live-region announcements.
 * 3. HITL approval modal with `role="alertdialog"`, focus containment, and safe default focus.
 */
export function AIAgentToolExecution() {
  const [isToolRunning, setIsToolRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showHitlModal, setShowHitlModal] = useState(false);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const runTriggerRef = useRef<HTMLButtonElement>(null);

  const runAgentTask = () => {
    setIsToolRunning(true);
    setLogs(['[System]: Agent task initialized.', '[Tool]: Executing repository scan...']);

    setTimeout(() => {
      setLogs(prev => [...prev, '[Tool]: Modifications detected in package.json. User confirmation required.']);
      setIsToolRunning(false);
      setShowHitlModal(true);
      // Move focus to safest default option (Cancel) in alertdialog
      setTimeout(() => cancelButtonRef.current?.focus(), 50);
    }, 1200);
  };

  const handleApprove = () => {
    setShowHitlModal(false);
    setLogs(prev => [...prev, '[System]: Action APPROVED by user. Applying changes...']);
    runTriggerRef.current?.focus();
  };

  const handleDecline = () => {
    setShowHitlModal(false);
    setLogs(prev => [...prev, '[System]: Action DECLINED by user. Task aborted.']);
    runTriggerRef.current?.focus();
  };

  return (
    <main className="agent-container" aria-label="AI Agent Workbench">
      <h1>AI Agent Task Runner</h1>

      <button 
        ref={runTriggerRef} 
        type="button" 
        onClick={runAgentTask} 
        disabled={isToolRunning}
      >
        {isToolRunning ? 'Agent Running...' : 'Execute Agent Refactor Task'}
      </button>

      {/* Operational text is not document-heading content and is silent by default. */}
      <div
        className="tool-execution-log" 
        aria-busy={isToolRunning}
        style={{ marginTop: '1.5rem', background: '#0f172a', color: '#38bdf8', padding: '1rem', borderRadius: '6px' }}
      >
        <p>{isToolRunning ? 'Executando ferramenta de refatoração...' : 'Execução da ferramenta finalizada.'}</p>
        {isToolRunning ? (
          <div style={{ fontFamily: 'monospace' }}>
            {logs.map((log, i) => <div key={i}>{log}</div>)}
          </div>
        ) : (
          <p>Executou a ferramenta de refatoração.</p>
        )}
      </div>

      {/* Human-in-the-Loop (HITL) Alert Dialog Modal */}
      {showHitlModal && (
        <div 
          className="modal-backdrop" 
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <div 
            role="alertdialog" 
            aria-modal="true" 
            aria-labelledby="hitl-title" 
            aria-describedby="hitl-desc"
            style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', maxWidth: '450px' }}
          >
            <h3 id="hitl-title">Confirmation Required</h3>
            <p id="hitl-desc">
              The AI Agent wishes to execute <code>npm install --save-exact</code> and modify configuration files. Do you approve this action?
            </p>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', justifyContent: 'flex-end' }}>
              {/* Default focused button is Cancel for safety */}
              <button ref={cancelButtonRef} type="button" onClick={handleDecline}>
                Decline & Abort
              </button>
              <button type="button" onClick={handleApprove} style={{ background: '#005fcc', color: 'white' }}>
                Approve Execution
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
