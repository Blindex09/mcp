import { ComboBox, ListBox, ListBoxItem, Label, Input, Popover } from 'react-aria-components';
import { useFilter } from 'react-aria';
import { useState } from 'react';

/**
 * Accessible combobox using React Aria Components (1.19+, 2026).
 *
 * A combobox is one of the hardest widgets to build by hand: it needs
 * role="combobox", aria-expanded, aria-controls, aria-activedescendant,
 * and full keyboard support. React Aria handles all of this at the hook
 * level — you write markup and CSS, the library wires ARIA + keyboard +
 * focus.
 *
 * WCAG: 4.1.2 (Name, Role, Value), 2.1.1 (Keyboard).
 */

const OPTIONS = [
  { id: 'apple', label: 'Apple' },
  { id: 'banana', label: 'Banana' },
  { id: 'cherry', label: 'Cherry' },
  { id: 'durian', label: 'Durian' },
];

export default function FruitCombobox() {
  const [value, setValue] = useState('');

  return (
    <ComboBox
      label="Favorite fruit"
      selectedKey={value}
      onSelectionChange={setValue}
      // menuTrigger="input" (default) opens on text edit.
      // Use "focus" to open on focus (browse-all-options comboboxes).
      // Use "manual" to open only via the trigger button or arrow keys.
    >
      <Label />
      <Input />
      {/* react-aria-components renders plain DOM with data-* state attributes,
          so style it with ordinary CSS — no runtime style props needed. */}
      {/* ComboBox composes with ListBox — options are ListBoxItem, not "ComboBoxItem"
          (that export doesn't exist). All ARIA wiring is handled by the library. */}
      <Popover>
        <ListBox>
          {OPTIONS.map((opt) => (
            <ListBoxItem key={opt.id} id={opt.id}>
              {opt.label}
            </ListBoxItem>
          ))}
        </ListBox>
      </Popover>
    </ComboBox>
  );
}

/* Gotchas documented in 2026 guides (nerdleveltech):
 * 1. Clicking or focusing the input alone does NOT open the popup when
 *    menuTrigger="input" (default). The popup opens when the user edits text.
 * 2. The Components API is safer than the raw hooks API — the hooks require
 *    manual prop spreading ({...inputProps}); miss one and a11y silently breaks.
 * 3. For a "browse all options" combobox, set menuTrigger="focus".
 */

/* Verifying accessibility with jest-axe (run in your test suite):
 *
 *   import { axe } from 'jest-axe';
 *   test('combobox has no violations', async () => {
 *     const { container } = render(<FruitCombobox />);
 *     expect(await axe(container)).toHaveNoViolations();
 *   });
 */