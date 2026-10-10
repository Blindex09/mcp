// Casa do Chá — v3: mesmo comportamento com mouse, agora também com teclado e leitor de tela.

// ---- Combobox de categoria (padrão APG: editável + lista de sugestões) ----
const cat = document.getElementById('cat');
const list = document.getElementById('opts');
const options = Array.from(list.querySelectorAll('[role="option"]'));
let active = -1;

function visible() { return options.filter(o => !o.hidden); }
function setOpen(open) {
  list.hidden = !open;
  cat.setAttribute('aria-expanded', String(open));
  if (!open) setActive(-1);
}
function setActive(i) {
  const vis = visible();
  options.forEach(o => o.removeAttribute('aria-selected'));
  active = i;
  if (i >= 0 && vis[i]) {
    vis[i].setAttribute('aria-selected', 'true');
    cat.setAttribute('aria-activedescendant', vis[i].id);
    vis[i].scrollIntoView({ block: 'nearest' });
  } else {
    cat.removeAttribute('aria-activedescendant');
  }
}
function choose(opt) { cat.value = opt.textContent; setOpen(false); }
function filter() {
  const q = cat.value.toLowerCase();
  options.forEach(o => { o.hidden = !o.textContent.toLowerCase().includes(q); });
}
cat.addEventListener('focus', () => { filter(); setOpen(visible().length > 0); });
cat.addEventListener('input', () => { filter(); setOpen(visible().length > 0); setActive(-1); });
cat.addEventListener('keydown', (e) => {
  const vis = visible();
  if (e.key === 'ArrowDown') { e.preventDefault(); if (list.hidden) { filter(); setOpen(true); } setActive(Math.min(active + 1, visible().length - 1)); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(Math.max(active - 1, 0)); }
  else if (e.key === 'Home' && !list.hidden) { e.preventDefault(); setActive(0); }
  else if (e.key === 'End' && !list.hidden) { e.preventDefault(); setActive(vis.length - 1); }
  else if (e.key === 'Enter' && !list.hidden && active >= 0) { e.preventDefault(); choose(vis[active]); }
  else if (e.key === 'Escape') { if (!list.hidden) { e.preventDefault(); setOpen(false); } }
});
options.forEach(o => o.addEventListener('mousedown', (e) => { e.preventDefault(); choose(o); }));
cat.addEventListener('blur', () => setOpen(false));

// ---- Menu "Produtos" (navegação: botão + lista de links; não é role=menu) ----
const dd = document.querySelector('.dropdown');
const trigger = dd.querySelector('.trigger');
const menu = document.getElementById('menu-produtos');
function setMenu(open) { menu.hidden = !open; trigger.setAttribute('aria-expanded', String(open)); }
trigger.addEventListener('click', () => setMenu(menu.hidden));
dd.addEventListener('mouseenter', () => setMenu(true));
dd.addEventListener('mouseleave', () => { if (!dd.contains(document.activeElement)) setMenu(false); });
dd.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !menu.hidden) { setMenu(false); trigger.focus(); } });
dd.addEventListener('focusout', (e) => { if (!dd.contains(e.relatedTarget)) setMenu(false); });

// ---- FAQ (acordeão: botão com aria-expanded) ----
document.querySelectorAll('.faq-q').forEach(btn => btn.addEventListener('click', () => {
  const open = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!open));
  document.getElementById(btn.getAttribute('aria-controls')).hidden = open;
}));

// ---- Comprar: o aviso agora é anunciado (role=status) ----
const toast = document.getElementById('toast');
let toastTimer;
document.querySelectorAll('.btn').forEach(b => b.addEventListener('click', () => {
  const nome = b.closest('.card').querySelector('h3').textContent;
  toast.textContent = 'Adicionado ao carrinho: ' + nome;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.textContent = ''; }, 6000);
}));
