(function () {
    if (window._finloNavigationHistoryInitialized || !window.htmx) return;
    window._finloNavigationHistoryInitialized = true;

    htmx.config.historyCacheSize = 20;

    function currentPath() {
        return window.location.pathname + window.location.search;
    }

    function setActiveSectionFromPath(path) {
        const sectionId = new URL(path, window.location.href).searchParams.get(
            "section",
        );
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
    }

    document.addEventListener(
        "click",
        function (event) {
            if (
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }

            const clickedElement =
                event.target instanceof Element
                    ? event.target
                    : event.target.parentElement;
            const link = clickedElement?.closest("a[href]");
            if (
                !link ||
                link.getAttribute("hx-boost")?.toLowerCase() !== "true" ||
                link.target ||
                link.hasAttribute("download")
            ) {
                return;
            }

            const destination = new URL(link.href, window.location.href);
            const destinationPath = destination.pathname + destination.search;
            if (
                destination.origin !== window.location.origin ||
                destinationPath === currentPath()
            ) {
                return;
            }

            let cachedPages;
            try {
                cachedPages = JSON.parse(
                    window.localStorage.getItem("htmx-history-cache") || "[]",
                );
            } catch (error) {
                console.error("Unable to read the tab's HTMX history cache.", error);
                window.sessionStorage.removeItem("htmx-history-cache");
                return;
            }
            if (!Array.isArray(cachedPages)) {
                console.error("The tab's HTMX history cache has an invalid format.");
                window.sessionStorage.removeItem("htmx-history-cache");
                return;
            }
            const isCached = cachedPages.some(
                (page) => page.url === destinationPath,
            );
            if (!isCached) return;

            event.preventDefault();
            event.stopImmediatePropagation();
            window.dispatchEvent(
                new CustomEvent("finlo:cachedNavigation", {
                    detail: { path: destinationPath },
                }),
            );
            window.history.pushState(
                { ...window.history.state, htmx: true },
                "",
                destination.href,
            );
            window.dispatchEvent(
                new PopStateEvent("popstate", {
                    state: window.history.state,
                }),
            );
            setActiveSectionFromPath(destinationPath);
        },
        true,
    );

    document.addEventListener("htmx:historyRestore", function (event) {
        setActiveSectionFromPath(event.detail?.path || currentPath());
    });

    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const path = event.detail.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path)) {
            window.sessionStorage.removeItem("htmx-history-cache");
        }
    });
})();
