/*!
 * ConnectLink UI feedback layer  ·  static/js/cl-ui.js
 * ---------------------------------------------------------------------------
 * ONE implementation of "the system is talking to the server" feedback, so a
 * control behaves the same everywhere instead of depending on whether the page
 * author remembered to hand-roll a spinner.
 *
 * Before this file the pages contained ~169 hand-written copies of
 *     btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>Saving...';
 * and plenty of committing buttons with no feedback at all.
 *
 * What it does, with NO per-button wiring:
 *   · form submit (classic navigation)  -> spinner on the submit button
 *   · fetch POST/PUT/PATCH/DELETE       -> spinner on the control that started it
 *   · XMLHttpRequest POST/... (jQuery)  -> same
 *   · a slim crimson progress bar at the top for any commit in flight
 *   · blocks an accidental double submit (while one is still running, or inside a
 *     short burst window) without ever swallowing a deliberate retry
 *   · alert() routes to the toast the page already has (or a built-in one made from
 *     the house .toast classes) so the 392 call sites stop blocking the UI, and a
 *     message can never be swallowed even if a page's own toast is broken
 *
 * Design rules it follows
 *   · never changes the button's width (the label is made transparent, the
 *     spinner is absolutely positioned over it) so no layout shift
 *   · restores EXACTLY what it changed (it will not re-enable a button that the
 *     page had deliberately disabled, e.g. the permission-gated Update buttons)
 *   · a watchdog always clears the state, so nothing can spin forever
 *   · GET requests are ignored by the progress bar (dashboards poll, and a bar
 *     that flashes every few seconds reads as a glitch)
 *   · opt out with data-cl-busy-off on the control, a parent, or the <form>
 *   · it can never throw into page code: every entry point is guarded
 *
 * Manual use (for the hand-rolled spots, migrate at your leisure):
 *   clBusy(el); clDone(el); clBusyWhile(el, somePromise);
 *   clNotify(msg, 'success' | 'error' | 'warning' | 'info');
 */
(function () {
    'use strict';

    if (window.__clUiLoaded) { return; }
    window.__clUiLoaded = true;

    var BUSY = 'cl-busy';
    var SPIN = 'cl-spin';
    var VERB = /^(POST|PUT|PATCH|DELETE)$/i;
    var WATCHDOG_AJAX_MS = 20000;   // a hung request must not leave a dead button
    var WATCHDOG_FORM_MS = 8000;    // submit that never navigates (e.g. file download)
    var CLICK_FRESH_MS = 2500;      // how long a click counts as "what started this"
    var DOUBLE_MS = 600;            // burst window that counts as a double click
    var FORM_SPIN_DELAY_MS = 250;   // classic submits only: wait to see if AJAX took over
    var BAR_DELAY_MS = 180;         // don't flash the bar for instant requests

    var CONTROL_SEL = 'button, input[type="submit"], input[type="button"], a, [role="button"], [data-cl-busy]';
    var book = new WeakMap();       // element -> record
    var lastClick = { el: null, at: 0 };
    var commitSeq = 0;              // bumped every time a tracked commit starts

    /* ---------------------------------------------------------------- helpers */

    function el(v) { return !!v && v.nodeType === 1; }

    function isBusy(node) {
        return el(node) && node.classList.contains(BUSY);
    }

    function blocked(node) {
        if (!el(node)) { return false; }
        if (node.hasAttribute('data-cl-busy-off') || node.classList.contains('cl-no-busy')) { return true; }
        return !!(node.closest && node.closest('[data-cl-busy-off], .cl-no-busy'));
    }

    function control(el0) {
        if (!el(el0)) { return null; }
        if (el0.matches && el0.matches(CONTROL_SEL)) { return el0; }
        return (el0.closest ? el0.closest(CONTROL_SEL) : null);
    }

    /* 52 hand-rolled sites already put their own spinner inside the button, often
       with a label worth keeping ("Saving...", "Generating PDF..."). When that
       spinner is genuinely showing we leave the page's markup completely alone and
       only add the click-blocking, so the layer ADAPTS instead of overwriting.

       getClientRects() is what makes this safe: the templates are full of
       declarative spinners parked with bootstrap's d-none, and those must NOT count
       as feedback - otherwise a button would have none at all. */
    function hasOwnSpinner(node) {
        try {
            var found = node.querySelectorAll('.spinner-border, .spinner-grow, [class*="spinner"]');
            for (var i = 0; i < found.length; i++) {
                if (found[i].getClientRects().length) { return true; }
            }
        } catch (e) { /* never let detection break the page */ }
        return false;
    }

    function sameOrigin(url) {
        try {
            if (!url) { return true; }
            if (/^(data|blob|javascript):/i.test(url)) { return false; }
            return new URL(url, location.href).origin === location.origin;
        } catch (e) {
            return true;
        }
    }

    /* ------------------------------------------------------------ busy state */

    function busy(node, watchdogMs) {
        if (!el(node) || blocked(node)) { return null; }
        var rec = book.get(node);
        if (!rec) {
            rec = { n: 0, timer: null, spin: null, color: '', position: false };
            book.set(node, rec);
        }
        rec.n += 1;
        if (rec.n === 1) {
            try {
                apply(node, rec);
            } catch (e) {
                rec.n = 0;
                return null;
            }
        }
        clearTimeout(rec.timer);
        rec.timer = setTimeout(function () { done(node); }, watchdogMs || WATCHDOG_AJAX_MS);
        return node;
    }

    function apply(node, rec) {
        var cs = window.getComputedStyle(node);
        var isInput = node.tagName === 'INPUT';

        node.classList.add(BUSY);
        node.setAttribute('aria-busy', 'true');

        /* Re-clicks are blocked by `pointer-events: none` in .cl-busy (see
           design-system.css). The `disabled` attribute is deliberately NEVER used:
           a disabled control is not a "successful control", so disabling a submit
           button mid-post can drop its own name/value from the request - and
           re-enabling it on finish would undo buttons the page keeps disabled on
           purpose (e.g. the permission-gated Update buttons in adminpage). */
        if (node.tagName === 'A') { node.setAttribute('aria-disabled', 'true'); }

        /* The page is already showing its own spinner here - keep its markup and
           its label, just block the re-click. */
        rec.own = isInput ? false : hasOwnSpinner(node);
        if (rec.own) {
            node.classList.add(BUSY + '-own');
            /* done() writes style.color back, so capture it even though we are not
               touching it - otherwise finishing would wipe a colour the page set. */
            rec.color = node.style.color || '';
            return;
        }

        /* The spinner is absolutely positioned, so the label (a bare text node in
           most buttons) has to be hidden by making the colour transparent. Its old
           value is kept in a custom property so the spinner can use it. */
        rec.color = node.style.color || '';
        if (cs.position === 'static') {
            node.style.position = 'relative';
            rec.position = true;
        }
        node.style.setProperty('--cl-spin-color', cs.color);
        if (!isInput && node.tagName !== 'SELECT' && node.tagName !== 'TEXTAREA') {
            node.style.color = 'transparent';
            rec.spin = document.createElement('span');
            rec.spin.className = SPIN;
            rec.spin.setAttribute('aria-hidden', 'true');
            node.appendChild(rec.spin);
        }
    }

    function done(node) {
        var rec = el(node) && book.get(node);
        if (!rec) { return; }
        rec.n = 0;
        clearTimeout(rec.timer);
        rec.timer = null;
        try {
            node.classList.remove(BUSY, BUSY + '-own');
            node.removeAttribute('aria-busy');
            node.removeAttribute('aria-disabled');
            rec.own = false;
            if (rec.spin && rec.spin.parentNode) { rec.spin.parentNode.removeChild(rec.spin); }
            rec.spin = null;
            node.style.color = rec.color || '';
            node.style.removeProperty('--cl-spin-color');
            if (rec.position) { node.style.position = ''; }
            rec.position = false;
        } catch (e) { /* never let cosmetics break the page */ }
    }

    /* --------------------------------------------------------- progress bar */

    var pending = 0, barTimer = null, bar = null;

    function barShow() {
        if (!bar) {
            bar = document.createElement('div');
            bar.className = 'cl-progress';
            bar.setAttribute('aria-hidden', 'true');
            (document.body || document.documentElement).appendChild(bar);
        }
        bar.classList.add('cl-progress-on');
    }

    function barHide() {
        if (bar) { bar.classList.remove('cl-progress-on'); }
    }

    function requestStart() {
        pending += 1;
        if (pending === 1) {
            clearTimeout(barTimer);
            barTimer = setTimeout(barShow, BAR_DELAY_MS);
        }
    }

    function requestEnd() {
        pending = Math.max(0, pending - 1);
        if (pending === 0) {
            clearTimeout(barTimer);
            barHide();
        }
    }

    /* ------------------------------------------- who started this request? */

    document.addEventListener('click', function (e) {
        var c = control(e.target);
        if (c) { lastClick.el = c; lastClick.at = Date.now(); }
    }, true);

    function initiator() {
        var focused = control(document.activeElement);
        if (focused && !blocked(focused)) { return focused; }
        if (lastClick.el && (Date.now() - lastClick.at) < CLICK_FRESH_MS && !blocked(lastClick.el)) {
            return lastClick.el;
        }
        return null;
    }

    /* ------------------------------------------------------------ fetch hook */

    var nativeFetch = window.fetch;
    if (typeof nativeFetch === 'function') {
        window.fetch = function (input, init) {
            var url = '';
            var method = 'GET';
            try {
                url = typeof input === 'string' ? input : (input && input.url) || '';
                method = (init && init.method) || (input && input.method) || 'GET';
            } catch (e) { /* ignore */ }

            var commit = VERB.test(method) && sameOrigin(url);
            var target = commit ? initiator() : null;
            if (commit) { commitSeq += 1; }
            if (target) { busy(target); }
            if (commit) { requestStart(); }

            var p;
            try {
                p = nativeFetch.apply(this, arguments);
            } catch (err) {
                if (target) { done(target); }
                if (commit) { requestEnd(); }
                throw err;
            }

            var finish = function () {
                if (target) { done(target); }
                if (commit) { requestEnd(); }
            };
            if (p && typeof p.then === 'function') { p.then(finish, finish); } else { finish(); }
            return p;
        };
    }

    /* -------------------------------------------------------------- XHR hook
       jQuery's $.ajax (used all over the older pages) goes through this. */

    if (window.XMLHttpRequest && XMLHttpRequest.prototype) {
        var nativeOpen = XMLHttpRequest.prototype.open;
        var nativeSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function (method, url) {
            try {
                this.__clMethod = method;
                this.__clUrl = url;
            } catch (e) { /* ignore */ }
            return nativeOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function () {
            var self = this;
            var commit = VERB.test(self.__clMethod || '') && sameOrigin(self.__clUrl);
            var target = commit ? initiator() : null;
            if (commit) { commitSeq += 1; }
            if (target) { busy(target); }
            if (commit) { requestStart(); }

            if (commit) {
                var finish = function () {
                    if (target) { done(target); }
                    requestEnd();
                };
                /* loadend fires once for success, error, abort AND timeout */
                self.addEventListener('loadend', finish, { once: true });
            }
            return nativeSend.apply(this, arguments);
        };
    }

    /* ------------------------------------------------------- form submit hook
       Classic (navigating) submits. The button is NOT disabled here, so its own
       name/value still reaches the server. */

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || form.nodeType !== 1 || blocked(form)) { return; }

        var submitter = e.submitter || null;
        if (!submitter) {
            submitter = form.querySelector('button[type="submit"]:not([disabled]), input[type="submit"]:not([disabled])');
        }
        submitter = control(submitter);

        /* Accidental double submit. The PRIMARY rule is "the first post is still
           running" - that also covers Enter-key submits, which have no click.
           DOUBLE_MS is only a secondary net for a request that finished almost
           instantly, so it stays short: a deliberate retry a moment later is
           never silently swallowed. Only a REAL user click is ever blocked -
           a programmatic submit (form.submit(), jQuery .submit()) has
           isTrusted === false and always goes through. */
        var now = Date.now();
        if (e.isTrusted && (isBusy(submitter) || form.__clPending ||
            (form.__clLastSubmit && (now - form.__clLastSubmit) < DOUBLE_MS))) {
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        if (e.isTrusted) { form.__clLastSubmit = now; }
        form.__clPending = true;

        /* Most forms in this app are intercepted by the page's own handler, which
           then does fetch/XHR - and that path already shows the spinner and
           restores it the moment the request settles. So a classic submit spinner
           is armed on a short delay and is only applied to a submit that is really
           going to navigate:
             · e.defaultPrevented -> the page owns it (AJAX, or a validation rule
               that refused the submit) so the hook already covers it, or nothing
               should be shown at all
             · commitSeq moved     -> a tracked request started in the meantime
           Without this, an AJAX form would sit spinning for the whole watchdog
           after a 200ms save, and a validation failure would spin too. */
        var seqAtSubmit = commitSeq;
        clearTimeout(form.__clSpinTimer);
        form.__clSpinTimer = setTimeout(function () {
            if (e.defaultPrevented || commitSeq !== seqAtSubmit) { form.__clPending = false; return; }
            if (!submitter || blocked(submitter) || isBusy(submitter)) {
                form.__clPending = false;
                return;
            }
            busy(submitter, WATCHDOG_FORM_MS);
        }, FORM_SPIN_DELAY_MS);

        /* Nothing else will tell us this classic submit is over (the page is
           navigating, or a download is streaming), so release the guard on the
           same watchdog the spinner uses. */
        clearTimeout(form.__clPendingTimer);
        form.__clPendingTimer = setTimeout(function () { form.__clPending = false; }, WATCHDOG_FORM_MS);
    }, true);

    /* ------------------------------------------------------------------ notify
       One notification path for the whole system.

       The pages already own a house toast - design-system.css defines
       .toast-container / .toast / .toast-success|error|warning|info, and each page
       exposes a showToast() (adminpage, whatsapp_app, base_modern, mainindex,
       pos-system, users_dashboard) or toast() (finance, procurement). alert() is
       the one thing that was never migrated: 392 call sites, and on pages with no
       toast at all (hr_dashboard, test1, profile...) there is no option but the
       browser modal.

       So instead of editing 392 sites, we shim window.alert and DELEGATE to the
       toast the page already has, falling back to a built-in one built from the
       same house classes. Every page keeps its own look, but they all behave the
       same and nothing blocks the UI for "saved successfully".

       The safety net that matters: if a page toast is broken or silently no-ops
       (finance.html's toast() has no null guard on its container), the message is
       still shown by the fallback - an error must never be swallowed.

       confirm() is deliberately NOT shimmed: it has to return a boolean
       synchronously, which no toast can do, and rewriting its 73 call sites is not
       worth the risk. window.clNativeAlert is there if blocking is ever needed. */

    var TOAST_SEL = '.toast, .pc-toast, .toast-notify, .toast-msg';
    var inNotify = false;
    var lastNote = { at: 0, message: '', type: 'info' };
    var SUCCESS_LEAD = '\u2705\u2714\u2713';
    var ERROR_LEAD = '\u274c\u2716\u26d4';
    var WARN_LEAD = '\u26a0\u2757\u2755';
    var INFO_LEAD = '\u2139';

    var GLYPH = {
        success: '<svg viewBox="0 0 16 16" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0Zm3.85 6.36-4.5 4.5a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 1 1 1.06-1.06l1.47 1.47 3.97-3.97a.75.75 0 1 1 1.06 1.06Z"/></svg>',
        error: '<svg viewBox="0 0 16 16" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0Zm1 12H7v-1.5h2V12Zm0-3H7V4h2v5Z"/></svg>',
        warning: '<svg viewBox="0 0 16 16" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M8.98 1.32a1.13 1.13 0 0 0-1.96 0L.28 13.02A1.13 1.13 0 0 0 1.26 14.7h13.48a1.13 1.13 0 0 0 .98-1.68L8.98 1.32ZM8 6a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 6Zm0 7.25a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8Z"/></svg>',
        info: '<svg viewBox="0 0 16 16" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0Zm.75 4.25a.9.9 0 1 1-1.8 0 .9.9 0 0 1 1.8 0ZM7.25 7h1.5v5h-1.5V7Z"/></svg>'
    };

    /* "❌ Error: ..." -> error, "✅ saved" -> success. The prefixes are already in
       the messages, so the mapping is reliable; keywords cover the rest. */
    function severityOf(msg) {
        var c = msg.charAt(0);
        if (SUCCESS_LEAD.indexOf(c) !== -1) { return 'success'; }
        if (ERROR_LEAD.indexOf(c) !== -1) { return 'error'; }
        if (WARN_LEAD.indexOf(c) !== -1) { return 'warning'; }
        if (INFO_LEAD.indexOf(c) !== -1) { return 'info'; }
        if (/(error|failed|failure|cannot|can't|unable|invalid|denied|not found|unavailable|network)/i.test(msg)) { return 'error'; }
        if (/(success|successfully|saved|updated|sent|added|created|deleted|removed|completed|complete|done|approved|authorised|authorized|resent|restored)/i.test(msg)) { return 'success'; }
        if (/(^please|^select|^no |^nothing|must|required|blank|not selected|enter a|provide a)/i.test(msg)) { return 'warning'; }
        return 'info';
    }

    /* Drop ONE leading decorative emoji (and its variation selector) - the toast
       draws its own icon, so keeping it would duplicate it. Never rewrites the
       rest of the message, and never empties a message that is only an emoji. */
    function tidy(msg) {
        var m = /^[\s\u200b]*([\u2705\u2714\u2713\u274c\u2716\u26d4\u26a0\u2757\u2755\u2139])\uFE0F?\s*([\s\S]*)$/.exec(msg);
        if (!m) { return msg; }
        return m[2].trim() ? m[2] : msg;
    }

    function builtinToast(message, type) {
        var wrap = document.querySelector('.toast-container');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'toast-container';
            (document.body || document.documentElement).appendChild(wrap);
        }
        var el = document.createElement('div');
        /* `show` matters: bootstrap.min.css ships .toast:not(.show){display:none} */
        el.className = 'toast show toast-' + type;
        el.setAttribute('role', 'status');
        el.innerHTML = '<span class="toast-icon">' + (GLYPH[type] || GLYPH.info) + '</span>' +
                       '<span class="toast-message"></span>' +
                       '<button class="toast-close" type="button" aria-label="Dismiss">&times;</button>';
        /* textContent, not innerHTML: alert() text is a message, never markup */
        el.querySelector('.toast-message').textContent = message;
        var kill = function () {
            if (!el.parentElement) { return; }
            el.classList.add('cl-toast-out');
            setTimeout(function () { el.remove(); }, 220);
        };
        el.querySelector('.toast-close').addEventListener('click', kill);
        wrap.appendChild(el);
        /* a loop of alerts must not turn the corner into a wall of toasts */
        while (wrap.children.length > 4) { wrap.removeChild(wrap.firstElementChild); }
        var life = type === 'error' ? 10000 : (type === 'warning' ? 8000 : (type === 'success' ? 4500 : 6000));
        var timer = setTimeout(kill, life);
        el.addEventListener('mouseenter', function () { clearTimeout(timer); });
        el.addEventListener('mouseleave', function () { timer = setTimeout(kill, 1500); });
        return el;
    }

    function notify(message, type) {
        var text = (message === null || message === undefined) ? '' : String(message);
        if (!text.trim()) { return null; }
        var sev = (type === 'danger' || type === 'failure') ? 'error' : (type || severityOf(text));
        text = tidy(text);
        lastNote = { at: Date.now(), message: text, type: sev };
        if (inNotify) { return null; }
        inNotify = true;
        try {
            var before = document.querySelectorAll(TOAST_SEL).length;
            var impl = window.clToastImpl ||
                (typeof window.showToast === 'function' ? window.showToast : null) ||
                (typeof window.toast === 'function' ? window.toast : null);
            if (impl) {
                try { impl(text, sev); } catch (e) { impl = null; }
                if (impl && document.querySelectorAll(TOAST_SEL).length > before) { return null; }
            }
            return builtinToast(text, sev);
        } catch (e) {
            return null;
        } finally {
            inNotify = false;
        }
    }

    /* A toast is worthless if the very next line reloads the page - and 6 alert()
       sites do exactly that ("Administrator added!" then location.reload()). So a
       toast still fresh when the page goes away is replayed on the next load. */
    function stashNote() {
        try {
            if (!lastNote.at || (Date.now() - lastNote.at) > 1500) { return; }
            sessionStorage.setItem('cl-pending-toast', JSON.stringify(lastNote));
            lastNote.at = 0;
        } catch (e) { /* private mode / no storage - just skip the replay */ }
    }
    window.addEventListener('pagehide', stashNote);
    window.addEventListener('beforeunload', stashNote);
    try {
        var stashed = sessionStorage.getItem('cl-pending-toast');
        if (stashed) {
            sessionStorage.removeItem('cl-pending-toast');
            var note = JSON.parse(stashed);
            if (note && note.message && (Date.now() - note.at) < 8000) {
                setTimeout(function () {
                    if (note.type) { notify(note.message, note.type); }
                    else { notify(note.message, severityOf(note.message)); }
                    lastNote.at = 0;         // never re-stash a replayed toast
                }, 120);
            }
        }
    } catch (e) { /* ignore */ }

    var nativeAlert = (typeof window.alert === 'function') ? window.alert : null;

    window.clNotify = function (message, type) { return notify(message, type); };
    window.clNativeAlert = function () {
        return nativeAlert ? nativeAlert.apply(window, arguments) : undefined;
    };
    window.clAlertShimOff = false;

    if (nativeAlert) {
        window.alert = function (message) {
            /* inNotify: a page toast that falls back to alert() itself must not
               recurse into us. clAlertShimOff: an escape hatch for anything that
               genuinely needs a blocking modal. */
            if (window.clAlertShimOff || inNotify) { return window.clNativeAlert.apply(window, arguments); }
            try {
                notify(message);
                return undefined;
            } catch (e) {
                return window.clNativeAlert.apply(window, arguments);
            }
        };
    }

    /* --------------------------------------------------------------- public API */

    window.clBusy = function (node) { return busy(control(node) || node); };
    window.clDone = function (node) { done(control(node) || node); };
    window.clBusyWhile = function (node, promise) {
        var t = control(node) || node;
        busy(t);
        var finish = function () { done(t); };
        if (promise && typeof promise.then === 'function') { promise.then(finish, finish); } else { finish(); }
        return promise;
    };
})();
