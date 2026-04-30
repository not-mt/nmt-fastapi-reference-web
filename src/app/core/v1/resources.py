# -*- coding: utf-8 -*-
# Copyright (c) 2026. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""
Resource configurations and navigation items for the web UI.

Defines the data-driven field layouts, accent palettes, and sidebar
navigation entries consumed by reusable Jinja2 templates.
"""

from nmtfast.htmx.v1.schemas import (
    AccentPalette,
    FieldConfig,
    NavItem,
    ResourceConfig,
    SettingsSection,
)

WIDGET_RESOURCE_CONFIG: ResourceConfig = ResourceConfig(
    name="Widget",
    name_plural="Widgets",
    base_url="/ui/v1/widgets",
    id_field="id",
    id_type="int",
    display_name_field="name",
    has_zap=True,
    panel_width=28,
    accent=AccentPalette(
        shade_50="#fff7ed",
        shade_100="#ffedd5",
        shade_500="#f97316",
        shade_600="#ea580c",
    ),
    fields=[
        FieldConfig(
            name="id",
            label="ID",
            field_type="display_only",
            is_id=True,
            show_in_form=False,
        ),
        FieldConfig(
            name="name",
            label="Name",
            required=True,
            is_name=True,
            placeholder="Widget name",
        ),
        FieldConfig(
            name="height",
            label="Height",
            placeholder="e.g. 10.5",
        ),
        FieldConfig(
            name="mass",
            label="Mass",
            placeholder="e.g. 2.3",
        ),
        FieldConfig(
            name="force",
            label="Force",
            field_type="number",
            placeholder="e.g. 42",
        ),
    ],
)

GADGET_RESOURCE_CONFIG: ResourceConfig = ResourceConfig(
    name="Gadget",
    name_plural="Gadgets",
    base_url="/ui/v1/gadgets",
    id_field="id",
    display_name_field="name",
    has_zap=True,
    panel_width=36,
    accent=AccentPalette(
        shade_50="#ecfdf5",
        shade_100="#d1fae5",
        shade_500="#10b981",
        shade_600="#059669",
    ),
    fields=[
        FieldConfig(
            name="id",
            label="ID",
            field_type="display_only",
            is_id=True,
            show_in_form=False,
            monospace=True,
            truncate=8,
        ),
        FieldConfig(
            name="name",
            label="Name",
            required=True,
            is_name=True,
            placeholder="Gadget name",
        ),
        FieldConfig(
            name="height",
            label="Height",
            placeholder="e.g. 10.5",
        ),
        FieldConfig(
            name="mass",
            label="Mass",
            placeholder="e.g. 2.3",
        ),
        FieldConfig(
            name="force",
            label="Force",
            field_type="number",
            placeholder="e.g. 42",
        ),
    ],
)

# SVG icon markup for sidebar navigation items (Feather icon style)
_ICON_DASHBOARD: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7"/>'
    '<rect x="14" y="3" width="7" height="7"/>'
    '<rect x="3" y="14" width="7" height="7"/>'
    '<rect x="14" y="14" width="7" height="7"/>'
    "</svg>"
)

_ICON_WIDGETS: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round">'
    '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3'
    ' 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
    "</svg>"
)

_ICON_GADGETS: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83'
    " 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1"
    " 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65"
    " 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65"
    " 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1"
    " 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0"
    " 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0"
    " 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51"
    " 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65"
    " 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2"
    ' 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
    "</svg>"
)

_ICON_PROFILE: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/>'
    "</svg>"
)

NAV_ITEMS: list[NavItem] = [
    NavItem(
        label="Dashboard",
        url="/ui/v1/dashboard",
        icon_svg=_ICON_DASHBOARD,
        match_prefix="/ui/v1/dashboard",
    ),
    NavItem(
        label="Widgets",
        url="/ui/v1/widgets",
        icon_svg=_ICON_WIDGETS,
        match_prefix="/ui/v1/widgets",
    ),
    NavItem(
        label="Gadgets",
        url="/ui/v1/gadgets",
        icon_svg=_ICON_GADGETS,
        match_prefix="/ui/v1/gadgets",
    ),
]

# SVG icon for the General settings section (Feather "sliders" style)
_ICON_SETTINGS_GENERAL: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round">'
    '<line x1="4" y1="21" x2="4" y2="14"/>'
    '<line x1="4" y1="10" x2="4" y2="3"/>'
    '<line x1="12" y1="21" x2="12" y2="12"/>'
    '<line x1="12" y1="8" x2="12" y2="3"/>'
    '<line x1="20" y1="21" x2="20" y2="16"/>'
    '<line x1="20" y1="12" x2="20" y2="3"/>'
    '<line x1="1" y1="14" x2="7" y2="14"/>'
    '<line x1="9" y1="8" x2="15" y2="8"/>'
    '<line x1="17" y1="16" x2="23" y2="16"/>'
    "</svg>"
)

SETTINGS_SECTIONS: list[SettingsSection] = [
    SettingsSection(
        label="General",
        url="/ui/v1/settings/general",
        icon_svg=_ICON_SETTINGS_GENERAL,
        active=True,
    ),
]
