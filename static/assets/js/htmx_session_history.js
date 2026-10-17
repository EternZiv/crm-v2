(function () {
    const historyCacheKey = "htmx-history-cache";
    const activeUserKey = "finlo-history-cache-user";
    const activeScopeKey = "finlo-history-cache-scope";
    const persistentStorage = window.localStorage;
    const tabStorage = window.sessionStorage;

    persistentStorage.removeItem(historyCacheKey);

    const localStorageForTab = new Proxy(persistentStorage, {
        get(target, property) {
            if (property === "getItem") {
                return (key) =>
                    key === historyCacheKey
                        ? tabStorage.getItem(key)
                        : target.getItem(key);
            }
            if (property === "setItem") {
                return (key, value) =>
                    key === historyCacheKey
                        ? tabStorage.setItem(key, value)
                        : target.setItem(key, value);
            }
            if (property === "removeItem") {
                return (key) =>
                    key === historyCacheKey
                        ? tabStorage.removeItem(key)
                        : target.removeItem(key);
            }
            if (property === "clear") {
                return () => {
                    target.clear();
                    tabStorage.removeItem(historyCacheKey);
                };
            }
            if (property === "length") {
                return new Set([
                    ...Array.from({ length: target.length }, (_, i) => target.key(i)),
                    ...(tabStorage.getItem(historyCacheKey) === null
                        ? []
                        : [historyCacheKey]),
                ]).size;
            }
            if (property === "key") {
                return (index) => {
                    const keys = [
                        ...Array.from(
                            { length: target.length },
                            (_, i) => target.key(i),
                        ).filter((key) => key !== historyCacheKey),
                        ...(tabStorage.getItem(historyCacheKey) === null
                            ? []
                            : [historyCacheKey]),
                    ];
                    return keys[index] ?? null;
                };
            }

            const value = Reflect.get(target, property, target);
            return typeof value === "function" ? value.bind(target) : value;
        },
        set(target, property, value) {
            if (property === historyCacheKey) {
                tabStorage.setItem(historyCacheKey, value);
                return true;
            }
            return Reflect.set(target, property, value, target);
        },
        deleteProperty(target, property) {
            if (property === historyCacheKey) {
                tabStorage.removeItem(historyCacheKey);
                return true;
            }
            return Reflect.deleteProperty(target, property);
        },
    });

    Object.defineProperty(window, "localStorage", {
        configurable: true,
        value: localStorageForTab,
    });

    function clearCacheWhenContextChanges() {
        const currentUser = document.body?.dataset.userId || "0";
        const currentScope = document.body?.dataset.companyScope || "none";
        const previousUser = tabStorage.getItem(activeUserKey);
        const previousScope = tabStorage.getItem(activeScopeKey);

        if (previousUser !== currentUser || previousScope !== currentScope) {
            tabStorage.removeItem(historyCacheKey);
        }

        tabStorage.setItem(activeUserKey, currentUser);
        tabStorage.setItem(activeScopeKey, currentScope);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            clearCacheWhenContextChanges,
            { once: true },
        );
    } else {
        clearCacheWhenContextChanges();
    }
})();
