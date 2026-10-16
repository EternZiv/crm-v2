(function () {
    const historyCacheKey = "htmx-history-cache";
    const activeUserKey = "horilla-history-cache-user";
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

    function clearCacheWhenUserChanges() {
        const currentUser = document.body?.dataset.userId || "0";
        const previousUser = tabStorage.getItem(activeUserKey);

        if (previousUser !== null && previousUser !== currentUser) {
            tabStorage.removeItem(historyCacheKey);
        }

        tabStorage.setItem(activeUserKey, currentUser);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            clearCacheWhenUserChanges,
            { once: true },
        );
    } else {
        clearCacheWhenUserChanges();
    }
})();
