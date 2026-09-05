// Executed by ThemeScriptTests in an isolated headless browser.
// Each case gets fresh DOM/storage doubles and runs the actual production file.
function themeEnvironment({saved = null, dark = false, blocked = false, button = true, icon = true} = {}) {
    const attributes = {};
    const buttonAttributes = {};
    const classes = new Set();
    const events = {};
    const preference = {matches: dark, addEventListener: (name, callback) => { events[name] = callback; }};
    const storage = {
        getItem(key) { if (blocked) throw new Error("Storage blocked"); return saved; },
        setItem(key, value) { if (blocked) throw new Error("Storage blocked"); saved = value; },
    };
    const toggle = {
        setAttribute: (key, value) => { buttonAttributes[key] = value; },
        querySelector: () => icon ? {classList: {toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); }}} : null,
        addEventListener: (name, callback) => { events[name] = callback; },
    };
    const document = {
        documentElement: {
            setAttribute: (key, value) => { attributes[key] = value; },
            getAttribute: key => attributes[key],
        },
        querySelector: () => button ? toggle : null,
    };
    new Function("document", "window", "localStorage", themeSource)(
        document, {matchMedia: () => preference}, storage
    );
    return {
        theme: () => attributes["data-bs-theme"],
        saved: () => saved,
        label: () => buttonAttributes["aria-label"],
        title: () => buttonAttributes.title,
        classes,
        click: () => events.click(),
        systemChange(value) { preference.matches = value; events.change(); },
    };
}

const results = [];
function check(condition, message) { if (!condition) throw new Error(message); }
function test(name, callback) {
    try { callback(); results.push({name, passed: true}); }
    catch (error) { results.push({name, passed: false, error: String(error)}); }
}

test("defaults to the system preference", () => {
    check(themeEnvironment().theme() === "light", "Light system preference");
    check(themeEnvironment({dark: true}).theme() === "dark", "Dark system preference");
});
test("saved preference overrides the system", () => {
    check(themeEnvironment({saved: "light", dark: true}).theme() === "light", "Saved light");
    check(themeEnvironment({saved: "dark"}).theme() === "dark", "Saved dark");
});
test("unknown saved value falls back to the system on load", () => {
    check(themeEnvironment({saved: "invalid", dark: true}).theme() === "dark", "Invalid saved preference");
});
test("click toggles and persists both directions", () => {
    const env = themeEnvironment();
    env.click();
    check(env.theme() === "dark" && env.saved() === "dark", "Persist dark");
    env.click();
    check(env.theme() === "light" && env.saved() === "light", "Persist light");
});
test("button label title and icon track the selected theme", () => {
    const env = themeEnvironment();
    check(env.label() === "Přepnout na tmavý režim" && env.title() === env.label(), "Light label");
    check(env.classes.has("fa-moon") && !env.classes.has("fa-sun"), "Light icon");
    env.click();
    check(env.label() === "Přepnout na světlý režim" && env.title() === env.label(), "Dark label");
    check(env.classes.has("fa-sun") && !env.classes.has("fa-moon"), "Dark icon");
});
test("system changes apply when no preference was saved", () => {
    const env = themeEnvironment();
    env.systemChange(true);
    check(env.theme() === "dark", "Follow dark system");
    env.systemChange(false);
    check(env.theme() === "light", "Follow light system");
});
test("system changes preserve an explicit preference", () => {
    const env = themeEnvironment({saved: "light"});
    env.systemChange(true);
    check(env.theme() === "light", "Keep saved preference");
    env.click();
    env.systemChange(false);
    check(env.theme() === "dark", "Keep clicked preference");
});
test("blocked storage still permits toggling and system updates", () => {
    const env = themeEnvironment({blocked: true});
    env.click();
    check(env.theme() === "dark", "Toggle without storage");
    env.systemChange(false);
    check(env.theme() === "light", "System without storage");
});
test("pages without a toggle still get the preferred theme", () => {
    const env = themeEnvironment({button: false, dark: true});
    check(env.theme() === "dark", "Initial theme without button");
    env.systemChange(false);
    check(env.theme() === "light", "System update without button");
});
test("a missing icon does not break the toggle", () => {
    const env = themeEnvironment({icon: false});
    env.click();
    check(env.theme() === "dark", "Toggle without icon");
});
document.body.textContent = JSON.stringify(results);
