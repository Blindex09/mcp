import { Injectable } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { LiveAnnouncer } from '@angular/cdk/a11y';
import { filter } from 'rxjs';

/**
 * Angular SPA accessibility service (Angular 21, 2026).
 *
 * On every client-side route change:
 *  1. Move focus to the new page <h1> (tabindex="-1") so screen reader
 *     users land at the new content — like a full page reload would.
 *  2. Announce the new page title via the CDK LiveAnnouncer.
 *
 * Without this, Angular's client-side routing silently strips screen
 * readers of context because no page reload occurs.
 */
@Injectable({ providedIn: 'root' })
export class A11yService {
  constructor(
    private router: Router,
    private titleService: Title,
    private liveAnnouncer: LiveAnnouncer,
  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe(() => this.onRouteChange());
  }

  private onRouteChange(): void {
    // Announce the new page title (polite live region)
    const title = this.titleService.getTitle();
    this.liveAnnouncer.announce(`Navigated to ${title}`);

    // Move focus to the page heading after the new view renders
    setTimeout(() => {
      const heading = document.querySelector('h1');
      if (heading) {
        heading.setAttribute('tabindex', '-1');
        (heading as HTMLElement).focus();
      }
    }, 100);
  }

  /** Announce a dynamic status message (search results, form success). */
  announce(message: string, politeness: 'polite' | 'assertive' = 'polite'): void {
    this.liveAnnouncer.announce(message, politeness);
  }
}

/* ------------------------------------------------------------------ */
/* Angular CDK a11y utilities                                          */
/* ------------------------------------------------------------------ */
/*
 * LiveAnnouncer (above) — wraps an aria-live region and speaks messages.
 *
 * FocusTrap directive (cdkTrapFocus) — use on modal dialogs:
 *
 *   <div role="dialog" aria-modal="true" cdkTrapFocus>
 *     <h2 id="dlg-title">Edit profile</h2>
 *     ...
 *     <button (click)="close()">Close</button>
 *   </div>
 *
 * It traps Tab/Shift+Tab inside the dialog and auto-creates focusable
 * sentinels so focus never escapes to the background.
 *
 * Dynamic ARIA binding requires the attr. prefix (Angular 21):
 *   <button [attr.aria-label]="dynamicLabel">...</button>
 * (Plain [aria-label] fails for ARIA attributes — they are not Angular
 *  property bindings.)
 */