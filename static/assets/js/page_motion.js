(function () {
    if (window.finloPageMotionInitialized) return;
    window.finloPageMotionInitialized = true;
    function initialize() {
        // Page navigation is intentionally immediate. Loading indicators and
        // animated reveals must never delay or obscure usable CRM content.
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
    else initialize();
})();
