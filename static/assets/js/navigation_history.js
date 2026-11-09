(function () {
    if (window._finloPageCacheInitialized) return;
    window._finloPageCacheInitialized = true;

    // --- In-Memory Page & Component Cache Store ---
    const cache = new Map();
    const MAX_ENTRIES = 150;

    function normalizeUrl(url) {
        if (!url) return "";
        try {
            const u = new URL(url, window.location.origin);
            return u.pathname + u.search;
        } catch (e) {
            return url;
        }
    }

    function buildCacheKey(url, target) {
        const norm = normalizeUrl(url);
        const cleanTarget = (target || "").replace(/^[#\.]/, "");
        return norm + "|" + cleanTarget;
    }

    function isCacheable(method, url) {
        if (method !== "GET") return false;
        if (!url) return false;

        const norm = normalizeUrl(url);
        // Exclude static assets
        if (norm.startsWith("/static/") || norm.includes("/assets/")) return false;
        // Exclude auth and session endpoints
        if (norm.includes("/login") || norm.includes("/logout")) return false;
        if (norm.includes("/reload_messages")) return false;
        if (norm.includes("/notifications/")) return false;
        if (norm.includes("/shortkeys/")) return false;
        if (norm.includes("/export") || norm.includes("/download")) return false;
        // Exclude live search input queries with active text
        if (/[\?\&]search=[^\&]+/.test(norm)) return false;

        return true;
    }

    const FinloPageCache = {
        get(url, target) {
            return cache.get(buildCacheKey(url, target));
        },
        set(url, target, data) {
            if (cache.size >= MAX_ENTRIES) {
                const firstKey = cache.keys().next().value;
                cache.delete(firstKey);
            }
            cache.set(buildCacheKey(url, target), data);
        },
        has(url, target) {
            return cache.has(buildCacheKey(url, target));
        },
        clear() {
            cache.clear();
        },
        deleteUrl(url) {
            const norm = normalizeUrl(url);
            for (const key of cache.keys()) {
                if (key.startsWith(norm + "|")) {
                    cache.delete(key);
                }
            }
        },
        size() {
            return cache.size;
        }
    };
    window.FinloPageCache = FinloPageCache;

    // Invalidate cache when any data mutation occurs
    function onMutationComplete(status) {
        if (status >= 200 && status < 400) {
            FinloPageCache.clear();
        }
    }

    // Intercept XMLHttpRequest for instant 0ms single-load navigation
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;

    XMLHttpRequest.prototype.open = function (method, url, async, user, password) {
        this._pageCacheMethod = (method || "GET").toUpperCase();
        this._pageCacheUrl = url;
        this._pageCacheHeaders = {};
        return origOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
        if (this._pageCacheHeaders && header) {
            this._pageCacheHeaders[header.toLowerCase()] = value;
        }
        return origSetHeader.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function (body) {
        const method = this._pageCacheMethod || "GET";
        const url = this._pageCacheUrl;
        const target = this._pageCacheHeaders?.["hx-target"] || "";

        if (method !== "GET") {
            // Any create, edit, or delete clears the cache to keep data fresh
            this.addEventListener("load", () => onMutationComplete(this.status));
            return origSend.apply(this, arguments);
        }

        // If this page/component was already loaded once, serve instantly from cache
        if (isCacheable(method, url) && FinloPageCache.has(url, target)) {
            const cached = FinloPageCache.get(url, target);
            const self = this;

            setTimeout(() => {
                try {
                    Object.defineProperty(self, "readyState", { value: 4, writable: true, configurable: true });
                    Object.defineProperty(self, "status", { value: cached.status || 200, writable: true, configurable: true });
                    Object.defineProperty(self, "statusText", { value: cached.statusText || "OK", writable: true, configurable: true });
                    Object.defineProperty(self, "responseText", { value: cached.responseText, writable: true, configurable: true });
                    Object.defineProperty(self, "response", { value: cached.responseText, writable: true, configurable: true });
                    if (cached.responseURL) {
                        Object.defineProperty(self, "responseURL", { value: cached.responseURL, writable: true, configurable: true });
                    }

                    self.getAllResponseHeaders = function () {
                        return cached.allHeaders || "content-type: text/html; charset=utf-8\r\n";
                    };
                    self.getResponseHeader = function (name) {
                        return cached.headersMap?.[name.toLowerCase()] || null;
                    };

                    self.dispatchEvent(new Event("readystatechange"));
                    self.dispatchEvent(new ProgressEvent("loadstart"));
                    self.dispatchEvent(new ProgressEvent("load", { lengthComputable: true, loaded: cached.responseText.length, total: cached.responseText.length }));
                    self.dispatchEvent(new ProgressEvent("loadend", { lengthComputable: true, loaded: cached.responseText.length, total: cached.responseText.length }));

                    if (typeof self.onload === "function") {
                        self.onload();
                    }
                } catch (e) {
                    console.error("FinloPageCache replay error:", e);
                }
            }, 0);
            return;
        }

        // Not in cache: fetch from server and cache for all future visits
        this.addEventListener("load", () => {
            if (this.status === 200 && isCacheable(method, url)) {
                const allHeaders = this.getAllResponseHeaders() || "";
                const headersMap = {};
                allHeaders.split("\r\n").forEach((line) => {
                    const idx = line.indexOf(":");
                    if (idx > 0) {
                        headersMap[line.slice(0, idx).trim().toLowerCase()] = line.slice(idx + 1).trim();
                    }
                });

                FinloPageCache.set(url, target, {
                    status: this.status,
                    statusText: this.statusText,
                    responseText: this.responseText,
                    allHeaders: allHeaders,
                    headersMap: headersMap,
                    responseURL: this.responseURL || url,
                });
            }
        });

        return origSend.apply(this, arguments);
    };

    // Monitor window.fetch for mutations as well
    if (window.fetch) {
        const origFetch = window.fetch;
        window.fetch = function (resource, options) {
            const method = (options?.method || "GET").toUpperCase();
            if (method !== "GET") {
                return origFetch.apply(this, arguments).then((res) => {
                    if (res.ok) onMutationComplete(res.status);
                    return res;
                });
            }
            return origFetch.apply(this, arguments);
        };
    }

    // Active sidebar section styling
    function setActiveSectionFromPath(path) {
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
    }

    document.addEventListener("htmx:afterSwap", function (event) {
        setActiveSectionFromPath(window.location.href);
    });

    document.addEventListener("htmx:historyRestore", function (event) {
        setActiveSectionFromPath(event.detail?.path || window.location.href);
    });

    document.body?.addEventListener("htmx:beforeRequest", function (event) {
        const path = event.detail.pathInfo?.requestPath || "";
        if (/\/logout\/?$/.test(path)) {
            FinloPageCache.clear();
        }
    });
})();
