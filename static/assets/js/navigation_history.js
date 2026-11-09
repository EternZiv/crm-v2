(function () {
    if (window._finloNavigationHistoryInitialized || !window.htmx) return;
    window._finloNavigationHistoryInitialized = true;

    // Use HTMX's native client-side history cache for instant page restoration
    htmx.config.historyCacheSize = 30;
    htmx.config.refreshOnHistoryMiss = false;

    function currentPath() {
        return window.location.pathname + window.location.search;
    }

    function setActiveSectionFromPath(path) {
        try {
            const sectionId = new URL(path, window.location.href).searchParams.get("section");
            if (!sectionId) return;

            const activeLink = document.getElementById(sectionId);
            if (!activeLink || !activeLink.matches("nav a.nav-link")) return;

            document.querySelectorAll("nav a.nav-link").forEach((link) => {
                link.classList.remove("bg-primary-600", "hover:bg-primary-800");
            });
            activeLink.classList.add("bg-primary-600", "hover:bg-primary-800");
            window.localStorage.setItem("activeNavLinkId", sectionId);
            window.localStorage.setItem("currentActiveSection", sectionId);
            window.localStorage.setItem("lastActiveSection", sectionId);

            if (sectionId === "home") {
                window.localStorage.setItem("sidebarClicked", "false");
                window.localStorage.removeItem("activeSidebarLinkId");
                window.localStorage.removeItem("activeSidebarLinkId_home");
            }
        } catch (e) {}
    }

    // Update active section on navigation
    document.addEventListener("htmx:afterSwap", function (event) {
        setActiveSectionFromPath(window.location.href);
    });

    document.addEventListener("htmx:historyRestore", function (event) {
        setActiveSectionFromPath(event.detail?.path || currentPath());
    });

    document.body?.addEventListener("htmx:beforeRequest", function (event) {
        const path = event.detail.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path)) {
            window.sessionStorage?.removeItem("htmx-history-cache");
            window.localStorage?.removeItem("htmx-history-cache");
        }
    });
})();
