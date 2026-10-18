/**
 * Accessible dropdown MENU with SUBMENUS — React, no library (2026)
 *
 * Implements the WAI-ARIA Menu Pattern:
 *   - Trigger: aria-haspopup="menu", aria-expanded, aria-controls
 *   - Menu: role="menu", aria-labelledby pointing back to the trigger
 *   - Items: role="menuitem" (and menuitemcheckbox / menuitemradio variants)
 *   - Roving tabindex: the active item gets tabindex="0", others get "-1"
 *   - Keyboard: Arrow keys navigate, Enter/Space activate, Escape closes,
 *     Home/End jump to first/last, Tab closes without trapping focus.
 *   - Submenus: ArrowRight opens the submenu and moves focus to its first
 *     item; ArrowLeft (or Escape) inside a submenu closes ONLY that level
 *     and returns focus to the parent menuitem that opened it — it does
 *     NOT close the whole menu tree.
 *
 * Source: WAI-ARIA APG Menu Pattern, ASOasis (2026), Daniel Joffe (2026).
 * WCAG: 2.1.1, 2.1.2, 2.4.3, 2.4.7, 4.1.2.
 */
import React, { useEffect, useId, useMemo, useRef, useState, useCallback, forwardRef, useImperativeHandle } from 'react';

type MenuItem =
  | { type: 'item'; label: string; onSelect: () => void; disabled?: boolean }
  | { type: 'separator' }
  | { type: 'checkbox'; label: string; checked: boolean; onToggle: () => void }
  | { type: 'radio-group'; label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void }
  | { type: 'submenu'; label: string; items: MenuItem[] };

type MenuButtonHandle = { focusFirst: () => void };

const MenuButton = forwardRef<MenuButtonHandle, { label: string; items: MenuItem[]; isSubmenu?: boolean; onRequestClose?: () => void }>(
  function MenuButton({ label, items, isSubmenu = false, onRequestClose }, ref) {
    const buttonRef = useRef<HTMLButtonElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);
    const submenuRefs = useRef<Record<number, MenuButtonHandle | null>>({});
    const [open, setOpen] = useState(false);
    const [activeIndex, setActiveIndex] = useState(-1);
    const [openSubmenuIndex, setOpenSubmenuIndex] = useState(-1);
    const [typeahead, setTypeahead] = useState('');
    const typeaheadTimer = useRef<number | null>(null);

    const menuId = useId();
    const labelId = useId();

    // A nested submenu is considered "open" for as long as its parent keeps it
    // mounted (parent gates mounting via openSubmenuIndex) — it has no trigger
    // button of its own to click.
    const effectiveOpen = isSubmenu || open;

    // Compute actionable (focusable) indices once — skip separators & disabled.
    const focusable = useMemo(
      () =>
        items
          .map((it, i) => ({ i, item: it }))
          .filter(({ item }) => item.type !== 'separator' && !('disabled' in item && item.disabled)),
      [items],
    );
    const firstIndex = focusable[0]?.i ?? -1;
    const lastIndex = focusable[focusable.length - 1]?.i ?? -1;

    // Outside click + Tab close (top-level menu only — submenus are closed via
    // ArrowLeft/Escape bubbling to onRequestClose, not by these document listeners).
    useEffect(() => {
      if (isSubmenu || !open) return;
      const onDocClick = (e: MouseEvent) => {
        const t = e.target as Node;
        if (!menuRef.current?.contains(t) && !buttonRef.current?.contains(t)) {
          setOpen(false);
          setActiveIndex(-1);
          setOpenSubmenuIndex(-1);
          buttonRef.current?.focus();
        }
      };
      const onDocKey = (e: KeyboardEvent) => {
        if (e.key === 'Tab') setOpen(false);
      };
      document.addEventListener('mousedown', onDocClick);
      document.addEventListener('keydown', onDocKey);
      return () => {
        document.removeEventListener('mousedown', onDocClick);
        document.removeEventListener('keydown', onDocKey);
      };
    }, [isSubmenu, open]);

    // Move DOM focus to the active item whenever it changes.
    useEffect(() => {
      if (!effectiveOpen) return;
      const el = menuRef.current?.querySelector<HTMLElement>(`[data-index="${activeIndex}"]`);
      if (el) el.focus();
      else (menuRef.current as HTMLElement | null)?.focus();
    }, [effectiveOpen, activeIndex]);

    // When a submenu is opened (ArrowRight sets openSubmenuIndex), move focus
    // into its first item once it has mounted and registered its ref.
    useEffect(() => {
      if (openSubmenuIndex !== -1) {
        submenuRefs.current[openSubmenuIndex]?.focusFirst();
      }
    }, [openSubmenuIndex]);

    const openAndFocus = useCallback((index: number) => {
      setOpen(true);
      setActiveIndex(index);
    }, []);

    useImperativeHandle(ref, () => ({ focusFirst: () => openAndFocus(firstIndex) }), [openAndFocus, firstIndex]);

    const onButtonKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); openAndFocus(firstIndex); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); openAndFocus(lastIndex); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openAndFocus(firstIndex); }
      else if (e.key === 'Escape') setOpen(false);
    };

    const closeSubmenuIfNavigatingAway = (next: number) => {
      if (next !== openSubmenuIndex) setOpenSubmenuIndex(-1);
    };

    const move = (delta: 1 | -1) => {
      if (!focusable.length) return;
      const curr = activeIndex === -1 ? (delta === 1 ? firstIndex : lastIndex) : activeIndex;
      const pos = focusable.findIndex((f) => f.i === curr);
      const next = focusable[(pos + delta + focusable.length) % focusable.length].i;
      setActiveIndex(next);
      closeSubmenuIfNavigatingAway(next);
    };

    const onMenuKeyDown = (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown': e.preventDefault(); move(1); break;
        case 'ArrowUp':   e.preventDefault(); move(-1); break;
        case 'Home':      e.preventDefault(); setActiveIndex(firstIndex); closeSubmenuIfNavigatingAway(firstIndex); break;
        case 'End':       e.preventDefault(); setActiveIndex(lastIndex); closeSubmenuIfNavigatingAway(lastIndex); break;
        case 'ArrowRight': {
          const it = items[activeIndex];
          if (it && it.type === 'submenu') {
            e.preventDefault();
            setOpenSubmenuIndex(activeIndex);
          }
          break;
        }
        case 'ArrowLeft': {
          if (isSubmenu) {
            e.preventDefault();
            onRequestClose?.();
          }
          break;
        }
        case 'Enter':
        case ' ': {
          e.preventDefault();
          const it = items[activeIndex];
          if (it && it.type === 'item' && !it.disabled) {
            it.onSelect();
            setOpen(false);
            setOpenSubmenuIndex(-1);
            buttonRef.current?.focus();
          } else if (it && it.type === 'submenu') {
            setOpenSubmenuIndex(activeIndex);
          }
          break;
        }
        case 'Escape':
          e.preventDefault();
          if (isSubmenu) {
            // Close only this level; focus returns to the parent menuitem.
            onRequestClose?.();
          } else {
            setOpen(false);
            setOpenSubmenuIndex(-1);
            buttonRef.current?.focus();
          }
          break;
        default:
          // Typeahead: focus next item whose label starts with the typed buffer.
          if (e.key.length === 1 && /\S/.test(e.key)) {
            const buffer = (typeahead + e.key).toLowerCase();
            setTypeahead(buffer);
            if (typeaheadTimer.current) clearTimeout(typeaheadTimer.current);
            typeaheadTimer.current = window.setTimeout(() => setTypeahead(''), 500);
            const start = activeIndex === -1 ? 0 : focusable.findIndex((f) => f.i === activeIndex) + 1;
            const labels = focusable.map((f) => (items[f.i] as any).label?.toLowerCase() ?? '');
            const rotated = labels.slice(start).concat(labels.slice(0, start));
            const foundRel = rotated.findIndex((l) => l.startsWith(buffer));
            if (foundRel !== -1) {
              const next = focusable[(start + foundRel) % focusable.length].i;
              setActiveIndex(next);
              closeSubmenuIfNavigatingAway(next);
            }
          }
      }
    };

    const onItemClick = (i: number) => {
      const it = items[i];
      if (it?.type === 'item' && !it.disabled) {
        it.onSelect();
        setOpen(false);
        setOpenSubmenuIndex(-1);
        buttonRef.current?.focus();
      } else if (it?.type === 'submenu') {
        setActiveIndex(i);
        setOpenSubmenuIndex(i);
      }
    };

    return (
      <div style={{ position: 'relative', display: 'inline-block' }}>
        {!isSubmenu && (
          <button
            ref={buttonRef}
            aria-haspopup="menu"
            aria-expanded={open}
            aria-controls={menuId}
            id={labelId}
            type="button"
            onClick={() => (open ? setOpen(false) : openAndFocus(firstIndex))}
            onKeyDown={onButtonKeyDown}
          >
            {label}
            <span aria-hidden="true">▾</span>
          </button>
        )}

        {effectiveOpen && (
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            aria-labelledby={labelId}
            tabIndex={-1}
            onKeyDown={onMenuKeyDown}
            style={{ position: 'absolute', minWidth: 180, background: '#fff',
                     border: '1px solid #ddd', borderRadius: 6, padding: 4, boxShadow: '0 10px 25px rgba(0,0,0,.12)' }}
          >
            {items.map((it, i) => {
              const base = {
                'data-index': i,
                tabIndex: (i === activeIndex ? 0 : -1) as number,
                onMouseEnter: () => it.type !== 'separator' && setActiveIndex(i),
                style: {
                  padding: '8px 10px', borderRadius: 4, cursor: 'pointer',
                  outline: i === activeIndex ? '2px solid #3b82f6' : 'none',
                  background: i === activeIndex ? 'rgba(59,130,246,.1)' : 'transparent',
                } as React.CSSProperties,
              };
              if (it.type === 'separator') return <div key={i} role="separator" style={{ height: 1, background: '#eee', margin: '4px 0' }} />;
              if (it.type === 'item')
                return <div key={i} role="menuitem" aria-disabled={it.disabled || undefined} onClick={() => onItemClick(i)} {...base}>{it.label}</div>;
              if (it.type === 'checkbox')
                return <div key={i} role="menuitemcheckbox" aria-checked={it.checked} onClick={it.onToggle} {...base}>{it.label}</div>;
              if (it.type === 'radio-group')
                return (
                  <div key={i} role="group" aria-label={it.label}>
                    {it.options.map((o, j) => (
                      <div key={`${i}-${j}`} role="menuitemradio" aria-checked={o.value === it.value}
                           onClick={() => it.onChange(o.value)} {...base}>{o.label}</div>
                    ))}
                  </div>
                );
              // submenu — opened with ArrowRight/Enter, closed with ArrowLeft/Escape
              if (it.type === 'submenu') {
                return (
                  <div key={i} role="menuitem" aria-haspopup="menu" aria-expanded={i === openSubmenuIndex} onClick={() => onItemClick(i)} {...base}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                      <span>{it.label}</span>
                      <span aria-hidden="true">▸</span>
                    </div>
                    {i === openSubmenuIndex && (
                      <div style={{ position: 'absolute', left: '100%', top: 0, marginLeft: 4 }}>
                        <MenuButton
                          ref={(el) => { submenuRefs.current[i] = el; }}
                          label={it.label}
                          items={it.items}
                          isSubmenu
                          onRequestClose={() => {
                            setOpenSubmenuIndex(-1);
                            menuRef.current?.querySelector<HTMLElement>(`[data-index="${i}"]`)?.focus();
                          }}
                        />
                      </div>
                    )}
                  </div>
                );
              }
              return null;
            })}
          </div>
        )}
      </div>
    );
  },
);

export { MenuButton, type MenuItem };

/* --------------------------------------------------------------- *
 * Usage:
 *
 *   <MenuButton label="More actions" items={[
 *     { type: 'item', label: 'Edit', onSelect: () => console.log('Edit') },
 *     { type: 'separator' },
 *     { type: 'checkbox', label: 'Word wrap', checked: true, onToggle: () => {} },
 *     { type: 'radio-group', label: 'Theme', value: 'dark',
 *       options: [{value:'light',label:'Light'},{value:'dark',label:'Dark'}],
 *       onChange: (v) => {} },
 *     { type: 'submenu', label: 'Share', items: [
 *       { type: 'item', label: 'Email', onSelect: () => {} },
 *     ]},
 *   ]} />
 *
 * Testing (React Testing Library + user-event):
 *
 *   test('opens with ArrowDown and focuses first item', async () => {
 *     render(<MenuButton label="More" items={[{type:'item',label:'Edit',onSelect:fn}]} />);
 *     const btn = screen.getByRole('button', { name: /more/i });
 *     await user.click(btn);
 *     expect(screen.getByRole('menu')).toBeInTheDocument();
 *     expect(screen.getByRole('menuitem', { name: /edit/i })).toHaveFocus();
 *   });
 *
 *   test('ArrowRight opens submenu and focuses its first item, ArrowLeft returns', async () => {
 *     render(<MenuButton label="More" items={[
 *       { type: 'submenu', label: 'Share', items: [{ type: 'item', label: 'Email', onSelect: fn }] },
 *     ]} />);
 *     await user.click(screen.getByRole('button', { name: /more/i }));
 *     await user.keyboard('{ArrowRight}');
 *     expect(screen.getByRole('menuitem', { name: /email/i })).toHaveFocus();
 *     await user.keyboard('{ArrowLeft}');
 *     expect(screen.getByRole('menuitem', { name: /share/i })).toHaveFocus();
 *   });
 * --------------------------------------------------------------- */
