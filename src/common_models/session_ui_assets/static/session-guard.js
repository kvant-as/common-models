/* Shared idle-session guard.
 *
 * Included on every page for an authenticated user via {{ cm_session_guard() }}.
 * Runs a client-side countdown to the idle timeout; real user interaction
 * (click / keypress / touch / typing / scroll) resets it, a full page load
 * re-reads a fresh baseline. When it reaches zero the browser is sent to the
 * logout URL, so accounts are signed out on expiry even on pages that are not
 * behind @session_required. Server-side @session_required enforces the same
 * cutoff independently.
 *
 * Background XHR/fetch (notification polls etc.) is deliberately NOT treated
 * as activity — otherwise the timeout would never fire.
 */
(function () {
    var script = document.currentScript;
    var INFO_URL = (script && script.dataset.infoUrl) || "/_session/session-info";
    var LOGOUT_URL = (script && script.dataset.logoutUrl) || "/logout";

    var expiresAt = null;
    var timeoutMs = null;
    var redirecting = false;
    var lastExtend = 0;

    function fmt(ms) {
        var total = Math.max(0, Math.floor(ms / 1000));
        var m = Math.floor(total / 60);
        var s = total % 60;
        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
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

    function tick() {
        if (expiresAt === null || redirecting) return;
        if (Date.now() >= expiresAt) {
            redirecting = true;
            window.location.href = LOGOUT_URL;
            return;
        }
        paint();
    }

    function extend() {
        if (!timeoutMs) return;
        var now = Date.now();
        if (now - lastExtend < 1000) return;
        lastExtend = now;
        expiresAt = now + timeoutMs;
        paint();
    }

    function start(timeoutMinutes, initialExpiresAt) {
        timeoutMs = timeoutMinutes * 60 * 1000;
        expiresAt = initialExpiresAt;
        paint();
        ["click", "keydown", "touchstart", "input"].forEach(function (evt) {
            document.addEventListener(evt, extend, { passive: true });
        });
        window.addEventListener("scroll", extend, { passive: true });
        setInterval(tick, 1000);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var card = document.getElementById("cmSessionCard");
        if (card && card.dataset.expiresAt && card.dataset.serverTime && card.dataset.timeoutMinutes) {
            var tMin = parseInt(card.dataset.timeoutMinutes, 10) || 60;
            var clockOffset = new Date(card.dataset.serverTime).getTime() - Date.now();
            start(tMin, new Date(card.dataset.expiresAt).getTime() - clockOffset);
            return;
        }
        fetch(INFO_URL, { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d || !d.success) return;
                var clockOffset = new Date(d.server_time).getTime() - Date.now();
                start(d.timeout_minutes || 60, new Date(d.expires_at).getTime() - clockOffset);
            })
            .catch(function () {});
    });
})();
