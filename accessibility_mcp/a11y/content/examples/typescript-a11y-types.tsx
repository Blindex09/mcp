/**
 * TypeScript accessibility constraint types (2026)
 *
 * TypeScript's built-in ARIA props are permissive — they allow any
 * combination of aria-* attributes without considering context or
 * mutual exclusions. Encode constraints with union types and `never`
 * so inaccessible component states literally won't compile.
 *
 * Source: Steve Kinney, "Accessibility Types and ARIA Props" (2026).
 */

import React, { useEffect, useRef } from 'react';

/* ------------------------------------------------------------------ */
/* 1. Button label — must have a name (children, aria-label, or       */
/*    aria-labelledby). A union of three mutually exclusive options.    */
/* ------------------------------------------------------------------ */
type ButtonLabel =
  | { children: React.ReactNode; 'aria-label'?: never; 'aria-labelledby'?: never }
  | { children?: never; 'aria-label': string; 'aria-labelledby'?: never }
  | { children?: never; 'aria-label'?: never; 'aria-labelledby': string };

// ✅ All compile
// <AccessibleButton onClick={fn}>Save</AccessibleButton>
// <AccessibleButton onClick={fn} aria-label="Close" />
// <AccessibleButton onClick={fn} aria-labelledby="save-label" />
// ❌ TypeScript error: button needs a label
// <AccessibleButton onClick={fn} />

/* ------------------------------------------------------------------ */
/* 2. Toggle button — aria-pressed only on toggles. Discriminated      */
/*    union prevents mixing toggle and regular button props.          */
/* ------------------------------------------------------------------ */
type ToggleButtonProps = {
  pressed: boolean;
  'aria-pressed': boolean;
  onToggle: (pressed: boolean) => void;
} | {
  pressed?: never;
  'aria-pressed'?: never;
  onToggle?: never;
  onClick: () => void;
};

// ❌ Error: can't mix toggle and regular button props
// <Button pressed={true} onClick={handleSave}>Invalid</Button>

/* ------------------------------------------------------------------ */
/* 3. Form control — when aria-invalid is true, aria-describedby is    */
/*    required (must point to the error message).                      */
/* ------------------------------------------------------------------ */
type FormControlError =
  | { 'aria-invalid': true; 'aria-describedby': string }
  | { 'aria-invalid'?: false | undefined; 'aria-describedby'?: string };

interface TextInputProps extends FormControlError {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}

// ❌ Error: invalid input needs an error description
// <TextInput aria-invalid={true} /* missing aria-describedby */ />

/* ------------------------------------------------------------------ */
/* 4. Role-specific button — switch needs aria-checked; tab needs      */
/*    aria-selected + aria-controls. Generic generics enforce this.   */
/* ------------------------------------------------------------------ */
type ButtonRole = 'button' | 'switch' | 'tab';

type ButtonByRole<R extends ButtonRole> = R extends 'switch'
  ? { role: 'switch'; 'aria-checked': boolean; onClick: (checked: boolean) => void }
  : R extends 'tab'
  ? { role: 'tab'; 'aria-selected': boolean; 'aria-controls': string; onClick: () => void }
  : { role?: 'button'; onClick: () => void };

type AccessibleButtonProps<R extends ButtonRole = 'button'> = ButtonLabel &
  ButtonByRole<R> & { disabled?: boolean; className?: string };

/* ------------------------------------------------------------------ */
/* 5. Conditional ARIA — collapsible section only gets aria-expanded    */
/*    + aria-controls when it is collapsible. Mapped types.            */
/* ------------------------------------------------------------------ */
type ConditionalAria<T extends boolean> = T extends true
  ? { 'aria-expanded': boolean; 'aria-controls': string }
  : { 'aria-expanded'?: never; 'aria-controls'?: never };

interface CollapsibleProps<T extends boolean = false> extends ConditionalAria<T> {
  isCollapsible: T;
  children: React.ReactNode;
}

/* ------------------------------------------------------------------ */
/* 6. Link or button — never both. The "button with href" antipattern. */
/* ------------------------------------------------------------------ */
type LinkOrButton =
  | { href: string; onClick?: never; type?: never }
  | { href?: never; onClick: () => void; type?: 'button' | 'submit' | 'reset' };

interface ActionElementProps extends LinkOrButton {
  children: React.ReactNode;
  disabled?: boolean;
}

/* ------------------------------------------------------------------ */
/* 7. Modal — always has an accessible name via aria-labelledby.       */
/* ------------------------------------------------------------------ */
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  'aria-labelledby': string;      // required — modal must have a name
  'aria-describedby'?: string;
  children: React.ReactNode;
}

const Modal: React.FC<ModalProps> = ({
  isOpen, onClose, 'aria-labelledby': labelledby, 'aria-describedby': describedby, children,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && modalRef.current) {
      modalRef.current.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledby}
      aria-describedby={describedby}
      tabIndex={-1}                 // programmatically focusable for focus management
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {children}
    </div>
  );
};

// ✅ Properly structured
// <Modal isOpen={show} onClose={() => setShow(false)} aria-labelledby="modal-title">
//   <h2 id="modal-title">Confirm Action</h2>
// </Modal>

/* ------------------------------------------------------------------ */
/* 8. Runtime validation with Zod — catch a11y violations from dynamic  */
/*    data (APIs, configs). Combine compile-time + runtime safety.     */
/* ------------------------------------------------------------------ */
// import { z } from 'zod';
// const ButtonPropsSchema = z.discriminatedUnion('role', [
//   z.object({ role: z.literal('button').optional(), onClick: z.function(), children: z.any().optional(), 'aria-label': z.string().optional() }),
//   z.object({ role: z.literal('switch'), 'aria-checked': z.boolean(), onClick: z.function(), 'aria-label': z.string() }),
// ]).refine(
//   (p) => p.role !== 'switch' ? (p.children || p['aria-label']) : p['aria-label'],
//   { message: 'Button must have accessible label' }
// );

/* ------------------------------------------------------------------ */
/* 9. Design-system metadata — attach WCAG criteria to components.     */
/* ------------------------------------------------------------------ */
type A11yLevel = 'AA' | 'AAA';
interface ComponentA11y {
  level: A11yLevel;
  features: ('keyboard' | 'screen-reader' | 'high-contrast')[];
  wcagCriteria: string[];
}
const ButtonA11y: ComponentA11y = {
  level: 'AA',
  features: ['keyboard', 'screen-reader'],
  wcagCriteria: ['2.1.1', '4.1.2'],
};

export { Modal, type AccessibleButtonProps, type ButtonRole, type ComponentA11y };