import { Router } from "express";

export const configRouter = Router();

// Shared, global application cache.
// In Node.js, exported objects are singletons cached by require/import.
const AppConfig = {
    theme: "light",
    features: {
        newCheckout: true,
        betaAccess: false
    }
};

configRouter.get("/theme", (req, res) => {
    // 1. We grab a reference to the global object
    const currentConfig = AppConfig;
    
    // 2. We extract a query param specifically designed to test theme overwrites
    const forceDark = req.query.forceDark as string | undefined;

    // ✨ BUG 5 ✨
    // Prototype Pollution / Shared Object Mutation
    // The developer meant to conditionally apply a dark theme for THIS response only.
    // Instead, they mutated the global AppConfig. Every request after this will crash
    // if forceDark passed is something stupid, because it poisons the cache.
    if (forceDark) {
        // TypeScript bypass: forced mutation via 'any' matching the user's specific instruction to bypass 'tsc'
        (currentConfig.theme as any) = forceDark;
    }

    // Now we use a strict method that expects EXACTLY 'light' or 'dark'
    // If currentConfig.theme was poisoned with 'bad_string', this throws.
    if (currentConfig.theme !== "light" && currentConfig.theme !== "dark") {
        throw new TypeError(`Invalid theme setting detected in application cache: ${currentConfig.theme}. Expected 'light' or 'dark'.`);
    }

    res.json({
        activeTheme: currentConfig.theme,
        message: "Config loaded successfully"
    });
});
