"""Cenarios por framework (React, Vue, Svelte, Angular): os mesmos cinco componentes, ruim e bom, em codigo real compilado.

Os componentes estao em frameworks/src/ e viram app-<framework>.js (frameworks/build.mjs). O gerador mede cada um com as sondas do MCP,
na pagina ja montada pelo framework, e mostra o codigo do componente (a regiao "#region nome" da fonte, ou o arquivo .svelte inteiro).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
FONTES = AQUI / "frameworks" / "src"

# componente -> (nome, sonda, alvo do ruim e do bom, o que o ruim quebra, o que corrigir)
TEMAS: dict[str, dict[str, str]] = {
    "acordeao": {
        "nome": "Acordeão", "sonda": "disclosure", "alvo": "#{k}-gatilho",
        "porque_ruim": "O clique funciona só com o mouse. A div não recebe foco, não é anunciada como botão e não diz se está aberta ou fechada.",
        "porque_bom": "Um button com aria-expanded e aria-controls: o leitor de tela anuncia botão, recolhido ou expandido, e Enter e Espaço alternam.",
        "corrigir": "Troque a div por button e mantenha aria-expanded igual ao estado do componente.",
    },
    "dialogo": {
        "nome": "Diálogo", "sonda": "dialog", "alvo": "#{k}-gatilho",
        "porque_ruim": "Para quem vê, abriu uma janela. Para o teclado e o leitor de tela, não é um diálogo: sem papel, sem nome, o foco fica no botão de trás e o Escape não fecha.",
        "porque_bom": "O elemento dialog aberto com showModal() dá papel, nome (pelo título), foco preso, Escape e devolução do foco ao botão.",
        "corrigir": "Use dialog com showModal() em vez de renderizar uma caixa condicional, e ligue o nome ao título com aria-labelledby.",
    },
    "erro": {
        "nome": "Erro de formulário", "sonda": "form_errors", "alvo": "#{k}-enviar",
        "porque_ruim": "Aparece uma frase vermelha ao lado. O campo não é marcado como inválido, a frase não está ligada a ele, o foco não se move e nada é anunciado.",
        "porque_bom": "O campo recebe aria-invalid, o texto do erro fica ligado por aria-describedby e anunciado por role=alert, e o foco vai ao campo.",
        "corrigir": "Marque o campo, ligue a mensagem, mova o foco e mantenha o elemento da mensagem sempre presente.",
    },
    "status": {
        "nome": "Mensagem de status", "sonda": "status_update", "alvo": "#{k}-salvar",
        "porque_ruim": "A região viva só passa a existir junto com o texto. Muitos leitores de tela só falam o que muda dentro de uma região que já estava na página.",
        "porque_bom": "A região role=status fica sempre na página e só o texto muda, então o leitor de tela fala a mensagem.",
        "corrigir": "Renderize a região sempre; troque só o texto dentro dela.",
    },
    "rota": {
        "nome": "Mudança de tela", "sonda": "route_change", "alvo": "#{k}-ir",
        "porque_ruim": "O conteúdo vira Contato, mas o título da aba continua Início, o foco permanece no botão e não há aviso: quem usa leitor de tela não sabe que a tela mudou.",
        "porque_bom": "Depois de atualizar o conteúdo, o título da aba muda, o foco vai ao novo título e há uma mensagem de status.",
        "corrigir": "Ao trocar a tela, atualize document.title, mova o foco para o novo h1 (tabindex -1) e avise numa região de status. O framework não faz isso sozinho.",
    },
}

# Frase sobre o que o proprio framework faz ou deixa de fazer, por componente do tipo ruim.
NOTAS: dict[str, dict[str, str]] = {
    "react": {
        "acordeao": "O JSX compila onClick numa div sem nenhum aviso; só um linter como eslint-plugin-jsx-a11y reclama, e só se estiver configurado.",
        "dialogo": "Renderizar a caixa com {aberto && ...} é o jeito mais comum e o mais frágil. No bom, o ref chama showModal().",
        "erro": "No bom, useId gera o id que liga a mensagem ao campo sem colidir com outros componentes da página.",
        "status": "O {salvo && <div role=\"status\">} cria a região no mesmo instante do texto.",
        "rota": "Nenhum roteador de React move o foco por você. No bom, um useEffect depois da troca cuida do título e do foco.",
    },
    "vue": {
        "acordeao": "O @click numa div compila sem aviso; só um linter como eslint-plugin-vuejs-accessibility reclama, e só se estiver configurado.",
        "dialogo": "O v-if cria e destrói a caixa; o dialog nativo existe sempre e o showModal() só o abre.",
        "erro": "No bom, useId (Vue 3.5) liga a mensagem ao campo, e nextTick garante que o DOM novo existe antes do focus().",
        "status": "O v-if cria a região junto com o texto; o bom usa a região sempre presente.",
        "rota": "O guia oficial do Vue manda devolver o foco ao início da página depois da troca de rota (um span com tabindex -1 antes do link de pular) e não fala de título nem de aviso: no bom, nextTick espera o DOM novo e o componente cuida do foco no novo título, do título da aba e do aviso.",
    },
    "svelte": {
        "acordeao": "Aqui o compilador do Svelte avisa de verdade (veja os avisos medidos abaixo): uma div com clique, sem papel e sem teclado. Não esconda o aviso com svelte-ignore; troque pelo button.",
        "dialogo": "O {#if} cria a caixa só quando abre; o dialog nativo existe sempre e o showModal() o abre.",
        "erro": "No bom, await tick() espera o DOM novo antes de chamar focus().",
        "status": "O {#if} cria a região junto com o texto; o bom usa a região sempre presente.",
        "rota": "O Svelte não move o foco na troca de tela. No bom, await tick() espera o DOM novo e depois cuida do foco e do título.",
    },
    "angular": {
        "acordeao": "O (click) numa div compila sem aviso; só as regras de acessibilidade de template do angular-eslint reclamam, e só se estiverem ativas.",
        "dialogo": "O @if cria a caixa só quando abre; o dialog nativo existe sempre e o showModal() o abre. O CDK também oferece cdkTrapFocus para caixas que não são dialog.",
        "erro": "No bom, o campo recebe o foco no mesmo envio em que a mensagem aparece, e a mensagem fica num elemento sempre presente.",
        "status": "O @if cria a região junto com o texto; o bom usa a região sempre presente. O LiveAnnouncer do CDK cria a sua região na criação do serviço, antes de qualquer texto.",
        "rota": "O Router do Angular não move o foco: a documentação manda ouvir NavigationEnd e focar um elemento da nova tela. Aqui o bom usa o LiveAnnouncer do CDK, foco e título.",
    },
}

PILHAS = {
    "react": ("React", "app-react.js", "react.jsx", "React 19, componentes de função com hooks (useState, useRef, useId, useEffect)."),
    "vue": ("Vue", "app-vue.js", "vue.js", "Vue 3.5, componentes com setup() e template, useId e nextTick."),
    "svelte": ("Svelte", "app-svelte.js", None, "Svelte 5, componentes .svelte com runes ($state, $props), compilados; os avisos de acessibilidade do compilador estão medidos."),
    "angular": ("Angular", "app-angular.js", "angular.ts", "Angular 20, componentes standalone com signals, compilação JIT no pacote e o CDK a11y (LiveAnnouncer)."),
}

ORDEM = ["acordeao", "dialogo", "erro", "status", "rota"]


def regiao(arquivo: str, nome: str) -> str:
    """O trecho entre '#region nome' e '#endregion' da fonte do framework (o codigo que o leitor da pagina ve)."""
    texto = (FONTES / arquivo).read_text(encoding="utf-8")
    m = re.search(rf"//#region {re.escape(nome)}\n(.*?)//#endregion", texto, re.DOTALL)
    if not m:
        raise KeyError(f"regiao {nome} nao encontrada em {arquivo}")
    return m.group(1).strip()


def arquivo_svelte(chave: str) -> str:
    base = "".join(parte.capitalize() for parte in chave.split("-"))
    return f"{base}.svelte"


def codigo(pilha: str, chave: str) -> str:
    if pilha == "svelte":
        return (FONTES / "svelte" / arquivo_svelte(chave)).read_text(encoding="utf-8").strip()
    return regiao(PILHAS[pilha][2] or "", chave)


def exemplos_da(pilha: str) -> list[dict[str, Any]]:
    nome, script, _src, _resumo = PILHAS[pilha]
    saida: list[dict[str, Any]] = []
    for tema in ORDEM:
        t = TEMAS[tema]
        for tipo in ("ruim", "bom"):
            chave = f"{tema}-{tipo}"
            alvo = "css:" + t["alvo"].format(k=chave)
            ex: dict[str, Any] = {
                "tipo": tipo, "titulo": f"{t['nome']} em {nome}: {'como não fazer' if tipo == 'ruim' else 'como fazer'}",
                "pilha": pilha, "chave": chave, "script": script, "sonda": (t["sonda"], alvo),
                "porque": t["porque_" + tipo] + (" " + NOTAS[pilha][tema] if tipo == "ruim" else ""),
                "corrigir": t["corrigir"] if tipo == "ruim" else "Nada a corrigir.",
                "codigo": codigo(pilha, chave),
            }
            if tema == "rota":
                ex["documento"] = f"{pilha}-rota-{tipo}"
                ex["html"] = f'<p><a href="{pilha}-rota-{tipo}.html">Abrir a aplicação de exemplo ({tipo})</a></p>'
            else:
                ex["html"] = f'<div data-exemplo="{chave}"></div>'
            saida.append(ex)
    return saida


def cenarios() -> list[dict[str, Any]]:
    return [
        {
            "slug": f"pilha-{pilha}", "nome": PILHAS[pilha][0], "pilha": pilha,
            "resumo": f"{PILHAS[pilha][3]} Os mesmos cinco componentes (acordeão, diálogo, erro de formulário, mensagem de status e mudança de tela), cada um ruim e bom, em código real compilado. "
                      "O framework não faz acessibilidade por você: o que muda é onde cada um esconde o erro.",
            "exemplos": exemplos_da(pilha),
        }
        for pilha in PILHAS
    ]


def pagina_rota(pilha: str, tipo: str) -> str:
    """Pagina inteira (so o componente de mudanca de tela) para a sonda route_change medir titulo, foco e aviso."""
    chave = f"rota-{tipo}"
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Início | Loja de chás</title>'
        "<style>body{font:1.1rem system-ui;margin:1rem;max-width:40rem} button{min-height:44px;padding:.5rem 1rem;font:inherit}"
        ".so-leitor{position:absolute;left:-9999px}</style></head><body>"
        f'<div data-exemplo="{chave}"></div><script src="{PILHAS[pilha][1]}"></script></body></html>'
    )
