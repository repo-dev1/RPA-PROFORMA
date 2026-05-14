"""
Style constants for the RPA Proforma GUI application.
"""

# ── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    # Primary ACONIC blue tones
    "primary": "#1B3A5C",
    "primary_dark": "#0F2744",
    "primary_light": "#2A5580",
    "primary_hover": "#1E4A73",

    # Accent
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",

    # Success / Error / Warning
    "success": "#10B981",
    "success_bg": "#D1FAE5",
    "error": "#EF4444",
    "error_bg": "#FEE2E2",
    "warning": "#F59E0B",
    "warning_bg": "#FEF3C7",

    # Neutral
    "bg_dark": "#1A1A2E",
    "bg_card": "#16213E",
    "bg_input": "#0F3460",
    "surface": "#1E293B",
    "surface_hover": "#334155",

    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",

    "border": "#334155",
    "border_light": "#475569",

    "table_header": "#1F4E79",
    "table_row_even": "#1E293B",
    "table_row_odd": "#0F172A",
    "table_selected": "#1E40AF",
}

# ── Font Configuration ───────────────────────────────────────────────────────
FONTS = {
    "title": ("Segoe UI", 20, "bold"),
    "subtitle": ("Segoe UI", 14, "bold"),
    "heading": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 11),
    "body_bold": ("Segoe UI", 11, "bold"),
    "small": ("Segoe UI", 9),
    "small_bold": ("Segoe UI", 9, "bold"),
    "mono": ("Consolas", 10),
}

# ── Dimensions ───────────────────────────────────────────────────────────────
DIMENSIONS = {
    "window_width": 1200,
    "window_height": 800,
    "padding": 15,
    "padding_small": 8,
    "corner_radius": 10,
    "button_height": 36,
    "entry_height": 36,
}

# ── Supplier Colors (for visual distinction) ────────────────────────────────
SUPPLIER_COLORS = {
    "MASTERTEC": "#3B82F6",   # Blue
    "CONICO": "#10B981",      # Green
    "COMTECH": "#F59E0B",     # Amber
    "SEVASA": "#8B5CF6",      # Purple
}
