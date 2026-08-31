/* Password-strength meter.
 *
 * <div data-cm-pwmeter="#password" data-min="5"></div>
 *
 * Builds a 4-segment bar + label under the referenced password input,
 * updates on every keystroke, and sets the input's `minlength` so the form
 * will not submit a too-short password (still validate on the server too).
 */
(function () {
    var LEVELS = [
        { text: "Слишком короткий", color: "#c0392b" }, // 0 — below minLength
        { text: "Слабый", color: "#c0392b" },
        { text: "Средний", color: "#c98a00" },
        { text: "Хороший", color: "#2f8f46" },
        { text: "Надёжный", color: "#1c7a3e" }
    ];

    function strength(value, min) {
        if (value.length < min) return 0;
        var pts = 0;
        if (value.length >= min) pts++;
        if (value.length >= 8) pts++;
        if (value.length >= 12) pts++;
        if (/[a-zа-яё]/.test(value) && /[A-ZА-ЯЁ]/.test(value)) pts++;
        if (/\d/.test(value)) pts++;
        if (/[^0-9A-Za-zА-Яа-яЁё]/.test(value)) pts++;
        return Math.max(1, Math.min(4, Math.ceil(pts * 4 / 6)));
    }

    function build(host) {
        var sel = host.getAttribute("data-cm-pwmeter");
        var input = sel && document.querySelector(sel);
        if (!input) return;

        var min = parseInt(host.getAttribute("data-min") || "5", 10);
        input.setAttribute("minlength", String(min));

        host.classList.add("cm-pwmeter");
        var track = document.createElement("div");
        track.className = "cm-pwmeter__track";
        var segs = [];
        for (var i = 0; i < 4; i++) {
            var seg = document.createElement("div");
            seg.className = "cm-pwmeter__seg";
            track.appendChild(seg);
            segs.push(seg);
        }
        var label = document.createElement("div");
        label.className = "cm-pwmeter__label";
        host.appendChild(track);
        host.appendChild(label);

        function render() {
            var v = input.value || "";
            if (!v) {
                segs.forEach(function (s) { s.classList.remove("is-on"); });
                label.innerHTML = "";
                host.style.removeProperty("--cm-pw-color");
                return;
            }
            var lvl = strength(v, min);
            var meta = LEVELS[lvl];
            host.style.setProperty("--cm-pw-color", meta.color);
            var on = lvl === 0 ? 1 : lvl;
            segs.forEach(function (s, idx) { s.classList.toggle("is-on", idx < on); });
            label.innerHTML = "Надёжность пароля: <b>" + meta.text + "</b>";
        }

        input.addEventListener("input", render);
        render();
    }

    /* ----- confirm-password match indicator ----------------------------- *
     * <div data-cm-pwmatch data-password="#pw1" data-confirm="#pw2"
     *      data-submit=".auth-form button[type=submit]" data-min="5"></div>
     * Shows "Пароли совпадают / не совпадают" in the same style and disables
     * the submit button while the confirmation does not match.
     */
    function buildMatch(host) {
        var pw = document.querySelector(host.getAttribute("data-password"));
        var confirm = document.querySelector(host.getAttribute("data-confirm"));
        if (!pw || !confirm) return;

        var min = parseInt(host.getAttribute("data-min") || "5", 10);
        var submit = host.getAttribute("data-submit")
            ? document.querySelector(host.getAttribute("data-submit"))
            : null;

        host.classList.add("cm-pwmatch");
        var bar = document.createElement("div");
        bar.className = "cm-pwmatch__bar";
        var label = document.createElement("div");
        label.className = "cm-pwmatch__label";
        host.appendChild(bar);
        host.appendChild(label);

        function render() {
            var a = pw.value || "";
            var b = confirm.value || "";

            if (!b) {
                host.classList.remove("is-ok", "is-bad");
                label.textContent = "";
                if (submit) submit.disabled = false;
                return;
            }
            var ok = a === b && a.length >= min;
            host.classList.toggle("is-ok", ok);
            host.classList.toggle("is-bad", !ok);
            label.textContent = ok
                ? "Пароли совпадают"
                : (a.length < min ? "Пароль слишком короткий" : "Пароли не совпадают");
            if (submit) submit.disabled = !ok;
        }

        pw.addEventListener("input", render);
        confirm.addEventListener("input", render);
        render();
    }

    document.addEventListener("DOMContentLoaded", function () {
        var meters = document.querySelectorAll("[data-cm-pwmeter]");
        for (var i = 0; i < meters.length; i++) build(meters[i]);
        var matches = document.querySelectorAll("[data-cm-pwmatch]");
        for (var j = 0; j < matches.length; j++) buildMatch(matches[j]);
    });
})();
