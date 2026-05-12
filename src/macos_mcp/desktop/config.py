# Bundle IDs for known browser applications
BROWSER_BUNDLE_IDS = {
    "com.apple.Safari",
    "com.google.Chrome",
    "org.mozilla.firefox",
    "com.microsoft.edgemac",
    "com.brave.Browser",
    "com.operasoftware.Opera",
    "com.vivaldi.Vivaldi",
    "company.thebrowser.Browser",  # Arc
}

# Bundle IDs for applications to exclude from window listing
EXCLUDED_BUNDLE_IDS = {
    "com.apple.finder",  # Finder (always running, often background)
}

# System UI apps to include in accessibility tree (whitelist).
# Use explicit bundle IDs instead of policy='Accessory' to avoid traversing
# helpers (Chrome Helper, Cursor Helper), agents (WallpaperAgent, talagent),
# and other accessory processes that add noise.
SYSTEM_UI_BUNDLE_IDS = {
    "com.apple.dock",  # Dock icons
    "com.apple.controlcenter",  # Control Centre panel
    "com.apple.systemuiserver",  # Menu bar extras (WiFi, battery, clock, etc.)
    "com.apple.Spotlight",
}
