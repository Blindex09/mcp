// Casa do Chá — v1 (original): tudo funciona com mouse.
const cat = document.getElementById('cat');
const opts = document.getElementById('opts');
cat.addEventListener('focus', () => opts.classList.add('open'));
cat.addEventListener('input', () => {
  const q = cat.value.toLowerCase();
  opts.querySelectorAll('.opt').forEach(o => { o.style.display = o.textContent.toLowerCase().includes(q) ? '' : 'none'; });
});
opts.querySelectorAll('.opt').forEach(o => o.addEventListener('mousedown', () => {
  cat.value = o.textContent;
  opts.classList.remove('open');
}));
cat.addEventListener('blur', () => setTimeout(() => opts.classList.remove('open'), 150));

document.querySelectorAll('.faq-q').forEach(q => q.addEventListener('click', () => q.parentElement.classList.toggle('open')));

const toast = document.getElementById('toast');
document.querySelectorAll('.btn').forEach(b => b.addEventListener('click', () => {
  const nome = b.parentElement.querySelector('h3').textContent;
  toast.textContent = 'Adicionado ao carrinho: ' + nome;
  setTimeout(() => { toast.textContent = ''; }, 4000);
}));
