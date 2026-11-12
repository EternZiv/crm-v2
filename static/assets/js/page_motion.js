(function () {
    if (window.finloPageMotionInitialized) return;
    window.finloPageMotionInitialized = true;
    function initialize() {
        // One welcome screen per tab visit, including the login-to-CRM redirect.
        let welcomed = false;
        try { welcomed = sessionStorage.getItem('finloWelcomeShown') === 'true'; } catch (_) {}
        if (!welcomed) {
            try { sessionStorage.setItem('finloWelcomeShown', 'true'); } catch (_) {}
            const welcome = document.createElement('div');
            welcome.className = 'finlo-welcome';
            welcome.setAttribute('role', 'status');
            welcome.setAttribute('aria-live', 'polite');
            const label = document.createElement('p');
            label.textContent = 'Welcome to Finlo CRM';
            const spinner = document.createElement('span');
            spinner.className = 'finlo-motion-spinner';
            spinner.setAttribute('aria-hidden', 'true');
            welcome.append(spinner, label);
            document.body.appendChild(welcome);
            // Presentation only: assets and requests continue during the welcome.
            setTimeout(() => welcome.remove(), 5000);
        }
        const indicator = document.createElement('div');
        indicator.className = 'finlo-request-motion';
        indicator.setAttribute('aria-hidden', 'true');
        document.body.appendChild(indicator);
        const pending = new Set();
        function update() { indicator.classList.toggle('is-loading', pending.size > 0); }
        document.addEventListener('htmx:beforeRequest', event => {
            if (event.detail && event.detail.xhr) pending.add(event.detail.xhr);
            update();
        });
        ['htmx:afterRequest', 'htmx:sendError', 'htmx:timeout', 'htmx:sendAbort'].forEach(name => {
            document.addEventListener(name, event => {
                if (event.detail) pending.delete(event.detail.xhr);
                update();
            });
        });
        function reveal(target) {
            if (!target || !target.animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
            target.animate([{ opacity: 0.7 }, { opacity: 1 }], { duration: 160 });
        }
        document.addEventListener('htmx:afterSwap', event => reveal(event.detail && event.detail.target));
        document.addEventListener('finlo:viewRestored', () => reveal(document.getElementById('mainContent')));
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
    else initialize();
})();
