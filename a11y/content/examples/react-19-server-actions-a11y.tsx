import React, { useActionState } from 'react';
import { useFormStatus } from 'react-dom';

/**
 * React 19 Accessible Server Actions Form
 * Demonstrates:
 * 1. Direct `ref` prop passing (deprecating forwardRef in React 19).
 * 2. Form pending state declared via aria-disabled="true" on submit button.
 * 3. Server action feedback announced via role="status" / aria-live="polite".
 */

// Custom Input receiving `ref` directly as a prop in React 19
function AccessibleInput({ label, id, ref, ...props }: { label: string; id: string; ref?: React.Ref<HTMLInputElement> } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      <input id={id} ref={ref} {...props} />
    </div>
  );
}

// Submit button tracking form status
function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} aria-disabled={pending}>
      {pending ? 'Saving Changes...' : 'Save Profile'}
    </button>
  );
}

async function updateProfileState(prevState: { success: boolean; message: string }, formData: FormData) {
  const name = formData.get('name') as string;
  if (!name || name.length < 2) {
    return { success: false, message: 'Name must be at least 2 characters long.' };
  }
  // Simulate async server action
  await new Promise(res => setTimeout(res, 800));
  return { success: true, message: 'Profile updated successfully!' };
}

export function React19AccessibleForm() {
  const [state, formAction] = useActionState(updateProfileState, { success: false, message: '' });
  const inputRef = React.useRef<HTMLInputElement>(null);

  return (
    <main className="form-card" aria-labelledby="form-title">
      <h1 id="form-title">React 19 Profile Settings</h1>

      {/* Screen Reader Status Live Region for Server Action Feedback */}
      <div 
        role="status"
        aria-atomic="true" 
        className={`status-banner ${state.success ? 'success' : 'error'}`}
      >
        {state.message}
      </div>

      <form action={formAction}>
        <AccessibleInput 
          ref={inputRef} 
          id="user-name" 
          name="name" 
          label="Display Name" 
          required 
        />
        <SubmitButton />
      </form>
    </main>
  );
}
