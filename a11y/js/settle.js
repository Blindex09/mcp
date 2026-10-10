({quiet, cap}) => new Promise((resolve) => {
  // Adaptativo: resolve quando o DOM fica quieto por `quiet` ms; `cap` e' so o teto de seguranca.
  let timer;
  const finish = () => { observer.disconnect(); clearTimeout(timer); clearTimeout(ceiling); resolve(true); };
  const observer = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(finish, quiet); });
  observer.observe(document, {subtree: true, childList: true, attributes: true, characterData: true});
  timer = setTimeout(finish, quiet);
  const ceiling = setTimeout(finish, cap);
})
