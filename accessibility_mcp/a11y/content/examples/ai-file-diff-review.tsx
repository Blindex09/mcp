import React, { useMemo, useState, useRef, useCallback, useEffect } from 'react';

/**
 * Accessible Multi-File AI Diff Review (2026)
 *
 * Fills the gap plain sr-only "+"/"-" line prefixes don't cover: a keyboard
 * user reviewing an AI agent's edits across several files needs to (1) pick
 * a file from a tree without losing roving-tabindex semantics, (2) jump
 * directly between changed hunks instead of arrowing through every unchanged
 * line, and (3) approve/reject per file (or per hunk) without a modal stack.
 *
 * Precedent: VS Code's real, shipping "Accessible Diff Viewer" (F7 / Shift+F7
 * to jump between changes, Escape to dismiss). We do NOT reuse F7 verbatim —
 * on the open web F7 is Firefox's caret-browsing toggle and fires a native
 * confirm dialog instead of reaching our handler — so this uses Alt+]/Alt+[.
 *
 * See references/agentic-ai-messaging-a11y.md §1.D and §3.B.1 for the
 * written spec this implements.
 *
 * WCAG: 2.1.1 (Keyboard), 4.1.2 (Name, Role, Value), 4.1.3 (Status Messages).
 */

type Hunk = { line: number; type: 'added' | 'removed' | 'context'; text: string };
type FileChange = { id: string; path: string; status: 'added' | 'modified' | 'deleted'; hunks: Hunk[] };

const FILES: FileChange[] = [
  {
    id: 'f1',
    path: 'src/components/Button.tsx',
    status: 'modified',
    hunks: [
      { line: 12, type: 'context', text: "export function Button({ children, ...props }) {" },
      { line: 13, type: 'removed', text: "  return <div onClick={props.onClick}>{children}</div>;" },
      { line: 13, type: 'added', text: "  return <button type=\"button\" {...props}>{children}</button>;" },
      { line: 14, type: 'context', text: "}" },
    ],
  },
  {
    id: 'f2',
    path: 'src/utils/format.ts',
    status: 'modified',
    hunks: [
      { line: 4, type: 'removed', text: "export const fmt = (n) => n.toFixed(2);" },
      { line: 4, type: 'added', text: "export const fmt = (n: number): string => n.toFixed(2);" },
    ],
  },
  {
    id: 'f3',
    path: 'src/legacy/oldWidget.js',
    status: 'deleted',
    hunks: [{ line: 1, type: 'removed', text: '// entire file removed — superseded by Button.tsx' }],
  },
];

function FileTree({
  files,
  selectedId,
  reviewState,
  onSelect,
}: {
  files: FileChange[];
  selectedId: string;
  reviewState: Record<string, 'pending' | 'approved' | 'rejected'>;
  onSelect: (id: string) => void;
}) {
  const treeRef = useRef<HTMLUListElement>(null);

  const onKeyDown = (e: React.KeyboardEvent) => {
    const ids = files.map((f) => f.id);
    const i = ids.indexOf(selectedId);
    if (e.key === 'ArrowDown' && i < ids.length - 1) { e.preventDefault(); onSelect(ids[i + 1]); }
    else if (e.key === 'ArrowUp' && i > 0) { e.preventDefault(); onSelect(ids[i - 1]); }
    else if (e.key === 'Home') { e.preventDefault(); onSelect(ids[0]); }
    else if (e.key === 'End') { e.preventDefault(); onSelect(ids[ids.length - 1]); }
  };

  return (
    <ul
      ref={treeRef}
      role="tree"
      aria-label="Changed files"
      onKeyDown={onKeyDown}
      style={{ listStyle: 'none', padding: 0, minWidth: 220, borderRight: '1px solid #ddd' }}
    >
      {files.map((f) => {
        const state = reviewState[f.id];
        const statusLabel = f.status === 'deleted' ? 'deleted' : f.status === 'added' ? 'added' : 'modified';
        const reviewLabel = state === 'approved' ? ', approved' : state === 'rejected' ? ', rejected' : ', pending review';
        return (
          <li
            key={f.id}
            role="treeitem"
            aria-selected={f.id === selectedId}
            aria-label={`${f.path}, ${statusLabel}${reviewLabel}`}
            tabIndex={f.id === selectedId ? 0 : -1}
            onClick={() => onSelect(f.id)}
            style={{
              padding: '8px 10px', cursor: 'pointer',
              background: f.id === selectedId ? 'rgba(59,130,246,.12)' : 'transparent',
              outline: 'none', borderLeft: f.id === selectedId ? '3px solid #3b82f6' : '3px solid transparent',
            }}
          >
            <span aria-hidden="true" style={{ marginRight: 6 }}>
              {f.status === 'added' ? '＋' : f.status === 'deleted' ? '－' : '●'}
            </span>
            {f.path}
            {state && (
              <span aria-hidden="true" style={{ marginLeft: 8, fontSize: '0.8em', opacity: 0.7 }}>
                ({state})
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function DiffView({
  file,
  onApprove,
  onReject,
  onRequestClose,
}: {
  file: FileChange;
  onApprove: () => void;
  onReject: () => void;
  onRequestClose: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeHunk, setActiveHunk] = useState(0);
  const [announcement, setAnnouncement] = useState('');
  const changedIndices = useMemo(
    () => file.hunks.map((h, i) => ({ h, i })).filter(({ h }) => h.type !== 'context').map(({ i }) => i),
    [file],
  );

  // Reset to the first change whenever the selected file changes.
  useEffect(() => { setActiveHunk(changedIndices[0] ?? 0); }, [file.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const jump = useCallback((delta: 1 | -1) => {
    if (!changedIndices.length) return;
    const pos = changedIndices.indexOf(activeHunk);
    const nextPos = pos === -1
      ? (delta === 1 ? 0 : changedIndices.length - 1)
      : (pos + delta + changedIndices.length) % changedIndices.length;
    const nextIndex = changedIndices[nextPos];
    setActiveHunk(nextIndex);
    const hunk = file.hunks[nextIndex];
    setAnnouncement(`Change ${nextPos + 1} of ${changedIndices.length}, ${hunk.type}, line ${hunk.line}`);
  }, [activeHunk, changedIndices, file.hunks]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    // Alt+]/Alt+[ instead of VS Code's F7/Shift+F7 — F7 is Firefox's
    // caret-browsing toggle on the open web and would never reach us.
    if (e.altKey && e.key === ']') { e.preventDefault(); jump(1); }
    else if (e.altKey && e.key === '[') { e.preventDefault(); jump(-1); }
    else if (e.key === 'Escape') { e.preventDefault(); onRequestClose(); }
  };

  return (
    <div
      ref={containerRef}
      role="region"
      aria-label={`Diff for ${file.path}`}
      aria-keyshortcuts="Alt+] Alt+[ Escape"
      tabIndex={0}
      onKeyDown={onKeyDown}
      style={{ flex: 1, padding: '0 1rem' }}
    >
      <h2 style={{ fontSize: '1rem' }}>{file.path}</h2>
      <p className="sr-only">
        Press Alt+] for next change, Alt+[ for previous change, Escape to return to the file list.
      </p>

      {/* Bounded status announcement on hunk jump — not one live-region hit per keystroke. */}
      <div role="status" className="sr-only">{announcement}</div>

      <pre style={{ background: '#0f172a', color: '#e2e8f0', padding: '1rem', borderRadius: 6, overflowX: 'auto' }}>
        <code>
          {file.hunks.map((h, i) => (
            <div
              key={i}
              data-hunk-index={i}
              style={{
                display: 'block',
                background: h.type === 'added' ? 'rgba(34,197,94,.15)' : h.type === 'removed' ? 'rgba(239,68,68,.15)' : 'transparent',
                outline: i === activeHunk && h.type !== 'context' ? '2px solid #3b82f6' : 'none',
              }}
            >
              <span className="sr-only">
                {h.type === 'added' ? 'Added line: ' : h.type === 'removed' ? 'Removed line: ' : ''}
              </span>
              <span aria-hidden={h.type === 'context' ? undefined : 'true'}>
                {h.type === 'added' ? '+ ' : h.type === 'removed' ? '- ' : '  '}
              </span>
              {h.text}
              {h.type !== 'context' && (
                <button
                  type="button"
                  aria-label={`${h.type === 'added' ? 'Accept' : 'Reject'} change: line ${h.line}`}
                  style={{ marginLeft: 12, fontSize: '0.75em' }}
                  onClick={() => setAnnouncement(`Line ${h.line} ${h.type === 'added' ? 'accepted' : 'rejected'} individually`)}
                >
                  {h.type === 'added' ? 'Accept line' : 'Reject line'}
                </button>
              )}
            </div>
          ))}
        </code>
      </pre>

      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
        <button type="button" onClick={onReject}>Reject file</button>
        <button type="button" onClick={onApprove} style={{ background: '#005fcc', color: 'white' }}>
          Approve file
        </button>
      </div>
    </div>
  );
}

export function AIFileDiffReview() {
  const [selectedId, setSelectedId] = useState(FILES[0].id);
  const [reviewState, setReviewState] = useState<Record<string, 'pending' | 'approved' | 'rejected'>>({});
  const [batchStatus, setBatchStatus] = useState('');
  const treeContainerRef = useRef<HTMLDivElement>(null);

  const selectedFile = FILES.find((f) => f.id === selectedId)!;

  const setState = (id: string, state: 'approved' | 'rejected') => {
    setReviewState((prev) => ({ ...prev, [id]: state }));
    // Do NOT auto-advance focus to the next file — the reviewer stays in
    // control of the tree, matching the SPA "never silently relocate focus" rule.
  };

  const approveAll = () => {
    FILES.forEach((f, i) => {
      setTimeout(() => {
        setReviewState((prev) => ({ ...prev, [f.id]: 'approved' }));
        setBatchStatus(`Applying changes: file ${i + 1} of ${FILES.length} — ${f.path}`);
      }, i * 400);
    });
  };

  return (
    <main aria-label="AI Multi-File Change Review">
      <h1>Review AI-Proposed Changes</h1>
      <button type="button" onClick={approveAll} style={{ marginBottom: '1rem' }}>
        Approve all files
      </button>

      {/* One bounded status region for the whole batch — not one live-region hit per file. */}
      <div role="status" className="sr-only">{batchStatus}</div>

      <div style={{ display: 'flex' }}>
        <div ref={treeContainerRef}>
          <FileTree files={FILES} selectedId={selectedId} reviewState={reviewState} onSelect={setSelectedId} />
        </div>
        <DiffView
          file={selectedFile}
          onApprove={() => setState(selectedFile.id, 'approved')}
          onReject={() => setState(selectedFile.id, 'rejected')}
          onRequestClose={() => treeContainerRef.current?.querySelector<HTMLElement>('[role="treeitem"][tabindex="0"]')?.focus()}
        />
      </div>
    </main>
  );
}
