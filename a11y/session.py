"""Sessao de navegador persistente: os "olhos e maos" para testar como usuario.

Divisao de papeis (regra do projeto): o MODELO julga (o que e cada elemento, onde o usuario
travou, o que melhorar); este modulo so (a) executa acoes e (b) devolve FATOS observados.
O harness impoe o que e PERMITIDO por persona - ex.: um usuario de teclado nao tem mouse,
independente do que o modelo "pretende".

Seguranca: so http/https (demais esquemas abortados), downloads recusados, dialogos JS
dispensados e registrados, popups fechados e registrados, uma sessao por vez, expira por
inatividade, nenhum JavaScript arbitrario exposto ao cliente.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import page_scripts as js
from .audit import _launch, validate_url
from .patience import PATIENCE_FACTOR
from .provisioning import check_browser_name, provisioner_for

IDLE_MIN_S = 600  # so o piso; o limite real cresce com o ritmo da conversa (10x o maior intervalo visto)
LONG_LIVED_TYPES = ('eventsource', 'websocket', 'ping', 'beacon')  # nunca terminam por natureza: nao contam como 'trabalhando'
LONG_POLL_FLOOR_S = 30.0  # requisicao em voo por mais que isso E muito mais que as ja concluidas: tratada como long-poll
QUIET_FLOOR_S = 2.0  # quietude minima antes de desistir de esperar um elemento
READY_SLICE_MS = 1000
ACTION_TIMEOUT_MS = 10_000  # so a 1a espera de uma acao; se estourar, repete com 3x e depois 9x
SETTLE_QUIET_MS = 200  # silencio do DOM que caracteriza "assentou"
SETTLE_CAP_MS = 3_000  # so o PISO da espera de mutacoes; requisicoes em andamento sempre sao esperadas
_ID_RE = re.compile(r"e\d+")
_SAFE_CSS_PROP = re.compile(r"^[a-z-]+$")
_ALLOWED_SCHEMES = ("http:", "https:", "data:", "blob:", "about:")
_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
_MUTATION_MODES = ("auto", "ask", "allow", "block")
_MAX_TREE_LINES = 400

# Personas: emulacao de navegador + o que o harness PERMITE fazer.
PERSONAS: dict[str, dict[str, Any]] = {
    "default": {"about": "usuario com mouse e visao, sem restricoes"},
    "keyboard": {
        "about": "so teclado: sem mouse; chega aos elementos com Tab/setas (a11y_reach ou a11y_act press)",
        "no_pointer": True,
    },
    "screen_reader": {
        "about": "leitor de tela: sem mouse e sem ver a tela; percebe so a arvore de acessibilidade e o que e anunciado",
        "no_pointer": True,
        "no_visual": True,
    },
    "low_vision": {
        "about": "zoom de 400% (equivale a 320 px CSS de largura): testa reflow e legibilidade",
        "viewport": {"width": 320, "height": 256},
    },
    "mobile_touch": {
        "about": "celular com toque",
        "viewport": {"width": 390, "height": 844},
        "is_mobile": True,
        "has_touch": True,
    },
    "reduced_motion": {"about": "prefere menos movimento", "reduced_motion": "reduce"},
    "forced_colors": {"about": "modo de alto contraste do sistema", "forced_colors": "active"},
}
_POINTER_ACTIONS = {"click", "hover", "focus", "select"}
_KEYBOARD_ACTIONS = {"press", "type", "wait"}


@dataclass
class Coverage:
    """O que ESTA sessao ja viu e provou (fatos de cobertura, sem opiniao)."""

    described: set[str] = field(default_factory=set)  # ids listados pelo dossie
    probed: set[str] = field(default_factory=set)  # ids sobre os quais se agiu / que se mediu
    discovered_total: int = 0
    page_map: bool = False
    frames_mapped: int = 0
    design_measured: bool = False
    stress_kinds: set[str] = field(default_factory=set)
    urls: set[str] = field(default_factory=set)
    actions: int = 0


def is_local_dev(url: str | None) -> bool:
    """Site de desenvolvimento local (localhost, 127.0.0.1, ::1, *.localhost, *.test) ou HTML passado direto."""
    if not url:
        return True
    host = (urlparse(url.strip()).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith((".localhost", ".test"))


def effective_policy(mode: str, url: str | None) -> str:
    """auto: site local = allow (aprovacao desligada); site real = ask (aprovacao ligada: pede antes)."""
    if mode == "auto":
        return "allow" if is_local_dev(url) else "ask"
    return mode


def payload_summary(method: str, url: str, post_data: str | None, content_type: str, navigation: bool) -> dict[str, Any]:
    """O QUE a requisicao mudaria, sem vazar valores: nomes dos campos e tamanhos, nunca o conteudo (pode ter senha)."""
    fields: list[str] = []
    ctype = (content_type or "").lower()
    if post_data:
        if "json" in ctype:
            try:
                data = json.loads(post_data)
                fields = [f"{k} ({len(str(v))} caracteres)" for k, v in (data.items() if isinstance(data, dict) else [])]
            except ValueError:
                fields = [f"corpo JSON ilegivel ({len(post_data)} caracteres)"]
        elif "x-www-form-urlencoded" in ctype:
            fields = [f"{k} ({len(v[0]) if v else 0} caracteres)" for k, v in parse_qs(post_data, keep_blank_values=True).items()]
        else:
            fields = [f"corpo de {len(post_data)} caracteres"]
    return {"method": method.upper(), "url": url[:120], "kind": "envio de formulario" if navigation else "chamada da pagina", "fields": fields[:20]}


class SessionError(Exception):
    """Erro esperado de uso da sessao (mensagem para o cliente)."""


def _key_of(lines: list[str]) -> Counter[str]:
    return Counter(line.rstrip() for line in lines)


def tree_diff(before: list[str], after: list[str], cap: int = 40) -> dict[str, list[str]]:
    """Linhas da arvore de acessibilidade que sumiram/apareceram (fato objetivo)."""
    b, a = _key_of(before), _key_of(after)
    removed = list((b - a).elements())[:cap]
    added = list((a - b).elements())[:cap]
    return {"removed": removed, "added": added}


class Session:
    def __init__(self) -> None:
        self.pw: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.persona = "default"
        self.cdp: Any = None  # so no Chromium; Firefox/WebKit usam a descoberta por DOM + aria snapshot
        self.browser_name = "chromium"
        self.coverage = Coverage()
        self.mutation_policy = "allow"  # allow | ask | block (resolvido no open)
        self.mutation_mode = "auto"
        self.blocked: list[str] = []
        self.pending: dict[str, dict[str, Any]] = {}  # pedidos de aprovacao retidos
        self._approval_seq = 0
        self._allow_once: set[tuple[str, str]] = set()  # (metodo, url) aprovados: passam UMA vez
        self._last: dict[str, Any] = {}  # ultima acao da pessoa (para refazer apos aprovar uma navegacao)
        self.stop_requested = False  # pedido de cancelamento de um teste autonomo em andamento
        self._inflight: set[Any] = set()  # requisicoes em andamento (sinal de que a pagina ainda esta reagindo)
        self._req_t0: dict[Any, float] = {}
        self._req_durations: list[float] = []  # quanto o site demorou para responder: adapta as esperas
        self._req_count = 0
        self._max_gap = 0.0  # maior intervalo entre chamadas da conversa
        self._frame_of: dict[str, int] = {}  # id do dossie -> indice do frame que o contem (Playwright)
        self._ids: dict[int, str] = {}  # backendNodeId -> id estavel (eN) entre chamadas do dossie
        self.last_used = time.monotonic()
        self.lock = asyncio.Lock()
        self.dialogs: list[str] = []
        self.popups: list[str] = []
        self.console_errors: list[str] = []
        self._live_seen = 0
        self._console_seen = 0
        self._watchdog: asyncio.Task[None] | None = None

    @property
    def allow_mutations(self) -> bool:
        return self.mutation_policy == "allow"

    # ----------------------------------------------------------- ciclo de vida
    async def open(
        self, url: str | None, html: str | None, persona: str = "default", color_scheme: str | None = None,
        browser: str = "chromium",
        allow_mutations: str = "auto",
    ) -> dict[str, Any]:
        if bool(url) == bool(html):
            raise SessionError("informe exatamente um entre url e html")
        if persona not in PERSONAS:
            raise SessionError(f"persona invalida: {persona}. Opcoes: {sorted(PERSONAS)}")
        if color_scheme not in (None, "light", "dark"):
            raise SessionError("color_scheme deve ser light ou dark")
        if allow_mutations not in _MUTATION_MODES:
            raise SessionError(f"allow_mutations deve ser um de: {', '.join(_MUTATION_MODES)}")
        try:
            check_browser_name(browser)
        except Exception as e:
            raise SessionError(str(e)) from e
        if url:
            validate_url(url)
        await provisioner_for(browser).ensure()  # instala Playwright/navegador sozinho se faltar
        await self.close()
        self.stop_requested = False
        from playwright.async_api import async_playwright

        cfg = PERSONAS[persona]
        opts: dict[str, Any] = {"accept_downloads": False}
        notes: list[str] = []
        for key in ("viewport", "is_mobile", "has_touch", "reduced_motion", "forced_colors"):
            if key in cfg:
                if key == "is_mobile" and browser == "firefox":
                    notes.append("Firefox nao emula is_mobile: o celular usa so viewport e toque")
                    continue
                opts[key] = cfg[key]
        if color_scheme:
            opts["color_scheme"] = color_scheme
        self.pw = await async_playwright().start()
        try:
            self.browser = await _launch(self.pw, browser)
            self.context = await self.browser.new_context(**opts)
            self.mutation_mode = allow_mutations
            self.mutation_policy = effective_policy(allow_mutations, url)
            self.blocked = []
            self.pending = {}
            await self.context.route("**/*", self._route)
            await self.context.add_init_script(js.LIVE_OBSERVER_JS)
            await self.context.add_init_script(js.LISTENER_HOOK_JS)
            await self.context.add_init_script(js.ACTIVITY_JS)
            self.context.on("page", self._on_popup)
            self.context.on("request", self._request_started)
            self.context.on("requestfinished", self._request_done)
            self.context.on("requestfailed", self._request_done)
            self.page = await self.context.new_page()
            if browser == "chromium":
                self.cdp = await self.context.new_cdp_session(self.page)
                await self.cdp.send("DOM.enable")
                await self.cdp.send("Accessibility.enable")
            else:
                notes.append(
                    f"{browser}: sem CDP. O dossie usa o tabIndex do navegador (focavel) e cursor:pointer (sinal mais fraco) e o papel/nome "
                    "vem do aria snapshot do Playwright; nao detecta clicavel por addEventListener; a11y_focus_style foca de verdade (dispara eventos)"
                )
            self.page.set_default_timeout(ACTION_TIMEOUT_MS)
            self.page.on("dialog", self._on_dialog)
            self.page.on("console", self._on_console)
            if url:
                await self.page.goto(url.strip(), wait_until="load", timeout=30_000)
            else:
                await self.page.set_content(html or "", wait_until="load")
        except Exception:
            await self.close()
            raise
        self.persona = persona
        self.browser_name = browser
        self._req_durations, self._req_t0, self._req_count = [], {}, 0  # o ritmo aprendido e' DESTE site, nao do anterior
        self.mutation_mode = allow_mutations
        self.mutation_policy = effective_policy(allow_mutations, url)
        self.blocked = []
        self.coverage = Coverage()
        self.coverage.urls.add(self.page.url)
        self.dialogs, self.popups, self.console_errors = [], [], []
        self._live_seen = self._console_seen = 0
        self.last_used = time.monotonic()
        self._watchdog = asyncio.create_task(self._idle_watchdog())
        return {
            "opened": self.page.url, "persona": persona, "browser": browser, "about": cfg["about"],
            "title": await self.page.title(), "limits": notes,
            "mutations": {
                "allow": "permitidas",
                "ask": "COM APROVACAO: POST/PUT/PATCH/DELETE e envio de formulario ficam retidos ate a pessoa aprovar (a11y_approve)",
                "block": "BLOQUEADAS: POST/PUT/PATCH/DELETE e envio de formulario nao sao enviados (modo estrito)",
            }[self.mutation_policy],
        }

    async def close(self) -> bool:
        was_open = self.page is not None
        for item in list(self.pending.values()):
            fut = item.get("future")
            if fut is not None and not fut.done():
                fut.set_result("deny")  # nada fica preso; sem aprovacao nao foi enviado
        if self._watchdog and self._watchdog is not asyncio.current_task():
            self._watchdog.cancel()
        self._watchdog = None
        for obj, method in ((self.browser, "close"), (self.pw, "stop")):
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:  # noqa: BLE001, S110 - fechando: ja pode ter caido
                    pass
        self.pw = self.browser = self.context = self.page = self.cdp = None
        self._ids = {}
        self._frame_of = {}
        self._inflight = set()
        self._req_t0 = {}
        return was_open

    def idle_limit_s(self) -> float:
        """Sessao parada so e' fechada (liberar recurso, nao encerrar trabalho) depois de um tempo que cresce com o ritmo de quem conversa."""
        return max(IDLE_MIN_S, 10 * self._max_gap)

    async def _idle_watchdog(self) -> None:
        while self.page is not None:
            await asyncio.sleep(30)
            if time.monotonic() - self.last_used > self.idle_limit_s():
                await self.close()
                return

    # ------------------------------------------------- guardas de seguranca
    async def _route(self, route: Any) -> None:
        req = route.request
        if not req.url.lower().startswith(_ALLOWED_SCHEMES):
            await route.abort()
            return
        key = (req.method.upper(), req.url)
        if key in self._allow_once:  # aprovado pela pessoa: passa uma vez
            self._allow_once.discard(key)
            await route.continue_()
            return
        if req.method.upper() in _SAFE_METHODS or self.mutation_policy == "allow":
            await route.continue_()
            return
        navigation = req.is_navigation_request()
        if self.mutation_policy == "ask":
            self._approval_seq += 1
            aid = f"a{self._approval_seq}"
            item: dict[str, Any] = {
                "id": aid, **payload_summary(req.method, req.url, req.post_data, req.headers.get("content-type", ""), navigation),
                "replay": dict(self._last), "navigation": navigation, "full_url": req.url,
            }
            self.pending[aid] = item
            self._inflight.discard(req)
            if navigation:
                # Reter uma NAVEGACAO deixaria a pagina "navegando" (qualquer leitura travaria). A pagina fica onde esta e, se a pessoa
                # aprovar, a acao dela e refeita UMA vez com esta requisicao liberada.
                await route.fulfill(status=204, body="")
                return
            item["future"] = asyncio.get_running_loop().create_future()
            decision = await item["future"]  # chamada da pagina (fetch/XHR): retida ate a pessoa decidir, sem relogio
            self.pending.pop(aid, None)
            if decision == "allow":
                await route.continue_()
                return
            self.blocked.append(f"{req.method} {req.url[:100]} (nao aprovada)")
            await route.abort()
            return
        self.blocked.append(f"{req.method} {req.url[:100]}")  # block: modo estrito escolhido pela pessoa
        if navigation:
            await route.fulfill(status=204, body="")  # a pagina continua onde esta (abortar levaria a uma pagina de erro)
        else:
            await route.abort()

    @staticmethod
    def _full_url(item: dict[str, Any]) -> str:
        return str(item.get("full_url") or item["url"])

    async def _replay(self, last: dict[str, Any]) -> None:
        page = self._need()
        action, target, value = last.get("action"), last.get("target"), last.get("value") or ""
        if action == "click" and target:
            await self._locator(target).click(timeout=ACTION_TIMEOUT_MS * PATIENCE_FACTOR, no_wait_after=True)
        elif action == "press":
            await page.keyboard.press(value)

    def pending_approvals(self) -> list[dict[str, Any]]:
        return [{k: v for k, v in p.items() if k not in ("future", "replay", "full_url")} for p in self.pending.values()]

    async def decide(self, decision: str, ids: list[str] | None = None) -> dict[str, Any]:
        """Aprovacao da pessoa: allow (esses pedidos) | deny | allow_all (aprovacao desligada para o resto da sessao)."""
        if decision not in ("allow", "deny", "allow_all"):
            raise SessionError("decision deve ser allow, deny ou allow_all")
        self._need()
        before = await self._state()
        if decision == "allow_all":
            self.mutation_policy = "allow"
        targets = list(self.pending) if (decision == "allow_all" or not ids) else [i for i in ids if i in self.pending]
        if ids and not targets:
            raise SessionError(f"nenhum pedido pendente com esses ids: {', '.join(ids)}")
        decided = []
        replays: list[dict[str, Any]] = []
        for aid in targets:
            item = self.pending.get(aid)
            if not item:
                continue
            allow = decision in ("allow", "allow_all")
            if item.get("navigation"):
                self.pending.pop(aid, None)
                if allow:
                    self._allow_once.add((item["method"], self._full_url(item)))
                    replays.append(item["replay"])
                else:
                    self.blocked.append(f"{item['method']} {item['url'][:100]} (nao aprovada)")
                decided.append({"id": aid, "method": item["method"], "url": item["url"], "decision": "allow" if allow else "deny"})
            elif not item["future"].done():
                item["future"].set_result("allow" if allow else "deny")
                decided.append({"id": aid, "method": item["method"], "url": item["url"], "decision": "allow" if allow else "deny"})
        for last in replays:  # refaz a acao da pessoa UMA vez, agora com a requisicao liberada
            await self._replay(last)
        await self._settle()
        after = await self._state()
        diff = tree_diff(before["tree"], after["tree"])
        return {
            "decided": decided, "policy_now": self.mutation_policy,
            "url_changed": None if before["url"] == after["url"] else {"from": before["url"], "to": after["url"]},
            "tree_added": diff["added"], "tree_removed": diff["removed"], "announcements": await self._live_new(),
            "still_pending": self.pending_approvals(),
        }

    async def _on_dialog(self, dialog: Any) -> None:
        self.dialogs.append(f"{dialog.type}: {dialog.message[:200]}")
        await dialog.dismiss()

    def _on_popup(self, page: Any) -> None:
        if self.page is not None and page is not self.page:
            self.popups.append(page.url or "(sem url)")
            asyncio.ensure_future(page.close())

    def _request_started(self, request: Any) -> None:
        self._req_count += 1
        if request.resource_type not in LONG_LIVED_TYPES:
            self._inflight.add(request)
            self._req_t0[request] = time.monotonic()

    def _request_done(self, request: Any) -> None:
        self._req_count += 1
        t0 = self._req_t0.pop(request, None)
        if t0 is not None and request in self._inflight:
            self._req_durations.append(time.monotonic() - t0)
            del self._req_durations[:-50]
        self._inflight.discard(request)

    def _on_console(self, msg: Any) -> None:
        if msg.type == "error":
            self.console_errors.append(msg.text[:200])

    def _need(self) -> Any:
        if self.page is None:
            raise SessionError("nenhuma sessao aberta: chame a11y_open primeiro")
        now = time.monotonic()
        self._max_gap = max(self._max_gap, min(now - self.last_used, 6 * 3600))
        self.last_used = now
        return self.page

    def _locator(self, target: str) -> Any:
        page = self._need()
        t = (target or "").strip()
        if _ID_RE.fullmatch(t):
            self.coverage.probed.add(t)
            frames = page.frames
            idx = self._frame_of.get(t, 0)
            scope = frames[idx] if idx < len(frames) else page
            loc = scope.locator(f'[data-a11y-id="{t}"]')  # o seletor do Playwright atravessa Shadow DOM aberto
        elif t.startswith("css:") and 0 < len(t) <= 300:
            loc = page.locator(t[4:])
        else:
            raise SessionError("target deve ser um id do dossie (ex.: e12) ou 'css:<seletor>'")
        return loc.first

    def _guard(self, action: str) -> None:
        cfg = PERSONAS[self.persona]
        if cfg.get("no_pointer") and action in _POINTER_ACTIONS:
            raise SessionError(
                f"persona '{self.persona}' nao tem mouse: '{action}' nao esta disponivel. "
                "Navegue com a11y_reach / a11y_act press (Tab, setas, Enter, Espaco, Escape)."
            )

    # ------------------------------------------------------------- observacao
    async def _focus_probe(self) -> dict[str, Any] | None:
        """Quem tem o foco AGORA, atravessando Shadow DOM aberto e iframes (o foco pode estar dentro de um frame)."""
        page = self._need()
        f = await page.evaluate(js.FOCUS_JS)
        if f and f.get("tag") in ("iframe", "frame"):
            for fr in page.frames[1:]:
                try:
                    inner = await fr.evaluate(js.FOCUS_JS)
                except Exception:  # noqa: BLE001, S112 - frame fechado
                    continue
                if inner:
                    inner["in_frame"] = fr.url[:60]
                    return dict(inner)
        return dict(f) if f else None

    async def _tree_lines(self) -> list[str]:
        page = self._need()
        try:
            snap = str(await page.locator("body").aria_snapshot())
        except Exception:  # noqa: BLE001 - pagina em transicao
            return []
        return snap.splitlines()[:_MAX_TREE_LINES]

    async def _live_new(self) -> list[dict[str, str]]:
        page = self._need()
        items = await page.evaluate("() => window.__a11yLive || []")
        new = items[self._live_seen :]
        self._live_seen = len(items)
        return new[:20]

    async def _state(self) -> dict[str, Any]:
        page = self._need()
        return {
            "url": page.url,
            "title": await page.title(),
            "focus": await self._focus_probe(),
            "tree": await self._tree_lines(),
        }

    async def observe(self) -> dict[str, Any]:
        st = await self._state()
        return {
            "url": st["url"], "title": st["title"], "focus": st["focus"], "persona": self.persona,
            "accessibility_tree": st["tree"], "recent_announcements": await self._live_new(),
            "js_dialogs": self.dialogs[-5:], "popups_blocked": self.popups[-5:],
            "console_errors": self.console_errors[-5:], "mutations_blocked": self.blocked[-5:],
            "approvals_pending": self.pending_approvals(),
        }

    async def _discover(self, limit: int = 600) -> tuple[list[dict[str, Any]], int]:
        """O NAVEGADOR aponta o que e focavel (arvore de acessibilidade) ou clicavel (DOMSnapshot.isClickable,
        que inclui quem so tem addEventListener), em TODOS os documentos: pagina, Shadow DOM aberto/fechado e iframes.
        Nenhuma lista de tags nem heuristica de cursor."""
        cdp = self.cdp
        if cdp is None:
            return await self._discover_dom(limit)
        await cdp.send("DOM.getDocument", {"depth": 0})
        snap = await cdp.send("DOMSnapshot.captureSnapshot", {"computedStyles": [], "includeDOMRects": True})
        strings = snap["strings"]
        found: list[dict[str, Any]] = []
        for di, doc in enumerate(snap["documents"]):
            nodes = doc["nodes"]
            clickable = set(nodes.get("isClickable", {}).get("index", []))
            layout = doc["layout"]
            rendered = {i for i, b in zip(layout["nodeIndex"], layout["bounds"], strict=False) if b[2] > 0 and b[3] > 0}
            frame_id = strings[doc["frameId"]] if doc.get("frameId", -1) >= 0 else None
            try:
                params = {"frameId": frame_id} if di > 0 and frame_id else {}
                ax_nodes = (await cdp.send("Accessibility.getFullAXTree", params))["nodes"]
            except Exception:  # noqa: BLE001 - frame sem arvore acessivel: segue so com o clicavel
                ax_nodes = []
            ax_by: dict[int, dict[str, Any]] = {}
            for n in ax_nodes:
                bid = n.get("backendDOMNodeId")
                if bid is None:
                    continue
                props = {p["name"]: p["value"].get("value") for p in n.get("properties", [])}
                ax_by[bid] = {
                    "role": (n.get("role") or {}).get("value"), "name": (n.get("name") or {}).get("value") or "",
                    "description": (n.get("description") or {}).get("value") or None,
                    "ignored": bool(n.get("ignored")), "properties": props,
                }
            for idx, bid in enumerate(nodes["backendNodeId"]):
                if nodes["nodeType"][idx] != 1 or idx not in rendered or strings[nodes["nodeName"][idx]] in ("HTML", "BODY"):
                    continue
                ax = ax_by.get(bid)
                focusable = bool(ax and not ax["ignored"] and ax["properties"].get("focusable"))
                is_clickable = idx in clickable
                if focusable or is_clickable:
                    found.append({"backend": bid, "focusable": focusable, "clickable": is_clickable, "ax": ax, "document": di})
        total = len(found)
        found = found[:limit]
        pushed = await cdp.send("DOM.pushNodesByBackendIdsToFrontend", {"backendNodeIds": [f["backend"] for f in found]})

        async def tag(item: dict[str, Any], node_id: int) -> None:
            eid = self._ids.setdefault(item["backend"], f"e{len(self._ids) + 1}")
            item["id"] = eid
            if node_id:
                await cdp.send("DOM.setAttributeValue", {"nodeId": node_id, "name": "data-a11y-id", "value": eid})

        for item, node_id in zip(found, pushed["nodeIds"], strict=False):
            await tag(item, node_id)
        await self._map_ids_to_frames()
        return found, total

    async def _map_ids_to_frames(self) -> None:
        """Descobre em qual frame do Playwright cada id esta (o seletor atravessa Shadow DOM aberto)."""
        page = self._need()
        self._frame_of = {}
        for fi, fr in enumerate(page.frames):
            try:
                ids = await fr.locator("[data-a11y-id]").evaluate_all("els => els.map(e => e.getAttribute('data-a11y-id'))")
            except Exception:  # noqa: BLE001, S112 - frame fechado durante a leitura
                continue
            for i in ids:
                self._frame_of[i] = fi

    async def _discover_dom(self, limit: int) -> tuple[list[dict[str, Any]], int]:
        """Firefox/WebKit (sem CDP): focavel = tabIndex do navegador; clicavel = listener registrado (gancho) ou propriedade on*;
        cursor:pointer entra como sinal MAIS FRACO. Percorre Shadow DOM aberto e cada iframe."""
        page = self._need()
        found: list[dict[str, Any]] = []
        total = 0
        counter = 0
        for fi, fr in enumerate(page.frames):
            try:
                res = await fr.evaluate(js.DISCOVER_JS, {"start": counter, "limit": max(0, limit - len(found))})
            except Exception:  # noqa: BLE001, S112 - frame fechado/inacessivel
                continue
            counter = int(res["next"])
            total += int(res["total"])
            for f in res["found"]:
                found.append({
                    "id": f["id"], "focusable": f["focusable"], "clickable": True if f["listener"] else None,
                    "pointer_cursor": f["pointer_cursor"], "ax": None, "frame": fi,
                })
                self._frame_of[f["id"]] = fi
        return found, total

    @staticmethod
    def parse_snapshot_head(snapshot: str) -> dict[str, Any] | None:
        """Le a 1a linha do aria snapshot do Playwright: `- role "nome" [estado] [estado=v]` (estrutura, nao semantica)."""
        line = next((ln.strip() for ln in snapshot.splitlines() if ln.strip().startswith("- ")), "")
        if not line:
            return None
        body = line[2:].rstrip(":")
        role, _, rest = body.partition(" ")
        name = ""
        if rest.startswith('"'):
            end = rest.find('"', 1)
            while end != -1 and rest[end - 1] == "\\":
                end = rest.find('"', end + 1)
            name = rest[1:end] if end != -1 else rest[1:]
            rest = rest[end + 1 :] if end != -1 else ""
        attrs = [a.strip("[]") for a in rest.split() if a.startswith("[") and a.endswith("]")]
        return {"role": role.rstrip(":"), "name": name, "description": None, "ignored": False,
                "properties": {"attrs": attrs}, "source": "playwright-aria-snapshot"}

    async def _facts_of(self, item: dict[str, Any], scope: str | None) -> dict[str, Any] | None:
        """Fatos de UM elemento, na propria raiz dele (Shadow DOM aberto/fechado, iframe)."""
        if self.cdp is not None and "backend" in item:
            cdp = self.cdp
            oid = (await cdp.send("DOM.resolveNode", {"backendNodeId": item["backend"]}))["object"]["objectId"]
            try:
                r = await cdp.send("Runtime.callFunctionOn", {
                    "objectId": oid, "functionDeclaration": js.DOSSIER_ITEM_JS, "arguments": [{"value": scope}], "returnByValue": True,
                })
            finally:
                await cdp.send("Runtime.releaseObject", {"objectId": oid})
            val = r.get("result", {}).get("value")
            return dict(val) if val else None
        loc = self._locator_raw(item["id"])
        val = await loc.evaluate(f"(el, scope) => ({js.DOSSIER_ITEM_JS}).call(el, scope)", scope)
        return dict(val) if val else None

    def _locator_raw(self, eid: str) -> Any:
        page = self._need()
        frames = page.frames
        idx = self._frame_of.get(eid, 0)
        return (frames[idx] if idx < len(frames) else page).locator(f'[data-a11y-id="{eid}"]').first

    async def dossier(self, scope: str = "", max_elements: int = 60) -> dict[str, Any]:
        """FATOS dos elementos que o navegador aponta como focaveis/clicaveis (pagina, Shadow DOM, iframes), com papel e
        nome COMPUTADOS por ele quando ha CDP (Chromium)."""
        page = self._need()
        limit = max(1, min(max_elements, 200))
        found, total = await self._discover()
        found = [f for f in found if "id" in f]
        elements: list[dict[str, Any]] = []
        outside_scope = 0
        over_limit = 0
        for chunk_start in range(0, len(found), 40):
            chunk = found[chunk_start : chunk_start + 40]
            facts = await asyncio.gather(*(self._facts_of(f, scope or None) for f in chunk), return_exceptions=True)
            for f, fact in zip(chunk, facts, strict=False):
                if isinstance(fact, BaseException) or fact is None:
                    outside_scope += 1
                    continue
                if len(elements) >= limit:
                    over_limit += 1
                    continue
                fact["focusable"], fact["clickable"] = f["focusable"], f["clickable"]
                if self.cdp is None:
                    fact["pointer_cursor"] = f.get("pointer_cursor")
                    snap = await self._locator_raw(f["id"]).aria_snapshot()
                    f["ax"] = self.parse_snapshot_head(str(snap))
                fact["computed"] = f["ax"]  # papel, nome, descricao e propriedades como o navegador os expoe (None = fora da arvore)
                fact["actionable"] = f["id"] in self._frame_of  # False: Shadow DOM fechado (medido, mas o Playwright nao consegue agir)
                elements.append(fact)
        result: dict[str, Any] = {
            "url": page.url, "title": await page.title(), "elements": elements, "browser": self.browser_name,
            "discovered_total": total, "discovery_truncated": total > len(found), "not_in_scope_or_gone": outside_scope,
            "not_listed_over_limit": over_limit, "frames": len(page.frames),
        }
        self.coverage.described |= {e["id"] for e in elements}
        self.coverage.discovered_total = total
        result["note"] = "ids sao atributos data-a11y-id colocados na pagina; cobre a pagina, Shadow DOM e iframes"
        if scope and not elements:
            result["scope_note"] = f"nenhum elemento interativo dentro de {scope!r} (o seletor e' aplicado na raiz de cada elemento)"
        limits: list[str] = []
        if self.cdp is None:
            limits.append("sem CDP: clickable so por listener registrado/propriedade on* (nao ve delegacao a ancestrais); papel/nome pelo aria snapshot do Playwright")
        if any(not e["actionable"] for e in elements):
            limits.append("elementos em Shadow DOM fechado foram medidos mas nao podem receber acoes (actionable=false)")
        if limits:
            result["limits"] = limits
        return result

    async def page_map(self, scope: str = "") -> dict[str, Any]:
        """FATOS de todo o conteudo da pagina (nao so o interativo), inclusive Shadow DOM aberto e cada iframe."""
        page = self._need()
        main = dict(await page.evaluate(js.PAGE_MAP_JS, scope or None))
        if "error" in main:
            return main
        frames: list[dict[str, Any]] = []
        for i, fr in enumerate(page.frames[1:], start=1):
            try:
                fm = dict(await fr.evaluate(js.PAGE_MAP_JS, None))
                frames.append({"frame": i, "url": fr.url[:100], "map": fm})
            except Exception as e:  # noqa: BLE001 - frame fechado/inacessivel: registra e segue
                frames.append({"frame": i, "url": fr.url[:100], "error": f"{type(e).__name__}: {str(e)[:80]}"})
        delegated = await page.evaluate("() => window.__a11yDelegated || []")
        self.coverage.page_map = True
        self.coverage.frames_mapped = len([f for f in frames if "map" in f]) + 1
        return {
            "main": main, "frames": frames, "browser": self.browser_name, "delegated_listeners": delegated,
            "note": "Shadow DOM fechado nao e visivel a JavaScript; fatos sao aritmetica sobre DOM/CSS, sem julgamento. "
                    "delegated_listeners: acoes tratadas por document/window/raiz (o alvo real nao e conhecido)",
        }

    def coverage_report(self) -> dict[str, Any]:
        """Fatos sobre o que foi coberto NESTA sessao e o que ficou de fora (para o relatorio dizer a verdade)."""
        page = self._need()
        c = self.coverage
        never_probed = sorted(c.described - c.probed, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
        not_listed = max(0, c.discovered_total - len(c.described))
        gaps: list[str] = []
        if not c.described:
            gaps.append("o dossie nao foi consultado: nenhum elemento interativo foi listado")
        if not_listed:
            gaps.append(f"{not_listed} elemento(s) interativo(s) descoberto(s) nao foram listados (limite por chamada; use scope ou max_elements)")
        if never_probed:
            gaps.append(f"{len(never_probed)} elemento(s) listado(s) nunca foram sondados por comportamento")
        if not c.page_map:
            gaps.append("o mapa da pagina nao foi consultado: titulos, imagens, links, formularios, tabelas, midia e ordem de leitura sem fatos")
        elif c.frames_mapped < len(page.frames):
            gaps.append(f"{len(page.frames) - c.frames_mapped} iframe(s) sem mapa")
        if not c.design_measured:
            gaps.append("a linguagem de design nao foi medida")
        for kind in ("reflow_320", "text_spacing"):
            if kind not in c.stress_kinds:
                gaps.append(f"estresse '{kind}' nao rodou")
        if c.actions == 0:
            gaps.append("nenhuma acao foi executada: nada foi provado por comportamento")
        if self.blocked:
            gaps.append(f"{len(self.blocked)} requisicao(oes) que alterariam dados nao foram enviadas (bloqueadas ou nao aprovadas): o resultado dessas acoes nao foi observado")
        if self.pending:
            gaps.append(f"{len(self.pending)} pedido(s) de aprovacao ainda pendente(s): a pessoa precisa decidir (a11y_approve)")
        return {
            "browser": self.browser_name, "persona": self.persona,
            "interactive": {"discovered": c.discovered_total, "listed": len(c.described), "probed_by_behavior": len(c.described & c.probed),
                            "listed_never_probed": never_probed[:40]},
            "page_map": c.page_map, "frames": {"total": len(page.frames), "mapped": c.frames_mapped},
            "design_measured": c.design_measured, "stress_run": sorted(c.stress_kinds),
            "actions_taken": c.actions, "pages_visited": sorted(c.urls)[:20], "gaps": gaps,
        }

    async def design_tokens(self) -> dict[str, Any]:
        self.coverage.design_measured = True
        return dict(await self._need().evaluate(js.DESIGN_JS))

    # ------------------------------------------------------------------ acoes
    async def act(self, action: str, target: str = "", value: str = "") -> dict[str, Any]:
        page = self._need()
        if action not in _POINTER_ACTIONS | _KEYBOARD_ACTIONS:
            raise SessionError(f"acao invalida: {action}. Opcoes: {sorted(_POINTER_ACTIONS | _KEYBOARD_ACTIONS)}")
        self._guard(action)
        before = await self._state()
        d0, p0, c0, m0 = len(self.dialogs), len(self.popups), len(self.console_errors), len(self.blocked)
        await self._live_new()  # descarta o que ja foi anunciado antes da acao
        free = not PERSONAS[self.persona].get("no_pointer")
        self._last = {"action": action, "target": target or None, "value": value}
        if action in _POINTER_ACTIONS:
            loc = self._locator(target)
            # A espera paciente vale so para o elemento ficar pronto (mais tempo a cada tentativa). A ACAO roda UMA vez:
            # repetir um clique com efeito (enviar, comprar) por causa de um estouro de tempo seria perigoso.
            await self._wait_ready(loc)
            once = ACTION_TIMEOUT_MS * PATIENCE_FACTOR
            if action == "click":
                await loc.click(timeout=once, no_wait_after=True)  # nao espera a navegacao: _settle espera a pagina assentar
            elif action == "hover":
                await loc.hover(timeout=once)
            elif action == "focus":
                await loc.focus(timeout=once)
            else:
                await loc.select_option(value, timeout=once)
        elif action == "press":
            if target and free:
                await self._locator(target).focus()
            await page.keyboard.press(value)
        elif action == "type":
            if target and free:
                await self._locator(target).click()
            await page.keyboard.type(value, delay=20)
        elif action == "wait":
            await page.wait_for_timeout(max(0, min(int(value or 500), 3000)))
        await self._settle()
        after = await self._state()
        self.coverage.actions += 1
        self.coverage.urls.add(after["url"])
        diff = tree_diff(before["tree"], after["tree"])
        return {
            "action": action, "target": target or None, "value": value if action != "type" else f"({len(value)} caracteres)",
            "persona": self.persona,
            "url_changed": None if before["url"] == after["url"] else {"from": before["url"], "to": after["url"]},
            "focus_before": before["focus"], "focus_after": after["focus"],
            "tree_removed": diff["removed"], "tree_added": diff["added"],
            "announcements": await self._live_new(),
            "js_dialogs": self.dialogs[d0:], "popups_blocked": self.popups[p0:],
            "console_errors": self.console_errors[c0:], "mutations_blocked": self.blocked[m0:],
            "approvals_pending": self.pending_approvals(),
        }

    def _long_poll_age_s(self) -> float:
        """Requisicao em voo por mais que isso, e muito mais do que o site costuma levar, e' tratada como long-poll (nao e' trabalho)."""
        done = sorted(self._req_durations)
        p95 = done[int(0.95 * (len(done) - 1))] if done else 0.0
        return max(LONG_POLL_FLOOR_S, 8 * p95)

    def _working_requests(self) -> int:
        now, limit = time.monotonic(), self._long_poll_age_s()
        return sum(1 for r in self._inflight if now - self._req_t0.get(r, now) < limit)

    async def _settle(self) -> None:
        """Espera adaptativa: navegacao terminou, nao ha requisicao REALMENTE em andamento e o DOM ficou quieto.
        Nao ha relogio fixo: enquanto ha trabalho na rede a espera continua (o tempo que for); so a agitacao continua do DOM sem
        rede (animacao, relogio na tela) e' limitada, e esse limite acompanha a lentidao que o proprio site ja mostrou."""
        page = self._need()
        done = sorted(self._req_durations)
        slow = done[int(0.95 * (len(done) - 1))] if done else 0.0
        dom_cap = max(SETTLE_CAP_MS / 1000, 4 * slow)
        try:
            await page.wait_for_load_state("load", timeout=max(SETTLE_CAP_MS, int(dom_cap * 1000)))
            while True:
                started = time.monotonic()
                await page.evaluate(js.SETTLE_JS, {"quiet": SETTLE_QUIET_MS, "cap": int(dom_cap * 1000) + 1})
                if not self._working_requests():
                    return
                while self._working_requests():  # rede trabalhando: espera terminar, sem teto
                    await asyncio.sleep(0.05)
                if time.monotonic() - started < 0.001:
                    return
        except Exception:  # noqa: BLE001 - pagina navegando/fechando: o estado seguinte mostra o que houver
            return

    async def _activity_signature(self) -> tuple[Any, ...]:
        page = self._need()
        try:
            muts = await asyncio.wait_for(page.evaluate("() => window.__a11yMutations || 0"), 2)
        except Exception:  # noqa: BLE001 - pagina em transicao: conta como agitacao
            muts = -1
        return (page.url, muts, self._req_count)

    async def _wait_ready(self, loc: Any) -> None:
        """Espera um elemento ficar pronto pelo tempo que a pagina continuar PROGREDINDO (rede ou DOM mudando); so desiste quando ela
        para de mudar por um tempo proporcional ao que ja esperou. Nao ha prazo fixo."""
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        start = last_change = time.monotonic()
        sig = await self._activity_signature()
        while True:
            try:
                await loc.wait_for(state="visible", timeout=min(ACTION_TIMEOUT_MS, READY_SLICE_MS))
                return
            except PlaywrightTimeout:
                now = time.monotonic()
                new = await self._activity_signature()
                if new != sig:
                    sig, last_change = new, now
                quiet = now - last_change
                worked = last_change - start
                if quiet > max(QUIET_FLOOR_S, 0.5 * worked):
                    raise

    async def reach(self, target: str, max_tabs: int = 100) -> dict[str, Any]:
        """Quantas vezes o usuario de teclado aperta Tab, do inicio da pagina, para chegar ao alvo."""
        page = self._need()
        loc = self._locator(target)
        if await loc.count() == 0:
            raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
        want = await loc.get_attribute("data-a11y-id")
        await page.evaluate(
            "() => { const b = document.body; b.setAttribute('tabindex', '-1'); b.focus(); b.removeAttribute('tabindex'); }"
        )
        path: list[dict[str, Any]] = []
        first: str | None = None
        previous: str | None = None
        for i in range(1, max(1, min(max_tabs, 300)) + 1):
            await page.keyboard.press("Tab")
            f = await self._focus_probe()
            if f is None:
                return {"reached": False, "tab_presses": i, "reason": "o foco saiu da pagina", "path": path[-15:]}
            sig = f"{f['tag']}|{f['name']}|{f['id']}"
            if first is None:
                first = sig
            elif sig == first:
                return {"reached": False, "tab_presses": i, "reason": "o foco deu a volta sem passar pelo alvo", "path": path[-15:]}
            if sig == previous:
                return {"reached": False, "tab_presses": i, "reason": "o foco parou de mover (fim da pagina) sem passar pelo alvo", "path": path[-15:]}
            previous = sig
            path.append({"stop": i, "tag": f["tag"], "role": f["role"], "name": f["name"], "focus_style": f["focus_style"]})
            if want and f["id"] == want:
                return {"reached": True, "tab_presses": i, "path": path[-15:]}
        return {"reached": False, "tab_presses": max_tabs, "reason": "limite de Tab atingido", "path": path[-15:]}

    async def focus_style(self, target: str) -> dict[str, Any]:
        """Mudanca de estilo que o :focus provoca no elemento, medida pelo Chromium (pseudo-estado forcado, sem
        disparar eventos de foco/blur). Sao FATOS: se aquilo e um indicador de foco visivel e suficiente e do modelo."""
        if PERSONAS[self.persona].get("no_visual"):
            raise SessionError("persona 'screen_reader' nao ve a tela: estilo de foco indisponivel.")
        loc = self._locator(target)
        if await loc.count() == 0:
            raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
        if self.cdp is None:
            return await self._focus_style_by_focusing(target, loc)
        eid = await loc.get_attribute("data-a11y-id")
        cdp = self.cdp
        backend = next((b for b, i in self._ids.items() if i == eid), None)
        if backend is not None:  # pelo id interno do navegador: atravessa iframes e Shadow DOM
            await cdp.send("DOM.getDocument", {"depth": 0})
            node = (await cdp.send("DOM.pushNodesByBackendIdsToFrontend", {"backendNodeIds": [backend]}))["nodeIds"][0]
        else:
            root = (await cdp.send("DOM.getDocument", {"depth": 0}))["root"]["nodeId"]
            node = (await cdp.send("DOM.querySelector", {"nodeId": root, "selector": f'[data-a11y-id="{eid}"]'}))["nodeId"]
        await cdp.send("CSS.enable")

        async def computed() -> dict[str, str]:
            got = await cdp.send("CSS.getComputedStyleForNode", {"nodeId": node})
            return {p["name"]: p["value"] for p in got["computedStyle"]}

        before = await computed()
        try:
            await cdp.send("CSS.forcePseudoState", {"nodeId": node, "forcedPseudoClasses": ["focus", "focus-visible"]})
            after = await computed()
        finally:
            await cdp.send("CSS.forcePseudoState", {"nodeId": node, "forcedPseudoClasses": []})
        changed = {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
        return {
            "target": target, "changed_on_focus": dict(list(changed.items())[:25]), "properties_changed": len(changed),
            "outline_when_focused": " ".join(after.get(k, "") for k in ("outline-style", "outline-width", "outline-color", "outline-offset")),
            "box_shadow_when_focused": after.get("box-shadow"),
            "note": "fatos do :focus; se e visivel e com contraste suficiente para a pessoa e julgamento (veja screenshot)",
        }

    async def _focus_style_by_focusing(self, target: str, loc: Any) -> dict[str, Any]:
        """Sem CDP nao ha pseudo-estado forcado: foca DE VERDADE (dispara focus/blur), mede e desfoca."""
        got: dict[str, Any] = await loc.evaluate(
            """el => { const snap = () => { const cs = getComputedStyle(el); const o = {}; for (const p of cs) o[p] = cs.getPropertyValue(p); return o; };
              const before = snap(); el.focus({preventScroll: true}); const after = snap(); el.blur(); return {before, after}; }"""
        )
        before, after = got["before"], got["after"]
        changed = {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
        return {
            "target": target, "changed_on_focus": dict(list(changed.items())[:25]), "properties_changed": len(changed),
            "outline_when_focused": " ".join(after.get(k, "") for k in ("outline-style", "outline-width", "outline-color", "outline-offset")),
            "box_shadow_when_focused": after.get("box-shadow"),
            "method": f"{self.browser_name}: foco real (dispara eventos de foco/blur; :focus-visible pode diferir de foco por teclado)",
            "note": "fatos do :focus; se e visivel e com contraste suficiente para a pessoa e julgamento (veja screenshot)",
        }

    async def announce(self, target: str) -> dict[str, Any]:
        """O que um leitor de tela receberia para o elemento (arvore de acessibilidade dele)."""
        loc = self._locator(target)
        if await loc.count() == 0:
            raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
        return {"target": target, "accessibility_tree": str(await loc.aria_snapshot())}

    async def screenshot(self, target: str = "", full_page: bool = False) -> bytes:
        if PERSONAS[self.persona].get("no_visual"):
            raise SessionError(
                "persona 'screen_reader' nao ve a tela: captura indisponivel. "
                "Abra outra sessao com persona 'default' para avaliar o visual."
            )
        page = self._need()
        if target:
            data: bytes = await self._locator(target).screenshot(type="jpeg", quality=70)
        else:
            data = await page.screenshot(type="jpeg", quality=70, full_page=full_page)
        return data

    # ---------------------------------------------------------------- estresse
    async def stress(self, kind: str) -> dict[str, Any]:
        page = self._need()
        self.coverage.stress_kinds.add(kind)
        if kind == "reflow_320":
            orig = page.viewport_size or {"width": 1280, "height": 800}
            await page.set_viewport_size({"width": 320, "height": 256})
            try:
                return {"kind": kind, **dict(await page.evaluate(js.REFLOW_JS, 320))}
            finally:
                await page.set_viewport_size(orig)
        if kind == "text_spacing":
            before = await page.evaluate(js.CLIPPED_JS)
            css = (
                "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; }"
                " p { margin-bottom: 2em !important; }"
            )
            handle = await page.add_style_tag(content=css)
            try:
                after = await page.evaluate(js.CLIPPED_JS)
            finally:
                await page.evaluate("(el) => el.remove()", handle)
            seen = {(c["tag"], c["text"]) for c in before}
            return {
                "kind": kind, "clipped_before": len(before),
                "newly_clipped_with_user_spacing": [c for c in after if (c["tag"], c["text"]) not in seen][:15],
            }
        raise SessionError("kind deve ser reflow_320 ou text_spacing")

    async def preview_css(self, target: str, css: str, revert: bool = False) -> dict[str, Any]:
        """Aplica CSS TEMPORARIO (so nesta sessao) para testar uma proposta de design sem tocar no site."""
        loc = self._locator(target)
        if await loc.count() == 0:
            raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
        if revert:
            await loc.evaluate("el => { if (el.dataset.a11yOrigStyle !== undefined) { el.setAttribute('style', el.dataset.a11yOrigStyle); } }")
            return {"reverted": True}
        decls: dict[str, str] = {}
        for part in css.split(";"):
            if not part.strip():
                continue
            prop, sep, val = part.partition(":")
            prop, val = prop.strip().lower(), val.strip()
            if not sep or not _SAFE_CSS_PROP.match(prop) or re.search(r"url\(|@|<|expression|javascript", val, re.IGNORECASE):
                raise SessionError(f"declaracao CSS nao permitida: {part.strip()[:60]!r} (sem url(), @ ou HTML)")
            decls[prop] = val
        if not decls:
            raise SessionError("css vazio")
        result: dict[str, Any] = await loc.evaluate(
            """(el, decls) => {
              if (el.dataset.a11yOrigStyle === undefined) el.dataset.a11yOrigStyle = el.getAttribute('style') || '';
              const get = () => { const cs = getComputedStyle(el); const o = {}; for (const p of Object.keys(decls)) o[p] = cs.getPropertyValue(p); return o; };
              const before = get();
              for (const [p, v] of Object.entries(decls)) el.style.setProperty(p, v, 'important');
              const r = el.getBoundingClientRect();
              return {before, after: get(), size_after: {w: Math.round(r.width), h: Math.round(r.height)}};
            }""",
            decls,
        )
        return {"applied": decls, **result, "note": "temporario: vale so nesta sessao; use revert=true para desfazer"}


SESSION = Session()
