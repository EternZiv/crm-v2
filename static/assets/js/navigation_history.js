(function () {
    if (window._horillaNavigationHistoryInitialized || !window.htmx) return;
    window._horillaNavigationHistoryInitialized = true;

    const refreshHeader = "X-Horilla-History-Refresh";
    let refreshId = 0;
    let activeRefresh = null;

    htmx.config.historyCacheSize = 20;

    function currentPath() {
        return window.location.pathname + window.location.search;
    }

    function hasUnsavedChanges(container) {
        return Array.from(
            container.querySelectorAll("input, textarea, select"),
        ).some((field) => {
            if (field.type === "checkbox" || field.type === "radio") {
                return field.checked !== field.defaultChecked;
            }
            if (field.tagName === "SELECT") {
                return Array.from(field.options).some(
                    (option) => option.selected !== option.defaultSelected,
                );
            }
            return field.value !== field.defaultValue;
        });
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
        },
        true,
    );

    document.body.addEventListener("htmx:historyRestore", function (event) {
        const container = document.getElementById("mainContent");
        const path = new URL(event.detail.path || currentPath(), window.location.href);
        const restoredPath = path.pathname + path.search;
        const requestId = ++refreshId;

        if (!container || hasUnsavedChanges(container)) return;
        if (activeRefresh) {
            activeRefresh.abort();
            activeRefresh = null;
        }

        window.setTimeout(function () {
            if (
                requestId !== refreshId ||
                currentPath() !== restoredPath ||
                !document.getElementById("mainContent")
            ) {
                return;
            }

            const refreshSource = document.getElementById(
                "navigationHistoryRefresh",
            );
            if (!refreshSource) {
                console.error(
                    "The navigation history refresh source is missing from the application shell.",
                );
                return;
            }

            htmx.ajax("GET", path.href, {
                source: refreshSource,
                target: "#mainContent",
                swap: "outerHTML",
                headers: { [refreshHeader]: "true" },
            });
        }, 0);
    });

    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const isHistoryRefresh =
            event.detail.requestConfig?.headers?.[refreshHeader] === "true";
        if (isHistoryRefresh) {
            activeRefresh = event.detail.xhr;
        } else if (activeRefresh) {
            activeRefresh.abort();
            activeRefresh = null;
            refreshId += 1;
        }

        const path = event.detail.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path)) {
            window.sessionStorage.removeItem("htmx-history-cache");
        }
    });

    document.body.addEventListener("htmx:afterRequest", function (event) {
        if (event.detail.xhr === activeRefresh) {
            activeRefresh = null;
        }
    });
})();
