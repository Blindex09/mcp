"""Ferramentas de teste como usuario: olhos (dossie, observacao, design) e maos (acoes).

O modelo do cliente e quem julga; estas ferramentas so agem e devolvem fatos observados.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context, Image

from llm import NO_MODEL_HELP, ask_model, backend_status

from .agent import run_agent
from .provisioning import status_of_all
from .session import PERSONAS, SESSION, SessionError


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)


def _error(e: Exception) -> str:
    return _json({"error": f"{type(e).__name__}: {e}"})


async def _run(coro: Any) -> str:
    """Executa uma operacao da sessao com serializacao e erro amigavel."""
    try:
        async with SESSION.lock:
            return _json(await coro)
    except SessionError as e:
        return _json({"error": str(e)})
    except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve o erro ao cliente
        return _error(e)


def register_ux(mcp: Any) -> None:
    """Registra as ferramentas de sessao/UX no servidor FastMCP."""

    @mcp.tool()
    async def a11y_open(
        url: str = "", html: str = "", persona: str = "default", color_scheme: str = "", browser: str = "chromium",
        allow_mutations: str = "auto",
    ) -> str:
        """Open a persistent browser session to test a page LIKE A USER (one session at a time;
        opening a new one closes the previous). Provide EITHER url (http/https, localhost ok) OR html.
        persona: default | keyboard | screen_reader | low_vision | mobile_touch | reduced_motion | forced_colors.
        The persona is ENFORCED: keyboard and screen_reader have no mouse (click/hover/focus/select are refused),
        screen_reader also cannot take screenshots, low_vision is a 320 px reflow viewport, mobile_touch is a phone.
        browser: chromium (default, most precise: browser-computed roles/names/clickable via CDP) | firefox | webkit
        (installed automatically on first use; less precise discovery, and the result lists the limits).
        allow_mutations: auto (default) | ask | allow | block. Approval is on or off, never a flat refusal: auto = local dev sites
        (localhost, 127.0.0.1, *.test) do everything (approval off); any other site HOLDS POST/PUT/PATCH/DELETE and form submissions and
        shows what they would change until the person approves with a11y_approve (approval on). allow = do everything; block = strict,
        never send them.
        color_scheme: light | dark (optional). Do not type real credentials into tested pages; use test accounts.
        Sessions close after 10 minutes idle."""
        try:
            async with SESSION.lock:
                return _json(await SESSION.open(url or None, html or None, persona, color_scheme or None, browser, allow_mutations))
        except SessionError as e:
            return _json({"error": str(e), "personas": {k: v["about"] for k, v in PERSONAS.items()}})
        except Exception as e:  # noqa: BLE001
            return _error(e)

    @mcp.tool()
    async def a11y_approve(decision: str, ids: str = "") -> str:
        """Answer the person's approval for requests the session is HOLDING (they would change data on a real site): each pending item shows
        method, URL and the NAMES of the fields it would send (never their values). decision: allow (the listed ids, or all pending if
        ids is empty) | deny | allow_all (approval off for the rest of the session). ids: comma-separated ids like a1,a2. Returns what was
        decided and the effect on the page. Only call this with the person's actual answer, never on your own."""
        try:
            async with SESSION.lock:
                return _json(await SESSION.decide(decision, [i.strip() for i in ids.split(",") if i.strip()] or None))
        except SessionError as e:
            return _json({"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return _error(e)

    @mcp.tool()
    async def a11y_close() -> str:
        """Close the browser session. If an autonomous test (a11y_walkthrough / a11y_review) is running, this
        interrupts it: the run stops at the next step and still returns the report of what it did so far."""
        try:
            if SESSION.lock.locked():
                SESSION.stop_requested = True
                return _json({"closed": False, "cancel_requested": True, "note": "o teste autonomo termina no proximo passo e devolve o relatorio parcial"})
            async with SESSION.lock:
                return _json({"closed": await SESSION.close()})
        except Exception as e:  # noqa: BLE001
            return _error(e)

    @mcp.tool()
    async def a11y_dossier(scope: str = "", max_elements: int = 60) -> str:
        """FACTS about every interactive / widget-like element on the current page, to decide WHAT EACH ONE
        REALLY IS in this site's context (text field vs combobox vs listbox vs menu vs disclosure vs tabs...).
        Per element: id (use it as target elsewhere), tag/type/role attribute, name sources, visible text,
        states (expanded/haspopup/checked/...), relations (aria-controls, datalist/select options, popup item
        count/kinds/links), editable, nearest landmark/heading/form, focusable, position, computed typography/colors.
        It does NOT classify: read the facts, then probe behavior with a11y_act and judge using
        a11y_get_reference "component-identity-guide". scope: optional CSS selector to limit the inventory.
        Re-run after navigation (ids are attributes added to the page)."""
        return await _run(SESSION.dossier(scope, max_elements))

    @mcp.tool()
    async def a11y_page_map(scope: str = "") -> str:
        """FACTS about ALL the content of the page (not just interactive elements), including open Shadow DOM and each
        iframe: heading outline and level jumps, landmarks, images (alt, size, in links), links (same text to different
        destinations), forms and fields (labels, autocomplete, errors), tables, lists, media (captions/tracks), iframes
        (titles), live regions, reading order versus visual order, and CSS :hover rules that reveal content (menus opened
        only by hover). No verdicts: YOU judge (does the alt make sense? does the hierarchy match the visual? is the
        reading order right?). scope: optional CSS selector for the main document. Use with a11y_dossier for interactive parts."""
        return await _run(SESSION.page_map(scope))

    @mcp.tool()
    async def a11y_coverage() -> str:
        """What this session has and has NOT covered, as facts: interactive elements discovered/listed/probed by behavior,
        whether the page map, design measurement and stress tests ran, iframes mapped, actions taken, pages visited, and a
        list of gaps. Include it (and the gaps) in any report so a green result is never mistaken for full coverage."""
        try:
            return _json(SESSION.coverage_report())
        except SessionError as e:
            return _json({"error": str(e)})

    @mcp.tool()
    async def a11y_observe() -> str:
        """Current state as a user would perceive it: URL, title, focused element, the accessibility tree
        (what a screen reader gets), recent live-region announcements, JS dialogs dismissed, popups blocked."""
        return await _run(SESSION.observe())

    @mcp.tool()
    async def a11y_act(action: str, target: str = "", value: str = "") -> str:
        """Do something a user does and get the EFFECT report: focus before/after, accessibility-tree lines that
        appeared/disappeared (states like expanded change here), what live regions announced, URL change,
        dialogs/popups/console errors. action: click | hover | focus | select | press | type | wait.
        target: an id from a11y_dossier (e.g. e12) or 'css:<selector>'. value: key for press (Tab, Enter, Escape,
        ArrowDown, Shift+Tab, ...), text for type, option for select, milliseconds for wait.
        Keyboard/screen_reader personas only have press/type/wait: reach things with Tab like a real user.
        Use it to check that a widget BEHAVES like the role it claims (does Escape close it? do arrows move?)."""
        return await _run(SESSION.act(action, target, value))

    @mcp.tool()
    async def a11y_reach(target: str, max_tabs: int = 100) -> str:
        """How many Tab presses a keyboard user needs, from the top of the page, to reach the target
        (id from a11y_dossier), with the focus path. Reports if the target is unreachable or the focus loops."""
        return await _run(SESSION.reach(target, max_tabs))

    @mcp.tool()
    async def a11y_focus_style(target: str) -> str:
        """FACTS about what :focus changes on an element (measured by Chromium by forcing the focus state, no
        events fired): every computed property that differs (outline, box-shadow, border, background, color...).
        Whether that is a visible, sufficient focus indicator is your judgment (compare with a11y_screenshot).
        Refused for the screen_reader persona."""
        return await _run(SESSION.focus_style(target))

    @mcp.tool()
    async def a11y_announce(target: str) -> str:
        """What a screen reader would be given for one element: its accessibility-tree entry (role, accessible
        name, states). Compare with the visible text to find missing, wrong or duplicated names."""
        return await _run(SESSION.announce(target))

    @mcp.tool()
    async def a11y_screenshot(target: str = "", full_page: bool = False) -> Any:
        """Screenshot (JPEG) of the page or one element (id from a11y_dossier, or css:<selector>), to judge
        layout, typography and spacing visually. Refused for the screen_reader persona (it cannot see)."""
        try:
            async with SESSION.lock:
                return Image(data=await SESSION.screenshot(target, full_page), format="jpeg")
        except SessionError as e:
            return _json({"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return _error(e)

    @mcp.tool()
    async def a11y_design_tokens() -> str:
        """The site's REAL design language, measured: type styles in use (family/size/weight/line-height/
        letter-spacing with counts and examples), font families, sizes, weights, text/background colors,
        spacing values, radii, shadows, CSS variables on :root, paragraph widths. Use it to critique and propose
        design changes INSIDE the site's own scale (see a11y_get_reference "design-language-review")."""
        return await _run(SESSION.design_tokens())

    @mcp.tool()
    async def a11y_preview_css(target: str, css: str = "", revert: bool = False) -> str:
        """Try a design change TEMPORARILY (this session only; the site is untouched): apply CSS declarations
        (e.g. 'font-size: 18px; line-height: 1.6') to an element and get before/after computed values and its new
        size. Follow with a11y_screenshot to compare. revert=true restores the element. No url(), @rules or HTML."""
        return await _run(SESSION.preview_css(target, css, revert))

    @mcp.tool()
    async def a11y_stress(kind: str) -> str:
        """Stress the page and report facts. kind: reflow_320 (WCAG 1.4.10: horizontal scroll and overflowing
        elements at 320 px width) | text_spacing (WCAG 1.4.12: text clipped after applying user text-spacing)."""
        return await _run(SESSION.stress(kind))


    async def _autonomous(
        ctx: Context, mode: str, goal: str, url: str, html: str, persona: str, max_steps: int, vision: bool, browser: str,
        allow_mutations: str = "auto",
    ) -> str:  # type: ignore[type-arg]
        async def ask(prompt: str, images: list[bytes] | None, max_tokens: int) -> str | None:
            return await ask_model(ctx, prompt, max_tokens, images)

        async def progress(step: int, total: int, message: str) -> None:
            try:
                await ctx.report_progress(step, total, message)
            except Exception:  # noqa: BLE001, S110 - cliente sem progresso: segue
                pass

        try:
            async with SESSION.lock:
                result = await run_agent(
                    session=SESSION, ask=ask, mode=mode, goal=goal, url=url or None, html=html or None,
                    persona=persona, max_steps=max_steps, vision=vision, progress=progress, browser=browser, allow_mutations=allow_mutations,
                )
        except SessionError as e:
            return _json({"error": str(e), "personas": {k: v["about"] for k, v in PERSONAS.items()}})
        except Exception as e:  # noqa: BLE001
            return _error(e)
        if result["stopped_by"] == "model_unavailable" and result["facts"]["steps_used"] == 0:
            return _json({"error": NO_MODEL_HELP, "how_to_do_it_manually": "use a11y_open + a11y_dossier + a11y_act com o seu proprio modelo"})
        return _json(result)

    @mcp.tool()
    async def a11y_walkthrough(
        ctx: Context, task: str, url: str = "", html: str = "", persona: str = "default", max_steps: int = 25, vision: bool = True,  # type: ignore[type-arg]
        browser: str = "chromium", allow_mutations: str = "auto",
    ) -> str:
        """AUTONOMOUS user test: a model plays a real person with the given persona trying to accomplish a task on the
        page (url http/https or html), step by step, seeing the screen (screenshot) and the accessibility tree, and
        writes a plain-language report of what happened, where the person struggled, and what to fix (keeping the
        design), including what could NOT be verified. Needs the server's own model (A11Y_MCP_MODEL + provider key,
        see a11y_status) or a client that offers sampling. The harness enforces the persona (keyboard/screen_reader
        have no mouse), a step cap (max 60), a time budget and stops repeated identical actions.
        task: the person's goal in plain words, e.g. "sign up for the newsletter" or "find the return policy"."""
        return await _autonomous(ctx, "task", task, url, html, persona, max_steps, vision, browser, allow_mutations)

    @mcp.tool()
    async def a11y_review(
        ctx: Context, focus: str = "componentes e design", url: str = "", html: str = "", persona: str = "default", max_steps: int = 30, vision: bool = True,  # type: ignore[type-arg]
        browser: str = "chromium", allow_mutations: str = "auto",
    ) -> str:
        """AUTONOMOUS UX review: a model explores the page, PROBES each important interactive component to learn what it
        really is for people in this site's context (text field vs combobox vs list vs menu vs navigation vs accordion...),
        compares with what it exposes today, and reviews typography/spacing against the site's own design language.
        Returns a plain-language report with evidence, fixes that keep the design, and what could not be verified.
        Same requirements and enforced limits as a11y_walkthrough. focus: what to review, in your own words."""
        return await _autonomous(ctx, "review", focus, url, html, persona, max_steps, vision, browser, allow_mutations)

    @mcp.tool()
    async def a11y_status() -> str:
        """Readiness check: is the browser (Playwright/Chromium) installed or being installed automatically, and is a
        model configured for the autonomous tools (a11y_find, a11y_walkthrough, a11y_review)? Never shows secrets."""
        return _json({
            "browsers": status_of_all(),
            "model": backend_status(),
            "note": "Sem modelo configurado, as ferramentas autonomas ficam indisponiveis; as demais (dossie, acoes, medicao) funcionam.",
        })
