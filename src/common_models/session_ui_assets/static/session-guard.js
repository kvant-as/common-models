/* Shared idle-session guard (client side).
 *
 * Included on every page for an authenticated user via {{ cm_session_guard() }}.
 * It mirrors the server rule: the session stays alive on page navigations and
 * ordinary server calls, but NOT on `/api` data loads and NOT on pure
 * client-side activity such as scrolling. There are deliberately no
 * scroll/click/keydown listeners here.
 *
 * A page load re-reads the real `expires_at` from the server. A non-ignored
 * fetch/XHR slides the local countdown to match what the server just did.
 * When the countdown runs out the guard asks the server once more; if the
 * session really is gone it sends the browser to the logout URL.
 */
(function () {
    var script = document.currentScript;
    var INFO_URL = (script && script.dataset.infoUrl) || "/_session/session-info";
    var LOGOUT_URL = (script && script.dataset.logoutUrl) || "/logout";

    var IGNORE = ["/api", "/_session", "/_forms"];
    try {
        if (script && script.dataset.ignorePrefixes) {
            IGNORE = JSON.parse(script.dataset.ignorePrefixes);
        }
    } catch (e) { /* keep default */ }

    var timeoutMs = null;
    var expiresAt = null;
    var lastSlide = 0;
    var checking = false;
    var stopped = false;

    function pathOf(url) {
        try {
            return new URL(url, window.location.origin).pathname;
        } catch (e) {
            return typeof url === "string" ? url : "";
        }
    }

    function isIgnored(url) {
        var p = pathOf(url);
        for (var i = 0; i < IGNORE.length; i++) {
            if (p.indexOf(IGNORE[i]) === 0) return true;
        }
        return false;
    }

    function fmt(ms) {
        var total = Math.max(0, Math.floor(ms / 1000));
        return String(Math.floor(total / 60)).padStart(2, "0") + ":" +
               String(total % 60).padStart(2, "0");
    }

    function paint() {
        if (expiresAt === null) return;
        var remaining = Math.max(0, expiresAt - Date.now());
        var valueEl = document.getElementById("cmSessionTimerValue");
        var fillEl = document.getElementById("cmSessionTimerFill");
        var card = document.getElementById("cmSessionCard");
        if (valueEl) valueEl.textContent = fmt(remaining);
        var ratio = timeoutMs ? Math.min(1, Math.max(0, remaining / timeoutMs)) : 1;
        if (fillEl) fillEl.style.width = ratio * 100 + "%";
        if (card) {
            card.classList.toggle("cm-session--warning", ratio <= 0.2 && ratio > 0.05);
            card.classList.toggle("cm-session--danger", ratio <= 0.05);
        }
    }

    function slide() {
        if (!timeoutMs || stopped) return;
        var now = Date.now();
        if (now - lastSlide < 2000) return;   // debounce request bursts
        lastSlide = now;
        expiresAt = now + timeoutMs;
        paint();
    }

    function goLogout() {
        if (stopped) return;
        stopped = true;
        window.location.href = LOGOUT_URL;
    }

    function verifyThenMaybeLogout() {
        if (checking || stopped) return;
        checking = true;
        fetch(INFO_URL, { credentials: "same-origin", redirect: "manual",
                          headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) {
                if (!r || !r.ok) { goLogout(); return null; }
                return r.json();
            })
            .then(function (d) {
                checking = false;
                if (!d || !d.success) return;
                var offset = new Date(d.server_time).getTime() - Date.now();
                var exp = new Date(d.expires_at).getTime() - offset;
                if (exp <= Date.now()) { goLogout(); return; }
                expiresAt = exp;                       // server still considers us active
                if (d.timeout_minutes) timeoutMs = d.timeout_minutes * 60 * 1000;
                paint();
            })
            .catch(function () { checking = false; goLogout(); });
    }

    function tick() {
        if (expiresAt === null || stopped) return;
        if (Date.now() >= expiresAt) {
            verifyThenMaybeLogout();
            return;
        }
        paint();
    }

    function hookRequests() {
        var origFetch = window.fetch;
        if (origFetch) {
            window.fetch = function (input, init) {
                var url = typeof input === "string" ? input : (input && input.url);
                var p = origFetch.apply(this, arguments);
                if (!isIgnored(url)) {
                    p.then(function () { slide(); }, function () {});
                }
                return p;
            };
        }
        var XHR = window.XMLHttpRequest;
        if (XHR) {
            var origOpen = XHR.prototype.open;
            XHR.prototype.open = function (method, url) {
                this.__cmIgnored = isIgnored(url);
                return origOpen.apply(this, arguments);
            };
            var origSend = XHR.prototype.send;
            XHR.prototype.send = function () {
                var self = this;
                this.addEventListener("loadend", function () {
                    if (!self.__cmIgnored) slide();
                });
                return origSend.apply(this, arguments);
            };
        }
    }

    function start(timeoutMinutes, initialExpiresAt) {
        timeoutMs = (timeoutMinutes || 60) * 60 * 1000;
        expiresAt = initialExpiresAt;
        hookRequests();
        paint();
        setInterval(tick, 1000);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var card = document.getElementById("cmSessionCard");
        if (card && card.dataset.expiresAt && card.dataset.serverTime && card.dataset.timeoutMinutes) {
            var offset = new Date(card.dataset.serverTime).getTime() - Date.now();
            start(parseInt(card.dataset.timeoutMinutes, 10),
                  new Date(card.dataset.expiresAt).getTime() - offset);
            return;
        }
        fetch(INFO_URL, { credentials: "same-origin",
                          headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d || !d.success) return;
                var offset = new Date(d.server_time).getTime() - Date.now();
                start(d.timeout_minutes, new Date(d.expires_at).getTime() - offset);
            })
            .catch(function () {});
    });
})();
