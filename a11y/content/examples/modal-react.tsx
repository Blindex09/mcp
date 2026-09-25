import React, { useEffect, useRef, useCallback } from 'react';

/**
 * Accessible modal — React implementation with manual focus management.
 * For production, prefer Radix Dialog or React Aria <Modal> which handle
 * edge cases (portals, shadow DOM, dynamically added elements) for you.
 *
 * WCAG: 2.1.1 (Keyboard), 2.1.2 (No Keyboard Trap), 2.4.3 (Focus Order),
 *        2.4.7 (Focus Visible), 4.1.2 (Name, Role, Value), 1.3.1 (Info).
 */
function AccessibleModal({ isOpen, onClose, title, children }) {
  const modalRef = useRef(null);
  const triggerRef = useRef(null); // remembers what had focus before we opened

  const getFocusableElements = useCallback(() => {
    if (!modalRef.current) return [];
    return modalRef.current.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input:not([disabled]), ' +
      'select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    // Store the trigger so we can return focus on close
    triggerRef.current = document.activeElement;

    const focusableElements = getFocusableElements();
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const focusable = getFocusableElements();
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to the trigger when the modal closes
      triggerRef.current?.focus();
    };
  }, [isOpen, onClose, getFocusableElements]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => e.stopPropagation()} // don't close when clicking inside
      >
        <h2 id="modal-title">{title}</h2>
        {children}
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

export default AccessibleModal;