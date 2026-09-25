import { useEffect, useRef } from "react"

export function ApprovalDialog({ request, onDecision }) {
  const dialogRef = useRef(null)
  const denyRef = useRef(null)
  const returnFocusRef = useRef(null)

  useEffect(() => {
    if (!request) return
    returnFocusRef.current = document.activeElement
    dialogRef.current?.showModal()
    denyRef.current?.focus()
    return () => returnFocusRef.current?.focus()
  }, [request])

  if (!request) return null
  const decide = approved => {
    dialogRef.current?.close()
    onDecision(approved)
  }
  return (
    <dialog
      ref={dialogRef} role="alertdialog" aria-labelledby="approval-title" aria-describedby="approval-description"
      onCancel={event => { event.preventDefault(); decide(false) }}
    >
      <h2 id="approval-title">Confirmar ação</h2>
      <p id="approval-description">{request.safeSummary}</p>
      <div className="dialog-actions">
        <button ref={denyRef} type="button" onClick={() => decide(false)}>Negar</button>
        <button type="button" onClick={() => decide(true)}>Permitir</button>
      </div>
    </dialog>
  )
}
