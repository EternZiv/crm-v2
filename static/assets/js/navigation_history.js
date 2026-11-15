/**
 * FINLONEXA CRM v2 - Instant Navigation, Smart LRU View Cache & Stale-While-Revalidate (SWR)
 * 
 * Provides:
 * 1. Immediate visual feedback (<10ms): instant active-state highlight.
 * 2. Instant client-side restoration (<5ms) of eligible views from bounded in-memory LRU cache.
 * 3. Stale-While-Revalidate (SWR): serves cached snapshot immediately, then revalidates in the
 *    background when stale, updating content without full-page reloads or distracting flicker.
 * 4. Background refresh management: pauses when browser tab is hidden, resumes on visibility.
 * 5. Race-condition & superseded request cancellation: older in-flight fetches never clobber newer navigation.
 * 6. Guaranteed mutation invalidation: all non-GET requests, form submits, and logout events flush the cache.
 * 7. Hardened ECharts instance cleanup: prevents memory leaks and canvas detachment reuse bugs.
 * 8. Scroll position capture and restoration: preserves viewport and table scroll offsets on cached visits.
 * 9. Duplicate in-flight navigation coalescing: prevents duplicate concurrent round-trips for the same URL.
 * 
 * Security & Scoping:
 * - Strictly in-memory (JS Map) - NEVER written to localStorage, sessionStorage, or disk.
 * - Cache keys incorporate userId and companyScope to enforce strict RBAC and tenant isolation.
 * - Form views, create/edit/delete actions, modals, and settings are NEVER cached.
 */
(function () {
    if (window._finloSmartNavigationInitialized || !window.htmx) return;
    window._finloSmartNavigationInitialized = true;

    // Configure native HTMX popstate history
    htmx.config.historyCacheSize = 20;
    htmx.config.refreshOnHistoryMiss = false;

    // --- Configuration & freshness policies ---
    const MAX_CACHED_VIEWS = 20;
    const MAX_CACHED_VIEW_BYTES = 8 * 1024 * 1024;

    // Per-view TTL policies (in milliseconds)
    const TTL_POLICIES = [
        { pattern: /\/dashboard\//i, ttl: 30000 },       // 30 seconds
        { pattern: /\/crm\/leads\//i, ttl: 30000 },       // 30 seconds
        { pattern: /\/crm\/accounts\//i, ttl: 30000 },    // 30 seconds
        { pattern: /\/crm\/contacts\//i, ttl: 30000 },    // 30 seconds
        { pattern: /\/crm\/opportunities\//i, ttl: 20000 }, // 20 seconds
        { pattern: /\/crm\/activities\//i, ttl: 20000 },  // 20 seconds
        { pattern: /.*/, ttl: 30000 }                     // 30 seconds default
    ];

    function getTtlForUrl(url) {
        const norm = normalizeUrl(url);
        for (const policy of TTL_POLICIES) {
            if (policy.pattern.test(norm)) {
                return policy.ttl;
            }
        }
        return 30000;
    }

    function estimateSnapshotBytes(data) {
        try {
            return JSON.stringify(data).length * 2 + 128;
        } catch (_error) {
            return MAX_CACHED_VIEW_BYTES + 1;
        }
    }

    // --- State Variables ---
    const viewCache = new Map();
    let viewCacheBytes = 0;
    const pendingFreshUpdates = new Map();
    let latestNavigationId = 0;
    const activeRevalidations = new Set();
    const activeInFlightNavigations = new Set();
    const historyFallbacks = new Set();
    const navigationRequests = new WeakMap();
    let pendingNavigation = null;
    let pendingHistoryValidation = null;
    let dashboardInterval = null;
    let leadRevisionRequest = null;
    let lastLeadRevision = null;
    let leadRevisionFailures = 0;
    let leadRevisionRetryAfter = 0;

    // Bounded, in-memory timing samples for the click → shell → request → usable
    // lifecycle. Route paths are recorded without query values or CRM data.
    const navigationMetrics = window.FinloNavigationMetrics || [];
    window.FinloNavigationMetrics = navigationMetrics;
    const NAVIGATION_METRICS_LIMIT = 30;
    const NAVIGATION_SHELL_TYPES = {
        home: "dashboard",
        dashboard: "dashboard",
        sales: "list",
        people: "list",
        analytics: "list",
        leads: "list",
        accounts: "list",
        contacts: "list",
        opportunities: "list",
        my_jobs: "list",
        reviews: "list",
        approvals: "list",
    };

    function createNavigationMetric(link, url, startedAt) {
        const parsedUrl = new URL(url, window.location.href);
        const metric = {
            routeId: link.id || link.dataset.section || "unknown",
            path: parsedUrl.pathname,
            clickAt: startedAt,
            shellPaintMs: null,
            requestDispatchMs: null,
            responseMs: null,
            usableMs: null,
            status: null,
            cacheRestore: false,
        };
        navigationMetrics.push(metric);
        if (navigationMetrics.length > NAVIGATION_METRICS_LIMIT) {
            navigationMetrics.splice(0, navigationMetrics.length - NAVIGATION_METRICS_LIMIT);
        }
        return metric;
    }

    function getNavigationShellType(link) {
        const explicitType = link.dataset.finloShell;
        if (["dashboard", "list", "generic"].includes(explicitType)) {
            return explicitType;
        }
        return NAVIGATION_SHELL_TYPES[(link.id || "").toLowerCase()] || "generic";
    }

    function showDestinationShell(link, navigation) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent) return false;

        // HTMX snapshots the source page immediately before its response swap.
        // Keep this transient shell out of that snapshot so Back cannot restore
        // a loading placeholder as if it were a completed page.
        suppressHistorySnapshot(mainContent);

        const shellType = getNavigationShellType(link);
        const template = document.getElementById(`finlo-nav-shell-${shellType}`);
        if (!template?.content) return false;

        cleanupDetachedChartInstances();
        mainContent.replaceChildren(template.content.cloneNode(true));
        mainContent.setAttribute("aria-busy", "true");
        mainContent.dataset.finloNavigationPending = String(navigation.id);
        navigation.shellType = shellType;
        navigation.shellInsertedAt = performance.now();

        requestAnimationFrame(() => requestAnimationFrame(() => {
            navigation.metric.shellPaintMs = Math.round(
                (performance.now() - navigation.startedAt) * 100,
            ) / 100;
        }));
        return true;
    }

    function suppressHistorySnapshot(mainContent) {
        const historyElement = mainContent?.closest("[hx-history-elt], [data-hx-history-elt]");
        if (historyElement && historyElement.getAttribute("hx-history") !== "false"
            && historyElement.getAttribute("data-hx-history") !== "false") {
            historyElement.setAttribute("data-finlo-history-suppressed", "true");
            historyElement.setAttribute("hx-history", "false");
        }
    }

    function getHistoryShellType(path) {
        let parsedUrl;
        try {
            parsedUrl = new URL(path, window.location.href);
        } catch (e) {
            return "generic";
        }

        if (/\/dashboard\//i.test(parsedUrl.pathname) || parsedUrl.searchParams.get("section") === "home") {
            return "dashboard";
        }
        if (/^\/crm\/(leads|accounts|contacts|opportunities|forecast)\//i.test(parsedUrl.pathname)) {
            return "list";
        }
        return "generic";
    }

    function showHistoryDestinationShell(path) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent) return false;

        const shellType = getHistoryShellType(path);
        const template = document.getElementById(`finlo-nav-shell-${shellType}`);
        if (!template?.content) return false;

        cleanupDetachedChartInstances();
        mainContent.replaceChildren(template.content.cloneNode(true));
        mainContent.setAttribute("aria-busy", "true");
        mainContent.dataset.finloHistoryNavigationPending = "true";
        setActiveSectionFromUrl(path);
        return true;
    }

    function clearProtectedHistoryCaches() {
        if (window.FinloViewCache) window.FinloViewCache.clear();
        try { window.sessionStorage?.removeItem("htmx-history-cache"); } catch (_error) {}
        try { window.localStorage?.removeItem("htmx-history-cache"); } catch (_error) {}
    }

    function showHistoryRestoreError(message, path, status) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent) return;

        const error = document.createElement("section");
        error.className = "m-5 rounded-xl border border-red-200 bg-white p-6 text-slate-800";
        error.setAttribute("role", "alert");
        const text = document.createElement("p");
        text.textContent = message || (status === 403
            ? "You do not have permission to open this page."
            : "This page could not be restored.");
        error.appendChild(text);

        if (status !== 401) {
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "mt-3 rounded-lg bg-primary-600 px-4 py-2 text-white";
            retry.dataset.finloHistoryRetry = "true";
            retry.dataset.finloHistoryUrl = path || (window.location.pathname + window.location.search);
            retry.textContent = "Retry";
            error.appendChild(retry);
        }

        mainContent.replaceChildren(error);
        mainContent.removeAttribute("aria-busy");
        delete mainContent.dataset.finloHistoryNavigationPending;
        delete mainContent.dataset.finloHistoryFallbackPending;
        hideProgressBar();
    }

    function initializeRestoredDashboard(mainContent) {
        if (!mainContent?.querySelector("#default-home-view")) return;
        if (typeof window.initFinloDefaultHomeDashboard === "function") {
            try { window.initFinloDefaultHomeDashboard(); } catch (error) {
                console.warn("Dashboard chart restoration failed:", error);
            }
        }
    }

    function finishHistoryValidation(path) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent || !isViewReadyForSnapshot(mainContent)) return false;

        mainContent.removeAttribute("aria-busy");
        delete mainContent.dataset.finloHistoryNavigationPending;
        delete mainContent.dataset.finloHistoryFallbackPending;
        if (pendingHistoryValidation?.timer) clearTimeout(pendingHistoryValidation.timer);
        pendingHistoryValidation = null;
        restoreHistorySnapshots();
        initializeRestoredDashboard(mainContent);
        window.dispatchEvent(new Event("resize"));
        document.dispatchEvent(new CustomEvent("finlo:viewRestored", { detail: { url: path } }));
        scheduleSnapshot();
        hideProgressBar();
        return true;
    }

    function scheduleHistoryValidation(path, fallbackUsed = false) {
        const target = new URL(path, window.location.href);
        if (target.origin !== window.location.origin) return;
        const key = normalizeUrl(target.href);

        if (pendingHistoryValidation?.timer) clearTimeout(pendingHistoryValidation.timer);
        if (!pendingHistoryValidation || pendingHistoryValidation.path !== key) {
            pendingHistoryValidation = {
                path: key,
                startedAt: Date.now(),
                fallbackUsed: Boolean(fallbackUsed),
                timer: null,
            };
        } else if (fallbackUsed) {
            pendingHistoryValidation.fallbackUsed = true;
        }

        pendingHistoryValidation.timer = setTimeout(() => {
            const state = pendingHistoryValidation;
            const mainContent = document.getElementById("mainContent");
            if (!state || state.path !== key || normalizeUrl(window.location.href) !== key) return;
            if (finishHistoryValidation(key)) return;

            const requestPending = mainContent?.matches(".htmx-request") || mainContent?.querySelector(".htmx-request");
            if (requestPending && Date.now() - state.startedAt < 10000) {
                scheduleHistoryValidation(key, state.fallbackUsed);
                return;
            }

            if (!state.fallbackUsed) {
                restoreInvalidHistorySnapshot(key);
                return;
            }

            showHistoryRestoreError("The page content did not finish loading. Retry to request it again.", key);
            pendingHistoryValidation = null;
        }, 500);
    }

    async function restoreInvalidHistorySnapshot(path) {
        let target;
        try { target = new URL(path, window.location.href); } catch (_error) { return; }
        if (target.origin !== window.location.origin || !/^https?:$/.test(target.protocol)) return;

        const key = normalizeUrl(target.href);
        if (historyFallbacks.has(key)) return;
        historyFallbacks.add(key);

        const restoreId = ++latestNavigationId;
        pendingNavigation = null;
        activeInFlightNavigations.add(key);
        showHistoryDestinationShell(target.href);
        showProgressBar();

        try {
            const response = await fetch(target.href, {
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "HX-Request": "true",
                    "HX-Target": "#mainContent",
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (restoreId !== latestNavigationId || normalizeUrl(window.location.href) !== key) return;

            const finalUrl = new URL(response.url || target.href, window.location.href);
            if (response.status === 401 || (response.redirected && finalUrl.pathname.replace(/\/$/, "") === "/login")) {
                clearProtectedHistoryCaches();
                const loginUrl = finalUrl.origin === window.location.origin
                    ? finalUrl.href
                    : `${window.location.origin}/login/?next=${encodeURIComponent(target.pathname + target.search)}`;
                window.location.replace(loginUrl);
                return;
            }
            if (response.status === 403) {
                clearProtectedHistoryCaches();
                showHistoryRestoreError(null, key, 403);
                return;
            }
            if (!response.ok) {
                showHistoryRestoreError("The page could not be restored from the server. Retry to try again.", key, response.status);
                return;
            }

            const html = await response.text();
            if (restoreId !== latestNavigationId || normalizeUrl(window.location.href) !== key) return;

            const doc = new DOMParser().parseFromString(html, "text/html");
            const freshMain = doc.querySelector("#mainContent");
            if (!freshMain) {
                const redirectedToLogin = doc.querySelector("form[action*='login'], #loginForm");
                if (redirectedToLogin) {
                    clearProtectedHistoryCaches();
                    window.location.replace(`${window.location.origin}/login/?next=${encodeURIComponent(target.pathname + target.search)}`);
                    return;
                }
                showHistoryRestoreError("The server response did not contain this page. Retry to try again.", key);
                return;
            }

            const nestedHeader = freshMain.querySelector("#header");
            if (nestedHeader) nestedHeader.remove();
            const nestedSidebar = freshMain.querySelector("#sidebar, #primarySidebar");
            if (nestedSidebar) nestedSidebar.remove();

            const mainContent = document.getElementById("mainContent");
            if (!mainContent) return;
            cleanupDetachedChartInstances();
            mainContent.innerHTML = freshMain.innerHTML;
            mainContent.setAttribute("aria-busy", "true");
            mainContent.dataset.finloHistoryFallbackPending = key;

            const freshSideMenu = doc.querySelector("#sideMenuContainer");
            const sideMenu = document.getElementById("sideMenuContainer");
            if (freshSideMenu && sideMenu) sideMenu.innerHTML = freshSideMenu.innerHTML;

            setActiveSectionFromUrl(key);
            if (window.htmx) {
                htmx.process(mainContent);
                if (sideMenu) htmx.process(sideMenu);
            }
            reexecuteScripts(mainContent);
            if (typeof window.bootstrapFinloUI === "function") window.bootstrapFinloUI(mainContent);
            initializeRestoredDashboard(mainContent);
            restoreHistorySnapshots();

            pendingHistoryValidation = {
                path: key,
                startedAt: Date.now(),
                fallbackUsed: true,
                timer: null,
            };
            scheduleHistoryValidation(key, true);
        } catch (error) {
            if (restoreId === latestNavigationId && normalizeUrl(window.location.href) === key) {
                showHistoryRestoreError("The page could not be restored because the request failed. Retry to try again.", key);
                pendingHistoryValidation = null;
            }
            console.debug("History restore fallback failed:", error.message);
        } finally {
            historyFallbacks.delete(key);
            activeInFlightNavigations.delete(key);
        }
    }

    document.addEventListener("click", function (event) {
        const retry = event.target instanceof Element
            ? event.target.closest("[data-finlo-history-retry]")
            : null;
        if (!retry) return;
        event.preventDefault();
        restoreInvalidHistorySnapshot(retry.dataset.finloHistoryUrl || window.location.href);
    });

    document.body.addEventListener("htmx:historyCacheMiss", function (event) {
        showHistoryDestinationShell(event.detail?.path || window.location.href);
    });

    document.body.addEventListener("htmx:historyCacheMissLoadError", function (event) {
        const xhr = event.detail?.xhr;
        const responseUrl = xhr?.responseURL ? new URL(xhr.responseURL, window.location.href) : null;
        if (xhr?.status === 401 || (responseUrl && responseUrl.pathname.replace(/\/$/, "") === "/login")) {
            clearProtectedHistoryCaches();
            const next = window.location.pathname + window.location.search;
            window.location.replace(responseUrl?.origin === window.location.origin
                ? responseUrl.href
                : `${window.location.origin}/login/?next=${encodeURIComponent(next)}`);
            return;
        }
        showHistoryRestoreError(
            "This page could not be restored. Retry to request the current page.",
            event.detail?.path || (window.location.pathname + window.location.search),
            xhr?.status || 0,
        );
    });

    function showNavigationFailure(navigation, status) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent) return;

        const error = document.createElement("section");
        error.className = "m-5 rounded-xl border border-red-200 bg-white p-6 text-slate-800";
        error.setAttribute("role", "alert");

        const heading = document.createElement("h2");
        heading.className = "mb-2 text-lg font-semibold";
        heading.textContent = status === 403
            ? "You do not have permission to open this page."
            : status === 404
                ? "This page could not be found."
                : "This page could not be loaded.";

        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "mt-3 rounded-lg bg-primary-600 px-4 py-2 text-white";
        retry.dataset.finloNavRetry = "true";
        retry.textContent = "Retry";

        error.append(heading, retry);
        mainContent.replaceChildren(error);
        mainContent.removeAttribute("aria-busy");
        delete mainContent.dataset.finloNavigationPending;
        restoreHistorySnapshots();
        navigation.failed = true;
        navigation.metric.status = status || 0;
        pendingNavigation = navigation;
        hideProgressBar();
    }

    function restoreHistorySnapshots() {
        document.querySelectorAll('[data-finlo-history-suppressed="true"]').forEach((element) => {
            element.removeAttribute("hx-history");
            element.removeAttribute("data-finlo-history-suppressed");
        });
    }

    document.addEventListener("click", function (event) {
        const retry = event.target instanceof Element
            ? event.target.closest("[data-finlo-nav-retry]")
            : null;
        if (!retry || !pendingNavigation?.failed || !pendingNavigation.link?.isConnected) return;
        event.preventDefault();
        pendingNavigation.link.click();
    });

    // --- User & Company Scoping ---
    function getActiveUserId() {
        return document.body?.dataset.userId || "0";
    }

    function getActiveCompanyScope() {
        return document.body?.dataset.companyScope || "none";
    }

    function normalizeUrl(url) {
        if (!url) return "";
        try {
            const u = new URL(url, window.location.origin);
            const params = Array.from(u.searchParams.entries()).sort(([ak, av], [bk, bv]) =>
                ak === bk ? av.localeCompare(bv) : ak.localeCompare(bk)
            );
            const query = new URLSearchParams(params).toString();
            return u.pathname + (query ? `?${query}` : "");
        } catch (e) {
            return url;
        }
    }

    function buildCacheKey(url) {
        const norm = normalizeUrl(url);
        return `${getActiveUserId()}|${getActiveCompanyScope()}|${norm}`;
    }

    function isCacheableUrl(url) {
        if (!url) return false;
        const norm = normalizeUrl(url).toLowerCase();

        // Must be internal CRM navigation
        if (norm.startsWith("/static/") || norm.includes("/assets/")) return false;
        if (norm.includes("/login") || norm.includes("/logout") || norm.includes("/auth")) return false;
        if (norm.includes("/reload_messages") || norm.includes("/notifications/")) return false;
        if (norm.includes("/export") || norm.includes("/download") || norm.includes("/webhook/")) return false;

        // Never cache transactional form builder, edit, or input submission screens
        if (norm.includes("-create") || norm.includes("-edit") || norm.includes("-delete") || norm.includes("/capture/")) return false;
        if (norm.includes("form-builder") || norm.includes("modal")) return false;
        if (norm.includes("/settings/") || norm.includes("/users/") || norm.includes("/roles/")) return false;

        // Skip actively queried search input queries
        if (/[\?\&]search=[^\&]+/.test(norm)) return false;

        return true;
    }

    // --- Active Form & Modal Safety Guard ---
    function isFormOrModalActiveOrDirty() {
        // 1. Check focused element
        const activeEl = document.activeElement;
        if (activeEl && (
            activeEl.tagName === "INPUT" ||
            activeEl.tagName === "TEXTAREA" ||
            activeEl.tagName === "SELECT" ||
            activeEl.isContentEditable ||
            activeEl.closest(".note-editor, .modal, [role='dialog'], form")
        )) {
            return true;
        }

        // 2. Check for open modals or dialogs (e.g. #modalBox or Flowbite modals)
        const openModal = document.querySelector("#modalBox:not(:empty), .modal:not(.hidden):not([style*='display: none']), [role='dialog']:not(.hidden):not([style*='display: none'])");
        if (openModal) {
            return true;
        }

        // 3. Check for dirty form fields (modified by user)
        const forms = document.querySelectorAll("form");
        for (const form of forms) {
            // Ignore filter controls that are auto-applied search bars
            if (form.matches("#filter-form, .filter-form, #search-form")) continue;
            const inputs = form.querySelectorAll("input:not([type='hidden']):not([name='search']):not([name='csrfmiddlewaretoken']), textarea, select");
            for (const input of inputs) {
                if (input.type === "file" && input.files && input.files.length > 0) {
                    return true;
                }
                if ((input.type === "checkbox" || input.type === "radio") && input.checked !== input.defaultChecked) {
                    return true;
                }
                if (input.tagName === "TEXTAREA" && input.value !== input.defaultValue) {
                    return true;
                }
                if (input.tagName === "INPUT" && input.type !== "checkbox" && input.type !== "radio" && input.type !== "file" && input.value !== input.defaultValue) {
                    return true;
                }
            }
        }

        // 4. Check for active rich-text editors (Summernote / TinyMCE)
        const summernoteEditors = document.querySelectorAll(".note-editor");
        if (summernoteEditors.length > 0) {
            return true;
        }

        return false;
    }

    // --- ECharts Cleanup Helper ---
    function cleanupDetachedChartInstances() {
        // 1. Dispose instances tracked by echarts DOM binding
        if (window.echarts && typeof window.echarts.getInstanceByDom === "function") {
            const chartDoms = document.querySelectorAll("#mainContent [_echarts_instance_], #mainContent canvas");
            chartDoms.forEach((node) => {
                const target = node.hasAttribute("_echarts_instance_") ? node : node.parentElement;
                if (target) {
                    const inst = window.echarts.getInstanceByDom(target);
                    if (inst && typeof inst.dispose === "function") {
                        try { inst.dispose(); } catch (e) {}
                    }
                }
            });
        }

        // 2. Dispose and clean up global chartInstances registry
        if (window.chartInstances && typeof window.chartInstances === "object") {
            const mainContent = document.getElementById("mainContent");
            Object.keys(window.chartInstances).forEach((key) => {
                const item = window.chartInstances[key];
                const inst = item && (item.instance || item);
                if (inst && typeof inst.dispose === "function") {
                    const dom = typeof inst.getDom === "function" ? inst.getDom() : null;
                    if (!dom || !dom.isConnected || (mainContent && mainContent.contains(dom))) {
                        try {
                            if (!inst.isDisposed?.()) {
                                inst.dispose();
                            }
                        } catch (e) {}
                        delete window.chartInstances[key];
                    }
                }
            });
        }
    }

    // --- Scroll State Capture & Restoration ---
    function captureScrollState(mainContent) {
        if (!mainContent) return null;
        const state = {
            mainTop: mainContent.scrollTop || 0,
            mainLeft: mainContent.scrollLeft || 0,
            tableTop: 0,
            tableLeft: 0
        };
        const tableContainer = mainContent.querySelector("#tableContainer, .table-container");
        if (tableContainer) {
            state.tableTop = tableContainer.scrollTop || 0;
            state.tableLeft = tableContainer.scrollLeft || 0;
        }
        return state;
    }

    function restoreScrollState(mainContent, scrollState) {
        if (!mainContent || !scrollState) return;
        requestAnimationFrame(() => {
            mainContent.scrollTop = scrollState.mainTop || 0;
            mainContent.scrollLeft = scrollState.mainLeft || 0;
            const tableContainer = mainContent.querySelector("#tableContainer, .table-container");
            if (tableContainer) {
                tableContainer.scrollTop = scrollState.tableTop || 0;
                tableContainer.scrollLeft = scrollState.tableLeft || 0;
            }
        });
    }

    // --- Snapshot Readiness Validator ---
    function isViewReadyForSnapshot(mainContent) {
        if (!mainContent) return false;

        // 1. Do not capture during loading indicators, spinners, or skeletons
        if (mainContent.querySelector("#header") ||
            mainContent.querySelector("#finlo-skeleton-loader") ||
            mainContent.querySelector(".finlo-skeleton") ||
            mainContent.querySelector(".htmx-indicator.htmx-request") ||
            mainContent.querySelector("#loading-indicator[style*='display: flex']")) {
            return false;
        }

        // 2. Do not capture when subviews are still unrendered placeholders
        const emptyLoaders = mainContent.querySelectorAll(
            "[hx-trigger*='load']:empty, #mainSession:empty, #navBar:empty"
        );
        if (emptyLoaders.length > 0) {
            return false;
        }

        // 3. Minimum content validation: must have non-trivial DOM tree
        if (!mainContent.firstElementChild || mainContent.innerHTML.trim().length < 80) {
            return false;
        }

        return true;
    }

    // --- Bounded LRU Cache Implementation ---
    const FinloViewCache = {
        get(url) {
            if (!isCacheableUrl(url)) return null;
            const key = buildCacheKey(url);
            const entry = viewCache.get(key);
            if (!entry) return null;

            // Security check: Verify that user and company scope still match current session
            if (entry.userId !== getActiveUserId() || entry.companyScope !== getActiveCompanyScope()) {
                viewCache.clear();
                viewCacheBytes = 0;
                return null;
            }

            // Touch entry for true LRU (re-insert moves it to the end of iteration order)
            viewCache.delete(key);
            viewCacheBytes -= entry.cacheBytes || 0;
            viewCache.set(key, entry);
            viewCacheBytes += entry.cacheBytes || 0;

            return entry;
        },
        set(url, data) {
            if (!isCacheableUrl(url)) return;
            const key = buildCacheKey(url);
            const cacheBytes = estimateSnapshotBytes(data);
            if (cacheBytes > MAX_CACHED_VIEW_BYTES) return;

            if (viewCache.has(key)) {
                viewCacheBytes -= viewCache.get(key).cacheBytes || 0;
                viewCache.delete(key);
            }
            while (viewCache.size >= MAX_CACHED_VIEWS ||
                   viewCacheBytes + cacheBytes > MAX_CACHED_VIEW_BYTES) {
                const lruKey = viewCache.keys().next().value;
                if (lruKey === undefined) break;
                viewCacheBytes -= viewCache.get(lruKey)?.cacheBytes || 0;
                viewCache.delete(lruKey);
            }

            const ttl = getTtlForUrl(url);
            viewCache.set(key, {
                ...data,
                userId: getActiveUserId(),
                companyScope: getActiveCompanyScope(),
                // Freshness threshold for SWR, not snapshot expiration.
                revalidateAfterMs: ttl,
                timestamp: Date.now(),
                cacheBytes
            });
        },
        has(url) {
            return FinloViewCache.get(url) !== null;
        },
        delete(url) {
            const key = buildCacheKey(url);
            viewCacheBytes -= viewCache.get(key)?.cacheBytes || 0;
            viewCache.delete(key);
        },
        clear() {
            viewCache.clear();
            viewCacheBytes = 0;
            activeRevalidations.clear();
            activeInFlightNavigations.clear();
        },
        size() {
            return viewCache.size;
        }
    };
    window.FinloViewCache = FinloViewCache;

    // --- Visual Progress Bar (<2px top indicator) ---
    function showProgressBar() {}
    function hideProgressBar() {}

    // --- Active Sidebar Navigation Styling ---
    function setActiveSectionFromUrl(path) {
        if (typeof window.syncActiveNavigation === "function") {
            window.syncActiveNavigation(path);
            return;
        }
        try {
            const sectionId = new URL(path, window.location.href).searchParams.get("section");
            if (!sectionId) return;

            const activeLink = document.getElementById(sectionId);
            if (activeLink) {
                document.querySelectorAll("#primarySidebar a").forEach((link) => {
                    link.classList.remove("finlo-nav-active", "bg-primary-600", "hover:bg-primary-800");
                });
                activeLink.classList.add("finlo-nav-active");
                window.localStorage.setItem("activeNavLinkId", sectionId);
                window.localStorage.setItem("currentActiveSection", sectionId);
                window.localStorage.setItem("lastActiveSection", sectionId);
            }
        } catch (e) {}
    }

    function highlightLinkImmediately(link) {
        if (!link) return;
        document.querySelectorAll("#primarySidebar a").forEach((l) => {
            l.classList.remove("finlo-nav-active", "bg-primary-600", "text-white", "hover:bg-primary-800");
        });
        link.classList.add("finlo-nav-active");
        if (typeof window.syncActiveNavigation === "function") {
            window.syncActiveNavigation(link.href || window.location.href);
        }
        const sectionId = link.getAttribute("data-section") || link.closest("[data-nav-section]")?.getAttribute("data-nav-section") || link.id;
        const linkId = link.id;
        if (linkId && sectionId) {
            window.localStorage.setItem(`activeSidebarLinkId_${sectionId}`, linkId);
            window.localStorage.setItem("activeSidebarLinkId", linkId);
            window.localStorage.setItem("sidebarClicked", "true");
        }
    }

    // --- Script Re-Execution Helper ---
    function reexecuteScripts(container) {
        if (!container) return;
        const scripts = container.querySelectorAll("script");
        scripts.forEach((oldScript) => {
            if (!oldScript.src) {
                const newScript = document.createElement("script");
                Array.from(oldScript.attributes).forEach((attr) => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                newScript.textContent = oldScript.textContent;
                oldScript.parentNode.replaceChild(newScript, oldScript);
            }
        });
    }

    // --- View Restoration Engine ---
    function restoreView(url, cached) {
        const mainContent = document.getElementById("mainContent");
        if (!mainContent || !cached || !cached.mainContentHtml) return false;

        // Sanity check: Never restore a blank or incomplete view
        let htmlToRestore = cached.mainContentHtml.trim();
        if (htmlToRestore.length < 80) {
            FinloViewCache.delete(url);
            return false;
        }

        // Verify it does not contain unfilled lazy shells or pending skeletons
        const tempTest = document.createElement("div");
        tempTest.innerHTML = htmlToRestore;
        if (tempTest.querySelector("#mainSession:empty") || tempTest.querySelector("#navBar:empty") || tempTest.querySelector(".finlo-skeleton")) {
            FinloViewCache.delete(url);
            return false;
        }

        // 1. Clean up detached ECharts before replacing DOM
        cleanupDetachedChartInstances();

        // 2. Clean up open Select2 dropdowns if any
        if (window.jQuery && jQuery(".select2-hidden-accessible").length) {
            try { jQuery(".select2-hidden-accessible").select2("close"); } catch (e) {}
        }
        document.querySelectorAll("body > .select2-container").forEach((el) => el.remove());

        // 3. Sanitize cached HTML: guarantee no nested header or sidebar
        if (htmlToRestore.includes('id="header"') || htmlToRestore.includes('id="sidebar"') || htmlToRestore.includes('id="primarySidebar"')) {
            const temp = document.createElement("div");
            temp.innerHTML = htmlToRestore;
            const h = temp.querySelector("#header");
            if (h) h.remove();
            const s = temp.querySelector("#sidebar, #primarySidebar");
            if (s) s.remove();
            const nestedMain = temp.querySelector("#mainContent");
            htmlToRestore = nestedMain ? nestedMain.innerHTML : temp.innerHTML;
        }

        // 4. Swap main content HTML
        mainContent.innerHTML = htmlToRestore;

        // 5. Swap sub-sidebar HTML if present
        if (cached.sideMenuHtml) {
            const sideMenuContainer = document.getElementById("sideMenuContainer");
            if (sideMenuContainer) {
                sideMenuContainer.innerHTML = cached.sideMenuHtml;
            }
        }

        // 6. Update URL in browser address bar and history
        if (window.location.href !== url) {
            // HTMX handles popstate only for entries carrying this marker.
            // Suppress its next snapshot while its private path can be stale.
            suppressHistorySnapshot(mainContent);
            history.pushState({ htmx: true }, "", url);
        }

        // 7. Update sidebar visual indicator
        if (window.SidebarNav && typeof window.SidebarNav.initFromUrl === "function") {
            try { window.SidebarNav.initFromUrl(); } catch (e) {}
        } else {
            setActiveSectionFromUrl(url);
        }

        // 8. Re-bind HTMX triggers on the restored DOM nodes
        if (window.htmx) {
            htmx.process(mainContent);
            const sideMenuContainer = document.getElementById("sideMenuContainer");
            if (sideMenuContainer) htmx.process(sideMenuContainer);
        }

        // 9. Re-execute component initialization scripts (charts, table bindings)
        reexecuteScripts(mainContent);
        initializeRestoredDashboard(mainContent);

        // 10. Restore scroll position
        if (cached.scrollState) {
            restoreScrollState(mainContent, cached.scrollState);
        }

        // 11. Trigger responsive resize for charts
        setTimeout(() => window.dispatchEvent(new Event("resize")), 50);

        // 12. Custom restoration event for extension hooks
        document.dispatchEvent(new CustomEvent("finlo:viewRestored", { detail: { url: url } }));
        return true;
    }

    // --- Stale-While-Revalidate (SWR) Engine ---
    async function revalidateView(url, navId) {
        if (!isCacheableUrl(url) || activeRevalidations.has(url)) return;
        activeRevalidations.add(url);
        showProgressBar();

        try {
            // Fetch fresh HTML from Django
            const response = await fetch(url, {
                headers: {
                    "HX-Request": "true",
                    "HX-Target": "#mainContent",
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin"
            });

            const responseUrl = new URL(response.url || url, window.location.href);
            if (response.status === 401 || (response.redirected && responseUrl.pathname.replace(/\/$/, "") === "/login")) {
                clearProtectedHistoryCaches();
                window.location.replace(responseUrl.origin === window.location.origin
                    ? responseUrl.href
                    : `/login/?next=${encodeURIComponent(new URL(url, window.location.href).pathname + new URL(url, window.location.href).search)}`);
                return;
            }
            if (response.status === 403) {
                clearProtectedHistoryCaches();
                if (navId === latestNavigationId && normalizeUrl(window.location.href) === normalizeUrl(url)) {
                    showHistoryRestoreError(null, url, 403);
                }
                return;
            }
            if (!response.ok) {
                throw new Error(`Revalidation failed with status ${response.status}`);
            }

            const html = await response.text();

            // Discard response if user has already navigated elsewhere
            if (navId !== latestNavigationId || normalizeUrl(window.location.href) !== normalizeUrl(url)) {
                return;
            }

            // Extract fresh HTML content using standard DOMParser
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const newMain = doc.querySelector("#mainContent");
            if (!newMain) {
                return;
            }

            // Guarantee no nested #header or #sidebar exists inside freshMain
            const nestedHeader = newMain.querySelector("#header");
            if (nestedHeader) nestedHeader.remove();
            const nestedSidebar = newMain.querySelector("#sidebar, #primarySidebar");
            if (nestedSidebar) nestedSidebar.remove();

            const freshMainHtml = newMain.innerHTML;
            const docSideContainer = doc.querySelector("#sideMenuContainer");
            const sideMenuContainer = document.getElementById("sideMenuContainer");
            const freshSideHtml = docSideContainer ? docSideContainer.innerHTML : (sideMenuContainer ? sideMenuContainer.innerHTML : "");

            // Check if user is currently interacting with an input / form / modal or has dirty unsaved changes
            const userEditingOrDirty = isFormOrModalActiveOrDirty();

            // Store fresh HTML into cache immediately so subsequent navigations receive fresh data
            FinloViewCache.set(url, {
                mainContentHtml: freshMainHtml,
                sideMenuHtml: freshSideHtml
            });

            if (userEditingOrDirty) {
                // User is actively editing or has open modal/dirty form: DO NOT overwrite active DOM!
                pendingFreshUpdates.set(url, {
                    mainContentHtml: freshMainHtml,
                    sideMenuHtml: freshSideHtml,
                    timestamp: Date.now()
                });

                document.querySelectorAll("form").forEach((f) => {
                    f.addEventListener("reset", () => {
                        setTimeout(() => applyPendingFreshUpdate(url), 100);
                    }, { once: true });
                });
                return;
            }

            // Safe to update DOM:
            const mainContent = document.getElementById("mainContent");
            if (mainContent && freshMainHtml && freshMainHtml !== mainContent.innerHTML) {
                cleanupDetachedChartInstances();
                mainContent.innerHTML = freshMainHtml;
                if (window.htmx) htmx.process(mainContent);
                reexecuteScripts(mainContent);
                if (typeof window.bootstrapFinloUI === "function") {
                    window.bootstrapFinloUI(mainContent);
                }
                window.dispatchEvent(new Event("resize"));
            }

        } catch (error) {
            console.debug("Background revalidation note:", error.message);
        } finally {
            activeRevalidations.delete(url);
            hideProgressBar();
        }
    }

    // --- Fast Navigation Click Interceptor (Capture Phase) ---
    document.addEventListener("click", function (event) {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }

        const link = event.target.closest("nav a.nav-link, #subSidebar a.sidebar-link, a[hx-boost='true']");
        if (!link) return;

        const href = link.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;

        const target = link.getAttribute("hx-target") || (link.hasAttribute("hx-boost") ? "#mainContent" : "");
        if (target !== "#mainContent") return;

        let fullUrl;
        try {
            fullUrl = new URL(href, window.location.href).href;
        } catch (e) {
            return;
        }

        // Prevent redundant click on exact current page
        if (fullUrl === window.location.href) return;

        // Prevent duplicate concurrent in-flight requests for the same URL
        if (activeInFlightNavigations.has(fullUrl)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return false;
        }

        // 1. Immediate visual feedback: highlight and replace stale page content
        // with a destination-specific shell before HTMX dispatches the request.
        highlightLinkImmediately(link);

        // 2. Increment navigation sequence to protect against race conditions
        const navId = ++latestNavigationId;
        const startedAt = performance.now();
        const navigation = {
            id: navId,
            url: fullUrl,
            link,
            startedAt,
            xhr: null,
            swapped: false,
            failed: false,
            metric: createNavigationMetric(link, fullUrl, startedAt),
        };
        pendingNavigation = navigation;

        // 3. Check FinloViewCache for instant restoration
        const cached = FinloViewCache.get(fullUrl);
        if (cached && cached.mainContentHtml) {
            const restored = restoreView(fullUrl, cached);
            if (restored) {
                // Prevent HTMX from triggering an expensive blocking round-trip
                event.preventDefault();
                event.stopImmediatePropagation();
                hideProgressBar();
                navigation.metric.cacheRestore = true;
                navigation.metric.shellPaintMs = 0;
                navigation.metric.requestDispatchMs = 0;
                navigation.metric.responseMs = 0;
                navigation.metric.usableMs = Math.round((performance.now() - startedAt) * 100) / 100;
                navigation.metric.status = 200;
                pendingNavigation = null;

                // 4. Stale-While-Revalidate (SWR): if stale, revalidate silently in background
                const age = Date.now() - cached.timestamp;
                if (age > (cached.revalidateAfterMs ?? cached.ttl ?? 30000)) {
                    revalidateView(fullUrl, navId);
                }
                return false;
            }
        }

        // Cache Miss: Track in-flight navigation
        activeInFlightNavigations.add(fullUrl);
        link.dataset.finloNavigationPending = String(navId);
        showDestinationShell(link, navigation);
        // Let HTMX proceed with normal request to Django
    }, true);

    // Associate HTMX's request lifecycle with the latest navigation intent.
    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const navigation = pendingNavigation;
        if (!navigation || navigation.id !== latestNavigationId || event.detail?.elt !== navigation.link) return;

        navigation.xhr = event.detail.xhr;
        navigation.dispatchedAt = performance.now();
        navigation.metric.requestDispatchMs = Math.round(
            (navigation.dispatchedAt - navigation.startedAt) * 100,
        ) / 100;
        navigationRequests.set(event.detail.xhr, navigation);
    });

    document.body.addEventListener("htmx:beforeSwap", function (event) {
        const navigation = navigationRequests.get(event.detail?.xhr);
        if (navigation && navigation.id !== latestNavigationId) {
            event.detail.shouldSwap = false;
            navigation.metric.staleResponse = true;
        }
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const navigation = navigationRequests.get(event.detail?.xhr);
        if (!navigation || navigation.id !== latestNavigationId || event.detail?.target?.id !== "mainContent") return;

        navigation.swapped = true;
        const mainContent = document.getElementById("mainContent");
        if (mainContent) {
            mainContent.removeAttribute("aria-busy");
            delete mainContent.dataset.finloNavigationPending;
        }
        restoreHistorySnapshots();
    });

    document.body.addEventListener("htmx:afterSettle", function (event) {
        const navigation = navigationRequests.get(event.detail?.xhr);
        if (!navigation || navigation.id !== latestNavigationId || !navigation.swapped) return;

        navigation.metric.usableMs = Math.round((performance.now() - navigation.startedAt) * 100) / 100;
        navigation.metric.status = event.detail?.xhr?.status || 200;
        if (pendingNavigation === navigation) pendingNavigation = null;
    });

    // A failed navigation replaces the shell with a small retry state, never
    // leaves a permanent skeleton or reinserts content from the previous route.
    document.body.addEventListener("htmx:afterRequest", function (event) {
        const reqPath = event.detail?.pathInfo?.requestPath;
        if (reqPath) {
            try {
                const fullUrl = new URL(reqPath, window.location.href).href;
                activeInFlightNavigations.delete(fullUrl);
            } catch (e) {
                activeInFlightNavigations.clear();
            }
        } else {
            activeInFlightNavigations.clear();
        }

        const navigation = navigationRequests.get(event.detail?.xhr);
        if (!navigation) return;

        const completedAt = performance.now();
        if (navigation.dispatchedAt !== undefined) {
            navigation.metric.responseMs = Math.round(
                (completedAt - navigation.dispatchedAt) * 100,
            ) / 100;
        }
        const status = event.detail?.xhr?.status || 0;
        navigation.metric.status = status;

        if (navigation.link?.dataset) delete navigation.link.dataset.finloNavigationPending;
        if (navigation.id !== latestNavigationId || navigation.failed) return;

        if (event.detail?.failed || status >= 400 || status === 0 || !navigation.swapped) {
            const hxRedirect = event.detail?.xhr?.getResponseHeader?.("HX-Redirect");
            if (status === 401 && hxRedirect) {
                window.location.assign(hxRedirect);
                return;
            }
            showNavigationFailure(navigation, status);
        } else if (pendingNavigation === navigation) {
            pendingNavigation = null;
        }
    });

    document.body.addEventListener("htmx:sendError", function (event) {
        const navigation = navigationRequests.get(event.detail?.xhr) || pendingNavigation;
        if (navigation && navigation.id === latestNavigationId && !navigation.failed) {
            showNavigationFailure(navigation, 0);
        }
        activeInFlightNavigations.clear();
    });

    document.body.addEventListener("htmx:abort", function () {
        activeInFlightNavigations.clear();
    });

    // --- Snapshot Capture after View Settles ---
    let captureTimeout = null;
    function scheduleSnapshot() {
        if (captureTimeout) clearTimeout(captureTimeout);
        captureTimeout = setTimeout(() => {
            const currentUrl = window.location.href;
            if (!isCacheableUrl(currentUrl)) return;

            const mainContent = document.getElementById("mainContent");
            if (!isViewReadyForSnapshot(mainContent)) {
                return;
            }

            const sideMenuContainer = document.getElementById("sideMenuContainer");
            const scrollState = captureScrollState(mainContent);

            FinloViewCache.set(currentUrl, {
                mainContentHtml: mainContent.innerHTML,
                sideMenuHtml: sideMenuContainer ? sideMenuContainer.innerHTML : "",
                scrollState: scrollState
            });
            hideProgressBar();
        }, 50);
    }

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail?.target;
        const targetId = target && target.id;
        if (targetId === "mainContent" || targetId === "calendarContainer" || targetId === "mainSession" || targetId === "navBar" || (target && target.closest && target.closest("#mainContent"))) {
            setActiveSectionFromUrl(window.location.href);
            scheduleSnapshot();
        }
    });

    document.body.addEventListener("htmx:afterSettle", function (event) {
        scheduleSnapshot();
        if (pendingHistoryValidation &&
            normalizeUrl(window.location.href) === pendingHistoryValidation.path &&
            (document.getElementById("mainContent")?.dataset.finloHistoryNavigationPending ||
             document.getElementById("mainContent")?.dataset.finloHistoryFallbackPending)) {
            scheduleHistoryValidation(pendingHistoryValidation.path, pendingHistoryValidation.fallbackUsed);
        }
    });

    document.addEventListener("htmx:historyRestore", function (event) {
        // The address bar is the final source of truth. Browser history entries
        // can carry a stale HTMX path when older snapshots were saved.
        const path = window.location.pathname + window.location.search;
        setActiveSectionFromUrl(path);
        const mainContent = document.getElementById("mainContent");
        if (mainContent) {
            cleanupDetachedChartInstances();
            reexecuteScripts(mainContent);
            initializeRestoredDashboard(mainContent);
            window.dispatchEvent(new Event("resize"));
        }
        restoreHistorySnapshots();
        // HTMX already requests a cache miss through its same-origin AJAX path.
        // Validate after nested fragments settle; invalid stored snapshots get
        // one bounded server fetch without triggering a full document reload.
        scheduleHistoryValidation(path, Boolean(event.detail?.cacheMiss));
    });

    // --- Tab Visibility & Background Refresh Strategy ---
    function isLeadResourceRoute(url) {
        const parsed = new URL(url, window.location.href);
        return /\/crm\/leads\//i.test(parsed.pathname) ||
            /\/dashboard\//i.test(parsed.pathname) ||
            parsed.searchParams.get("section") === "home";
    }

    async function checkLeadResourceRevision() {
        if (document.visibilityState !== "visible" || navigator.onLine === false) return;
        if (Date.now() < leadRevisionRetryAfter) return;
        if (leadRevisionRequest) return leadRevisionRequest;

        const requestedUrl = window.location.href;
        leadRevisionRequest = (async () => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            try {
                const response = await fetch("/crm/leads/cache-revision/", {
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    signal: controller.signal
                });
                if (response.status === 401) {
                    stopDashboardInterval();
                    FinloViewCache.clear();
                    window.location.reload();
                    return;
                }
                if (response.status === 403) {
                    stopDashboardInterval();
                    FinloViewCache.clear();
                    if (/\/crm\/leads\//i.test(new URL(requestedUrl).pathname)) {
                        window.location.reload();
                    } else if (normalizeUrl(window.location.href) === normalizeUrl(requestedUrl)) {
                        await revalidateView(requestedUrl, ++latestNavigationId);
                    }
                    return;
                }
                if (!response.ok) {
                    leadRevisionFailures += 1;
                    leadRevisionRetryAfter = Date.now() + Math.min(
                        120000,
                        30000 * (2 ** Math.min(leadRevisionFailures - 1, 2))
                    );
                    return;
                }
                if (normalizeUrl(window.location.href) !== normalizeUrl(requestedUrl)) return;
                const payload = await response.json();
                const revision = payload?.resources?.leads;
                if (payload?.enabled === false) {
                    stopDashboardInterval();
                    return;
                }
                if (typeof revision !== "string") return;
                leadRevisionFailures = 0;
                leadRevisionRetryAfter = 0;

                if (lastLeadRevision === null) {
                    lastLeadRevision = revision;
                    return;
                }
                if (revision !== lastLeadRevision) {
                    lastLeadRevision = revision;
                    await revalidateView(requestedUrl, ++latestNavigationId);
                }
            } catch (error) {
                // A transient freshness-service error must not break navigation.
                console.debug("Lead freshness check unavailable:", error.message);
                leadRevisionFailures += 1;
                leadRevisionRetryAfter = Date.now() + Math.min(
                    120000,
                    30000 * (2 ** Math.min(leadRevisionFailures - 1, 2))
                );
            } finally {
                clearTimeout(timeoutId);
                leadRevisionRequest = null;
            }
        })();
        return leadRevisionRequest;
    }

    function checkAndRevalidateActiveView() {
        const currentUrl = window.location.href;
        if (!isCacheableUrl(currentUrl)) return;

        if (isLeadResourceRoute(currentUrl)) {
            checkLeadResourceRevision();
            return;
        }

        const cached = FinloViewCache.get(currentUrl);
        if (cached) {
            const age = Date.now() - cached.timestamp;
            if (age > (cached.revalidateAfterMs ?? cached.ttl ?? 30000)) {
                revalidateView(currentUrl, ++latestNavigationId);
            }
        }
    }

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            checkAndRevalidateActiveView();
            startDashboardInterval();
        } else {
            stopDashboardInterval();
        }
    });

    // One active-view freshness scheduler. Lead/Dashboard pages use the small
    // revision endpoint; other eligible routes retain their existing SWR path.
    function startDashboardInterval() {
        stopDashboardInterval();
        checkAndRevalidateActiveView();
        dashboardInterval = setInterval(checkAndRevalidateActiveView, 30000);
    }

    function stopDashboardInterval() {
        if (dashboardInterval) {
            clearInterval(dashboardInterval);
            dashboardInterval = null;
        }
    }

    startDashboardInterval();
    window.addEventListener("online", checkAndRevalidateActiveView);
    window.addEventListener("focus", checkAndRevalidateActiveView);

    // --- Guaranteed Invalidation on Mutations ---
    function onMutationDetected() {
        pendingFreshUpdates.clear();
        FinloViewCache.clear();
    }

    // 1. Any non-GET HTMX request (POST, PUT, DELETE, PATCH)
    document.body.addEventListener("htmx:afterRequest", function (event) {
        const verb = (event.detail?.requestConfig?.verb || "").toUpperCase();
        if (verb && verb !== "GET") {
            onMutationDetected();
        }
    });

    // 2. Any native form submission
    document.addEventListener("submit", function (event) {
        onMutationDetected();
    });

    // 3. Custom mutation signals & authorization boundary invalidation
    document.addEventListener("finlo:data-mutated", onMutationDetected);
    document.addEventListener("finlo:invalidateCache", onMutationDetected);
    document.addEventListener("finlo:permissions-updated", onMutationDetected);
    document.addEventListener("finlo:role-changed", onMutationDetected);
    document.addEventListener("finlo:company-changed", onMutationDetected);

    // 4. Invalidate on company switch or logout link clicks
    document.addEventListener("click", function (event) {
        const target = event.target.closest("a[href*='switch-company'], a[href*='logout'], form[action*='logout'], a[href*='/auth/']");
        if (target) {
            onMutationDetected();
        }
    });

    // 5. Purge on logout or user switch via HTMX
    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const path = event.detail?.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path) || path.includes("switch-company")) {
            FinloViewCache.clear();
            window.sessionStorage?.removeItem("htmx-history-cache");
            window.localStorage?.removeItem("htmx-history-cache");
        }
    });

    document.addEventListener("submit", function (event) {
        if (event.target.matches("form[action*='logout']")) {
            FinloViewCache.clear();
            window.sessionStorage?.removeItem("htmx-history-cache");
            window.localStorage?.removeItem("htmx-history-cache");
        }
    }, true);
})();
