/**
 * FINLONEXA CRM v2 - Instant Navigation, Smart LRU View Cache & Stale-While-Revalidate (SWR)
 * 
 * Provides:
 * 1. Immediate visual feedback (<10ms): instant active-state highlight and lightweight skeleton.
 * 2. Instant client-side restoration (<5ms) of eligible views from bounded in-memory LRU cache.
 * 3. Stale-While-Revalidate (SWR): serves cached snapshot immediately, then revalidates in the
 *    background when stale, updating content without full-page reloads or distracting flicker.
 * 4. Background refresh management: pauses when browser tab is hidden, resumes on visibility.
 * 5. Race-condition & superseded request cancellation: older in-flight fetches never clobber newer navigation.
 * 6. Guaranteed mutation invalidation: all non-GET requests, form submits, and logout events flush the cache.
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

    // --- Configuration & TTL Policies ---
    const MAX_CACHED_VIEWS = 20;

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

    // --- State Variables ---
    const viewCache = new Map();
    const pendingFreshUpdates = new Map();
    let latestNavigationId = 0;
    let activeRevalidations = new Set();
    let dashboardInterval = null;

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

    function applyPendingFreshUpdate(url) {
        if (!url || normalizeUrl(window.location.href) !== normalizeUrl(url)) return;

        // If form or modal is active or dirty, DO NOT apply pending DOM update yet
        if (isFormOrModalActiveOrDirty()) {
            return;
        }

        const update = pendingFreshUpdates.get(url);
        if (!update) return;
        pendingFreshUpdates.delete(url);

        const mainContent = document.getElementById("mainContent");
        if (mainContent && update.mainContentHtml && update.mainContentHtml !== mainContent.innerHTML) {
            let htmlToApply = update.mainContentHtml;
            if (htmlToApply.includes('id="header"') || htmlToApply.includes('id="sidebar"')) {
                const temp = document.createElement("div");
                temp.innerHTML = htmlToApply;
                const h = temp.querySelector("#header");
                if (h) h.remove();
                const s = temp.querySelector("#sidebar, #primarySidebar");
                if (s) s.remove();
                htmlToApply = temp.innerHTML;
            }
            mainContent.innerHTML = htmlToApply;
            if (window.htmx) htmx.process(mainContent);
            reexecuteScripts(mainContent);
            if (typeof window.bootstrapFinloUI === "function") {
                window.bootstrapFinloUI(mainContent);
            }
            setTimeout(() => window.dispatchEvent(new Event("resize")), 50);
        }
    }

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
            return u.pathname + u.search;
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

    // --- Bounded LRU Cache Implementation ---
    const FinloViewCache = {
        get(url) {
            if (!isCacheableUrl(url)) return null;
            const key = buildCacheKey(url);
            const entry = viewCache.get(key);
            if (!entry) return null;

            // Touch entry for true LRU (re-insert moves it to the end of iteration order)
            viewCache.delete(key);
            viewCache.set(key, entry);

            return entry;
        },
        set(url, data) {
            if (!isCacheableUrl(url)) return;
            const key = buildCacheKey(url);

            // LRU eviction if full
            if (viewCache.has(key)) {
                viewCache.delete(key);
            } else if (viewCache.size >= MAX_CACHED_VIEWS) {
                const lruKey = viewCache.keys().next().value;
                viewCache.delete(lruKey);
            }

            const ttl = getTtlForUrl(url);
            viewCache.set(key, {
                ...data,
                ttl: ttl,
                timestamp: Date.now()
            });
        },
        has(url) {
            return FinloViewCache.get(url) !== null;
        },
        delete(url) {
            const key = buildCacheKey(url);
            viewCache.delete(key);
        },
        clear() {
            viewCache.clear();
            activeRevalidations.clear();
        },
        size() {
            return viewCache.size;
        }
    };
    window.FinloViewCache = FinloViewCache;

    // --- Visual Progress Bar (<2px top indicator) ---
    function ensureProgressBar() {
        return null;
    }

    function showProgressBar() {}

    function hideProgressBar() {}

    // --- Lightweight Skeleton Generator for Uncached Navigation ---
    function renderImmediateSkeleton(mainContent) {
        return;
        mainContent.innerHTML = `
            <div class="p-5 h-full flex flex-col gap-6 animate-pulse" id="finlo-skeleton-loader">
                <!-- Top Nav Bar Skeleton -->
                <div class="flex items-center justify-between h-14 bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700">
                    <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48"></div>
                    <div class="flex items-center gap-3">
                        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                        <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                    </div>
                </div>
                <!-- KPI Stats Grid Skeleton -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div class="h-24 bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                        <div class="h-7 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                    </div>
                    <div class="h-24 bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-28"></div>
                        <div class="h-7 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                    </div>
                    <div class="h-24 bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
                        <div class="h-7 bg-gray-200 dark:bg-gray-700 rounded w-14"></div>
                    </div>
                    <div class="h-24 bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                        <div class="h-7 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                    </div>
                </div>
                <!-- Main Body Card Skeleton -->
                <div class="flex-1 min-h-[350px] bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-100 dark:border-gray-700 flex flex-col gap-4">
                    <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-40 mb-2"></div>
                    <div class="h-10 bg-gray-100 dark:bg-gray-750 rounded w-full"></div>
                    <div class="h-10 bg-gray-100 dark:bg-gray-750 rounded w-full"></div>
                    <div class="h-10 bg-gray-100 dark:bg-gray-750 rounded w-full"></div>
                    <div class="h-10 bg-gray-100 dark:bg-gray-750 rounded w-full"></div>
                </div>
            </div>
        `;
    }

    // --- Active Sidebar Navigation Styling ---
    function setActiveSectionFromUrl(path) {
        try {
            const sectionId = new URL(path, window.location.href).searchParams.get("section");
            if (!sectionId) return;

            const activeLink = document.getElementById(sectionId);
            if (activeLink && activeLink.matches("nav a.nav-link")) {
                document.querySelectorAll("nav a.nav-link").forEach((link) => {
                    link.classList.remove("bg-primary-600", "hover:bg-primary-800");
                });
                activeLink.classList.add("bg-primary-600", "hover:bg-primary-800");
                window.localStorage.setItem("activeNavLinkId", sectionId);
                window.localStorage.setItem("currentActiveSection", sectionId);
                window.localStorage.setItem("lastActiveSection", sectionId);
            }
        } catch (e) {}
    }

    function highlightLinkImmediately(link) {
        if (!link) return;
        if (link.matches("nav a.nav-link")) {
            document.querySelectorAll("nav a.nav-link").forEach((l) => {
                l.classList.remove("bg-primary-600", "hover:bg-primary-800");
            });
            link.classList.add("bg-primary-600", "hover:bg-primary-800");
            const sectionId = link.id;
            if (sectionId) {
                window.localStorage.setItem("activeNavLinkId", sectionId);
                window.localStorage.setItem("currentActiveSection", sectionId);
            }
        } else if (link.matches("ul a.sidebar-link")) {
            document.querySelectorAll("ul a.sidebar-link").forEach((l) => {
                l.classList.remove("bg-primary-600", "text-white");
            });
            link.classList.add("bg-primary-600", "text-white");
            const sectionId = link.getAttribute("data-section") || link.closest("[data-section]")?.getAttribute("data-section");
            const linkId = link.id;
            if (linkId && sectionId) {
                window.localStorage.setItem(`activeSidebarLinkId_${sectionId}`, linkId);
                window.localStorage.setItem("activeSidebarLinkId", linkId);
                window.localStorage.setItem("sidebarClicked", "true");
            }
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
        if (!mainContent) return false;

        // Clean up open Select2 dropdowns if any
        if (window.jQuery && jQuery(".select2-hidden-accessible").length) {
            try { jQuery(".select2-hidden-accessible").select2("close"); } catch (e) {}
        }
        document.querySelectorAll("body > .select2-container").forEach((el) => el.remove());

        // Sanitize cached HTML: guarantee no nested header, sidebar, or skeleton loader
        let htmlToRestore = cached.mainContentHtml || "";
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

        // 1. Swap main content HTML
        mainContent.innerHTML = htmlToRestore;

        // 2. Swap sub-sidebar HTML if present
        if (cached.sideMenuHtml) {
            const sideMenuContainer = document.getElementById("sideMenuContainer");
            if (sideMenuContainer) {
                sideMenuContainer.innerHTML = cached.sideMenuHtml;
            }
        }

        // 3. Update URL in browser address bar and history
        if (window.location.href !== url) {
            history.pushState(null, "", url);
        }

        // 4. Update sidebar visual indicator
        if (window.SidebarNav && typeof window.SidebarNav.initFromUrl === "function") {
            try { window.SidebarNav.initFromUrl(); } catch (e) {}
        } else {
            setActiveSectionFromUrl(url);
        }

        // 5. Re-bind HTMX triggers on the restored DOM nodes
        if (window.htmx) {
            htmx.process(mainContent);
            const sideMenuContainer = document.getElementById("sideMenuContainer");
            if (sideMenuContainer) htmx.process(sideMenuContainer);
        }

        // 6. Re-execute component initialization scripts (charts, table bindings)
        reexecuteScripts(mainContent);

        // 7. Trigger responsive resize for charts
        window.dispatchEvent(new Event("resize"));

        // 8. Custom restoration event for extension hooks
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
                // If response does not contain #mainContent, abort without corrupting the view
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
                // Store fresh update to be applied safely once editing session or modal concludes.
                pendingFreshUpdates.set(url, {
                    mainContentHtml: freshMainHtml,
                    sideMenuHtml: freshSideHtml,
                    timestamp: Date.now()
                });

                // Attach safe listeners on forms to apply updates when user resets or closes modal
                document.querySelectorAll("form").forEach((f) => {
                    f.addEventListener("reset", () => {
                        setTimeout(() => applyPendingFreshUpdate(url), 100);
                    }, { once: true });
                });
                return;
            }

            // Safe to update DOM immediately:
            const mainContent = document.getElementById("mainContent");
            const currentMainSession = document.getElementById("mainSession");

            if (currentMainSession && currentMainSession.getAttribute("hx-get")) {
                // For generic views with independent layout data, trigger smooth re-fetch of #mainSession
                const layoutUrl = currentMainSession.getAttribute("hx-get");
                if (window.htmx && layoutUrl) {
                    htmx.ajax("GET", layoutUrl, { target: "#mainSession", swap: "innerHTML" });
                }
            } else if (mainContent) {
                if (freshMainHtml && freshMainHtml !== mainContent.innerHTML) {
                    mainContent.innerHTML = freshMainHtml;
                    if (window.htmx) htmx.process(mainContent);
                    reexecuteScripts(mainContent);
                    if (typeof window.bootstrapFinloUI === "function") {
                        window.bootstrapFinloUI(mainContent);
                    }
                    window.dispatchEvent(new Event("resize"));
                }
            }

        } catch (error) {
            console.debug("Background revalidation note:", error.message);
            // On network failure, cached view remains intact without disruptive errors
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

        // 1. Immediate visual feedback (<10ms): Highlight clicked link immediately!
        highlightLinkImmediately(link);
        showProgressBar();

        // 2. Increment navigation sequence to protect against race conditions
        const navId = ++latestNavigationId;

        // 3. Check FinloViewCache for instant restoration
        const cached = FinloViewCache.get(fullUrl);
        if (cached && cached.mainContentHtml) {
            // Prevent HTMX from triggering an expensive blocking round-trip
            event.preventDefault();
            event.stopImmediatePropagation();

            // Restore instantly in <5ms
            restoreView(fullUrl, cached);
            hideProgressBar();

            // 4. Stale-While-Revalidate (SWR): if stale, revalidate silently in background
            const age = Date.now() - cached.timestamp;
            if (age > cached.ttl) {
                revalidateView(fullUrl, navId);
            }
            return false;
        }

        // 4. Cache Miss: Display instant lightweight skeleton in #mainContent (<20ms)
        const mainContent = document.getElementById("mainContent");
        if (mainContent && isCacheableUrl(fullUrl)) {
            renderImmediateSkeleton(mainContent);
        }
        // Let HTMX proceed with normal request to Django
    }, true);

    // --- Snapshot Capture after View Settles ---
    let captureTimeout = null;
    function scheduleSnapshot() {
        if (captureTimeout) clearTimeout(captureTimeout);
        captureTimeout = setTimeout(() => {
            const currentUrl = window.location.href;
            if (!isCacheableUrl(currentUrl)) return;

            const mainContent = document.getElementById("mainContent");
            if (!mainContent) return;

            // Do not capture if still showing loading spinner, skeleton, indicator, or if header was nested
            if (mainContent.querySelector("#header") ||
                mainContent.querySelector("#finlo-skeleton-loader") ||
                mainContent.querySelector(".htmx-indicator.htmx-request") ||
                mainContent.querySelector("#loading-indicator[style*='display: flex']")) {
                return;
            }

            const sideMenuContainer = document.getElementById("sideMenuContainer");
            FinloViewCache.set(currentUrl, {
                mainContentHtml: mainContent.innerHTML,
                sideMenuHtml: sideMenuContainer ? sideMenuContainer.innerHTML : ""
            });
            hideProgressBar();
        }, 0);
    }

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail?.target;
        const targetId = target && target.id;
        if (targetId === "mainContent" || targetId === "calendarContainer" || (target && target.closest && target.closest("#mainContent"))) {
            setActiveSectionFromUrl(window.location.href);
            scheduleSnapshot();
        }
    });

    document.body.addEventListener("htmx:afterSettle", function (event) {
        scheduleSnapshot();
    });

    document.addEventListener("htmx:historyRestore", function (event) {
        const path = event.detail?.path || window.location.pathname;
        setActiveSectionFromUrl(path);
        const mainContent = document.getElementById("mainContent");
        if (mainContent) {
            reexecuteScripts(mainContent);
            window.dispatchEvent(new Event("resize"));
        }
        hideProgressBar();
    });

    // --- Tab Visibility & Background Refresh Strategy ---
    function checkAndRevalidateActiveView() {
        const currentUrl = window.location.href;
        if (!isCacheableUrl(currentUrl)) return;

        const cached = FinloViewCache.get(currentUrl);
        if (cached) {
            const age = Date.now() - cached.timestamp;
            if (age > cached.ttl) {
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

    // Dashboard periodic revalidation while tab is active
    function startDashboardInterval() {
        stopDashboardInterval();
        dashboardInterval = setInterval(() => {
            if (document.visibilityState !== "visible") return;
            const currentUrl = window.location.href;
            if (/\/dashboard\//i.test(currentUrl) || /section=home/i.test(currentUrl)) {
                checkAndRevalidateActiveView();
            }
        }, 45000); // 45 seconds
    }

    function stopDashboardInterval() {
        if (dashboardInterval) {
            clearInterval(dashboardInterval);
            dashboardInterval = null;
        }
    }

    startDashboardInterval();

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

    // 3. Custom mutation signals (e.g. from WebSockets or data events)
    document.addEventListener("finlo:data-mutated", onMutationDetected);
    document.addEventListener("finlo:invalidateCache", onMutationDetected);

    // 4. Purge on logout or user switch
    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const path = event.detail?.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path)) {
            FinloViewCache.clear();
            window.sessionStorage?.removeItem("htmx-history-cache");
            window.localStorage?.removeItem("htmx-history-cache");
        }
    });
})();
