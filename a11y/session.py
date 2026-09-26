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
import re
import time
from collections import Counter
from typing import Any

from . import page_scripts as js
from .audit import _launch, validate_url
from .provisioning import check_browser_name, provisioner_for

IDLE_TIMEOUT_S = 600
ACTION_TIMEOUT_MS = 10_000
SETTLE_QUIET_MS = 200  # silencio do DOM que caracteriza "assentou"
SETTLE_CAP_MS = 3_000  # teto de seguranca da espera adaptativa
_ID_RE = re.compile(r"e\d+")
_SAFE_CSS_PROP = re.compile(r"^[a-z-]+$")
_ALLOWED_SCHEMES = ("http:", "https:", "data:", "blob:", "about:")
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
        self.stop_requested = False  # pedido de cancelamento de um teste autonomo em andamento
        self._inflight: set[Any] = set()  # requisicoes em andamento (sinal de que a pagina ainda esta reagindo)
        self._ids: dict[int, str] = {}  # backendNodeId -> id estavel (eN) entre chamadas do dossie
        self.last_used = time.monotonic()
        self.lock = asyncio.Lock()
        self.dialogs: list[str] = []
        self.popups: list[str] = []
        self.console_errors: list[str] = []
        self._live_seen = 0
        self._console_seen = 0
        self._watchdog: asyncio.Task[None] | None = None

    # ----------------------------------------------------------- ciclo de vida
    async def open(
        self, url: str | None, html: str | None, persona: str = "default", color_scheme: str | None = None,
        browser: str = "chromium",
    ) -> dict[str, Any]:
        if bool(url) == bool(html):
            raise SessionError("informe exatamente um entre url e html")
        if persona not in PERSONAS:
            raise SessionError(f"persona invalida: {persona}. Opcoes: {sorted(PERSONAS)}")
        if color_scheme not in (None, "light", "dark"):
            raise SessionError("color_scheme deve ser light ou dark")
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
            await self.context.route("**/*", self._route)
            await self.context.add_init_script(js.LIVE_OBSERVER_JS)
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
        self.dialogs, self.popups, self.console_errors = [], [], []
        self._live_seen = self._console_seen = 0
        self.last_used = time.monotonic()
        self._watchdog = asyncio.create_task(self._idle_watchdog())
        return {
            "opened": self.page.url, "persona": persona, "browser": browser, "about": cfg["about"],
            "title": await self.page.title(), "limits": notes,
        }

    async def close(self) -> bool:
        was_open = self.page is not None
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
        self._inflight = set()
        return was_open

    async def _idle_watchdog(self) -> None:
        while self.page is not None:
            await asyncio.sleep(30)
            if time.monotonic() - self.last_used > IDLE_TIMEOUT_S:
                await self.close()
                return

    # ------------------------------------------------- guardas de seguranca
    @staticmethod
    async def _route(route: Any) -> None:
        if route.request.url.lower().startswith(_ALLOWED_SCHEMES):
            await route.continue_()
        else:
            await route.abort()

    async def _on_dialog(self, dialog: Any) -> None:
        self.dialogs.append(f"{dialog.type}: {dialog.message[:200]}")
        await dialog.dismiss()

    def _on_popup(self, page: Any) -> None:
        if self.page is not None and page is not self.page:
            self.popups.append(page.url or "(sem url)")
            asyncio.ensure_future(page.close())

    def _request_started(self, request: Any) -> None:
        self._inflight.add(request)

    def _request_done(self, request: Any) -> None:
        self._inflight.discard(request)

    def _on_console(self, msg: Any) -> None:
        if msg.type == "error":
            self.console_errors.append(msg.text[:200])

    def _need(self) -> Any:
        if self.page is None:
            raise SessionError("nenhuma sessao aberta: chame a11y_open primeiro")
        self.last_used = time.monotonic()
        return self.page

    def _locator(self, target: str) -> Any:
        page = self._need()
        t = (target or "").strip()
        if _ID_RE.fullmatch(t):
            loc = page.locator(f'[data-a11y-id="{t}"]')
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
            "focus": await page.evaluate(js.FOCUS_JS),
            "tree": await self._tree_lines(),
        }

    async def observe(self) -> dict[str, Any]:
        st = await self._state()
        return {
            "url": st["url"], "title": st["title"], "focus": st["focus"], "persona": self.persona,
            "accessibility_tree": st["tree"], "recent_announcements": await self._live_new(),
            "js_dialogs": self.dialogs[-5:], "popups_blocked": self.popups[-5:],
            "console_errors": self.console_errors[-5:],
        }

    async def _discover(self, limit: int = 600) -> tuple[list[dict[str, Any]], int]:
        """O NAVEGADOR aponta o que e focavel (arvore de acessibilidade) ou clicavel (DOMSnapshot.isClickable,
        que inclui quem so tem addEventListener). Nenhuma lista de tags nem heuristica de cursor."""
        cdp = self.cdp
        if cdp is None:
            return await self._discover_dom(limit)
        await cdp.send("DOM.getDocument", {"depth": 0})
        snap = await cdp.send("DOMSnapshot.captureSnapshot", {"computedStyles": [], "includeDOMRects": True})
        doc, strings = snap["documents"][0], snap["strings"]
        nodes = doc["nodes"]
        clickable = set(nodes.get("isClickable", {}).get("index", []))
        layout = doc["layout"]
        rendered = {i for i, b in zip(layout["nodeIndex"], layout["bounds"], strict=False) if b[2] > 0 and b[3] > 0}
        ax_by: dict[int, dict[str, Any]] = {}
        for n in (await cdp.send("Accessibility.getFullAXTree"))["nodes"]:
            bid = n.get("backendDOMNodeId")
            if bid is None:
                continue
            props = {p["name"]: p["value"].get("value") for p in n.get("properties", [])}
            ax_by[bid] = {
                "role": (n.get("role") or {}).get("value"), "name": (n.get("name") or {}).get("value") or "",
                "description": (n.get("description") or {}).get("value") or None,
                "ignored": bool(n.get("ignored")), "properties": props,
            }
        found: list[dict[str, Any]] = []
        for idx, bid in enumerate(nodes["backendNodeId"]):
            if nodes["nodeType"][idx] != 1 or idx not in rendered or strings[nodes["nodeName"][idx]] in ("HTML", "BODY"):
                continue
            ax = ax_by.get(bid)
            focusable = bool(ax and not ax["ignored"] and ax["properties"].get("focusable"))
            is_clickable = idx in clickable
            if focusable or is_clickable:
                found.append({"backend": bid, "focusable": focusable, "clickable": is_clickable, "ax": ax})
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
        return found, total

    async def _discover_dom(self, limit: int) -> tuple[list[dict[str, Any]], int]:
        """Firefox/WebKit (sem CDP): focavel = tabIndex calculado pelo navegador; cursor:pointer e um sinal mais fraco."""
        page = self._need()
        res = await page.evaluate(js.DISCOVER_JS, limit)
        found = [
            {"id": f["id"], "focusable": f["focusable"], "clickable": None, "pointer_cursor": f["pointer_cursor"], "ax": None}
            for f in res["found"]
        ]
        return found, int(res["total"])

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

    async def dossier(self, scope: str = "", max_elements: int = 60) -> dict[str, Any]:
        """FATOS dos elementos que o navegador aponta como focaveis/clicaveis, com papel e nome COMPUTADOS por ele."""
        page = self._need()
        found, total = await self._discover()
        found = [f for f in found if "id" in f]
        result = dict(await page.evaluate(
            js.DOSSIER_JS, {"ids": [f["id"] for f in found], "scope": scope or None, "max": max(1, min(max_elements, 200))}
        ))
        if "error" in result:
            return result
        by_id = {f["id"]: f for f in found}
        for e in result["elements"]:
            f = by_id[e["id"]]
            e["focusable"], e["clickable"] = f["focusable"], f["clickable"]
            if self.cdp is None:  # sem CDP: papel/nome do aria snapshot do Playwright, elemento a elemento
                e["pointer_cursor"] = f.get("pointer_cursor")
                snap = await page.locator(f'[data-a11y-id="{e["id"]}"]').first.aria_snapshot()
                f["ax"] = self.parse_snapshot_head(str(snap))
            e["computed"] = f["ax"]  # papel, nome, descricao e propriedades como o navegador os expoe (None = fora da arvore)
        result["discovered_total"] = total
        result["discovery_truncated"] = total > len(found)
        result["browser"] = self.browser_name
        result["note"] = "iframes nao sao percorridos; ids sao atributos data-a11y-id colocados na pagina"
        if self.cdp is None:
            result["limits"] = ["sem CDP: clickable desconhecido (so cursor:pointer), papel/nome pelo aria snapshot do Playwright"]
        return result

    async def design_tokens(self) -> dict[str, Any]:
        return dict(await self._need().evaluate(js.DESIGN_JS))

    # ------------------------------------------------------------------ acoes
    async def act(self, action: str, target: str = "", value: str = "") -> dict[str, Any]:
        page = self._need()
        if action not in _POINTER_ACTIONS | _KEYBOARD_ACTIONS:
            raise SessionError(f"acao invalida: {action}. Opcoes: {sorted(_POINTER_ACTIONS | _KEYBOARD_ACTIONS)}")
        self._guard(action)
        before = await self._state()
        d0, p0, c0 = len(self.dialogs), len(self.popups), len(self.console_errors)
        await self._live_new()  # descarta o que ja foi anunciado antes da acao
        free = not PERSONAS[self.persona].get("no_pointer")
        if action == "click":
            await self._locator(target).click()
        elif action == "hover":
            await self._locator(target).hover()
        elif action == "focus":
            await self._locator(target).focus()
        elif action == "select":
            await self._locator(target).select_option(value)
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
        diff = tree_diff(before["tree"], after["tree"])
        return {
            "action": action, "target": target or None, "value": value if action != "type" else f"({len(value)} caracteres)",
            "persona": self.persona,
            "url_changed": None if before["url"] == after["url"] else {"from": before["url"], "to": after["url"]},
            "focus_before": before["focus"], "focus_after": after["focus"],
            "tree_removed": diff["removed"], "tree_added": diff["added"],
            "announcements": await self._live_new(),
            "js_dialogs": self.dialogs[d0:], "popups_blocked": self.popups[p0:],
            "console_errors": self.console_errors[c0:],
        }

    async def _settle(self) -> None:
        """Espera adaptativa: navegacao terminou, nao ha requisicoes em voo e o DOM ficou quieto.
        Nao ha sleep fixo; SETTLE_CAP_MS e' so o teto de seguranca para a acao inteira."""
        page = self._need()
        deadline = time.monotonic() + SETTLE_CAP_MS / 1000
        try:
            await page.wait_for_load_state("load", timeout=SETTLE_CAP_MS)
            while True:
                left = max(0.0, deadline - time.monotonic())
                await page.evaluate(js.SETTLE_JS, {"quiet": SETTLE_QUIET_MS, "cap": int(left * 1000) + 1})
                if not self._inflight or time.monotonic() >= deadline:
                    return
                while self._inflight and time.monotonic() < deadline:  # rede ainda ocupada: espera esvaziar
                    await asyncio.sleep(0.05)
        except Exception:  # noqa: BLE001 - pagina navegando/fechando: o estado seguinte mostra o que houver
            return

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
        for i in range(1, max(1, min(max_tabs, 300)) + 1):
            await page.keyboard.press("Tab")
            f = await page.evaluate(js.FOCUS_JS)
            if f is None:
                return {"reached": False, "tab_presses": i, "reason": "o foco saiu da pagina", "path": path[-15:]}
            sig = f"{f['tag']}|{f['name']}|{f['id']}"
            if first is None:
                first = sig
            elif sig == first:
                return {"reached": False, "tab_presses": i, "reason": "o foco deu a volta sem passar pelo alvo", "path": path[-15:]}
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
