(function () {
    "use strict";

    const storageKey = "pilatovic-theme";
    const root = document.documentElement;
    const toggle = document.querySelector(".site-theme-toggle");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

    function storedTheme() {
        try {
            return localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }

    function storeTheme(theme) {
        try {
            localStorage.setItem(storageKey, theme);
        } catch (error) {
            // The selected mode still applies for this page if storage is blocked.
        }
    }

    function preferredTheme() {
        const savedTheme = storedTheme();
        if (savedTheme === "light" || savedTheme === "dark") {
            return savedTheme;
        }
        return systemDark.matches ? "dark" : "light";
    }

    function applyTheme(theme) {
        root.setAttribute("data-bs-theme", theme);

        if (!toggle) {
            return;
        }

        const isDark = theme === "dark";
        const icon = toggle.querySelector("i");
        toggle.setAttribute(
            "aria-label",
            isDark ? "Přepnout na světlý režim" : "Přepnout na tmavý režim"
        );
        toggle.setAttribute(
            "title",
            isDark ? "Přepnout na světlý režim" : "Přepnout na tmavý režim"
        );

        if (icon) {
            icon.classList.toggle("fa-moon", !isDark);
            icon.classList.toggle("fa-sun", isDark);
        }
    }

    applyTheme(preferredTheme());

    if (toggle) {
        toggle.addEventListener("click", function () {
            const nextTheme = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            storeTheme(nextTheme);
            applyTheme(nextTheme);
        });
    }

    systemDark.addEventListener("change", function () {
        if (!storedTheme()) {
            applyTheme(preferredTheme());
        }
    });
})();
