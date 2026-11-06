(function () {
    'use strict';

    if (window.__clSystemUpdateNoticeLoaded) { return; }
    window.__clSystemUpdateNoticeLoaded = true;

    var CHECK_INTERVAL_MS = 30000;
    var ENDPOINT = '/api/system-updates';
    var DEFAULT_MESSAGE = 'A teammate made changes. Keep working; this page will not reload automatically. Refresh after saving your work.';
    var initialScript = document.currentScript
        || document.getElementById('cl-system-update-notice-script');
    var initialCursorValue = initialScript && initialScript.getAttribute
        ? initialScript.getAttribute('data-initial-cursor')
        : null;
    var parsedInitialCursor = initialCursorValue === null || initialCursorValue === ''
        ? null
        : Number(initialCursorValue);
    var latestId = Number.isSafeInteger(parsedInitialCursor) && parsedInitialCursor >= 0
        ? parsedInitialCursor
        : null;
    var requestInFlight = false;
    var pollingStopped = false;
    var errorReported = false;
    var notice;
    var message;
    var pollTimer;

    function installStyles() {
        if (document.getElementById('cl-system-update-styles')) { return; }

        var style = document.createElement('style');
        style.id = 'cl-system-update-styles';
        style.textContent = [
            '.cl-system-update-notice{box-sizing:border-box;position:fixed;right:12px;bottom:12px;z-index:1040;',
            'width:min(440px,calc(100vw - 24px));padding:14px 16px;background:#fff;color:#152333;',
            'border:1px solid #d5e0e8;border-left:4px solid #1877c9;border-radius:12px;',
            'box-shadow:0 10px 32px rgba(15,35,52,.2);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;}',
            '.cl-system-update-notice[hidden]{display:none!important;}',
            '.cl-system-update-copy{margin:0 0 12px;}',
            '.cl-system-update-title{display:block;margin:0 0 3px;font-size:15px;font-weight:700;}',
            '.cl-system-update-message{margin:0;color:#465766;}',
            '.cl-system-update-actions{display:flex;justify-content:flex-end;gap:8px;}',
            '.cl-system-update-actions button{min-height:36px;padding:7px 12px;border:1px solid transparent;',
            'border-radius:8px;font:inherit;font-weight:600;cursor:pointer;}',
            '.cl-system-update-refresh{background:#1769aa;color:#fff;}',
            '.cl-system-update-refresh:hover{background:#10588f;}',
            '.cl-system-update-later{background:transparent;color:#34495a;border-color:#c8d3dc!important;}',
            '.cl-system-update-notice button:focus-visible{outline:3px solid #79b8f3;outline-offset:2px;}',
            'body.dark-theme .cl-system-update-notice{background:#1a1f2e;color:#e5e7eb;border-color:#3a4659;}',
            'body.dark-theme .cl-system-update-message{color:#c3ccd8;}',
            'body.dark-theme .cl-system-update-later{color:#e5e7eb;border-color:#586579!important;}',
            '@media(max-width:480px){.cl-system-update-notice{right:12px;bottom:12px;width:calc(100vw - 24px);}}'
        ].join('');
        document.head.appendChild(style);
    }

    function showNotice() {
        if (notice) { notice.hidden = false; }
    }

    function hideNotice() {
        if (notice) { notice.hidden = true; }
    }

    function createNotice() {
        installStyles();

        notice = document.createElement('section');
        notice.id = 'cl-system-update-notice';
        notice.className = 'cl-system-update-notice';
        notice.setAttribute('role', 'status');
        notice.setAttribute('aria-live', 'polite');
        notice.setAttribute('aria-atomic', 'true');
        notice.setAttribute('aria-label', 'System updates available');
        notice.hidden = true;

        var copy = document.createElement('div');
        copy.className = 'cl-system-update-copy';

        var title = document.createElement('strong');
        title.className = 'cl-system-update-title';
        title.textContent = 'Updates available';

        message = document.createElement('p');
        message.className = 'cl-system-update-message';
        message.textContent = DEFAULT_MESSAGE;

        var actions = document.createElement('div');
        actions.className = 'cl-system-update-actions';

        var refresh = document.createElement('button');
        refresh.type = 'button';
        refresh.className = 'cl-system-update-refresh';
        refresh.textContent = 'Refresh when ready';
        refresh.addEventListener('click', function () {
            if (document.querySelector('.cl-busy')) {
                message.textContent = 'A save is still in progress. Wait for it to finish; this page will not reload automatically.';
                window.setTimeout(function () {
                    if (message && !notice.hidden) {
                        message.textContent = DEFAULT_MESSAGE;
                    }
                }, 4000);
                return;
            }
            window.location.reload();
        });

        var later = document.createElement('button');
        later.type = 'button';
        later.className = 'cl-system-update-later';
        later.textContent = 'Later';
        later.addEventListener('click', hideNotice);

        copy.appendChild(title);
        copy.appendChild(message);
        actions.appendChild(later);
        actions.appendChild(refresh);
        notice.appendChild(copy);
        notice.appendChild(actions);
        document.body.appendChild(notice);
    }

    function stopPolling() {
        pollingStopped = true;
        if (pollTimer) {
            window.clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function checkForUpdates() {
        if (pollingStopped || requestInFlight || document.hidden) { return; }

        requestInFlight = true;
        var url = ENDPOINT;
        if (latestId !== null) {
            url += '?after=' + encodeURIComponent(latestId);
        }

        Promise.resolve().then(function () {
            return window.fetch(url, {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: { 'Accept': 'application/json' }
            });
        }).then(function (response) {
            if (response.status === 401 || response.status === 403) {
                stopPolling();
                return null;
            }
            if (!response.ok) {
                throw new Error('Update check failed with HTTP ' + response.status);
            }
            return response.json();
        }).then(function (payload) {
            if (payload === null) { return; }
            if (!payload || payload.success !== true
                    || typeof payload.changed !== 'boolean') {
                throw new Error('Update check returned an invalid response');
            }

            var nextId = Number(payload.latest_id);
            if (!Number.isSafeInteger(nextId) || nextId < 0) {
                throw new Error('Update check returned an invalid cursor');
            }

            if (latestId !== null && nextId < latestId) {
                throw new Error('Update check returned an older cursor');
            }

            latestId = nextId;
            if (payload.changed) { showNotice(); }
            errorReported = false;
        }).catch(function (error) {
            if (!errorReported) {
                console.warn('Could not check for system updates.', error);
                errorReported = true;
            }
        }).then(function () {
            requestInFlight = false;
        });
    }

    createNotice();
    checkForUpdates();
    pollTimer = window.setInterval(checkForUpdates, CHECK_INTERVAL_MS);

    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) { checkForUpdates(); }
    });
    window.addEventListener('online', checkForUpdates);
})();
