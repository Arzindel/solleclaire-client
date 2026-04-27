"""
Desktop AT-SPI capture module.
Sources desktop state via Atspi (GObject Introspection) for the Reader.
"""

import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi
import json
from typing import Any


def get_desktop_state(max_depth: int = 3) -> dict[str, Any]:
    """
    Capture the current desktop state from AT-SPI.

    Returns a dictionary with:
    - desktop_name: name of the desktop
    - applications: list of running applications with their windows and elements

    Args:
        max_depth: How deep to recurse into element trees (default 3)
    """
    desktop = Atspi.get_desktop(0)

    state = {
        'desktop': {
            'name': desktop.name,
            'role': desktop.get_role_name(),
        },
        'applications': [],
    }

    # Iterate through applications
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue

        app_info = _extract_application(app, max_depth=max_depth)
        if app_info['windows']:
            state['applications'].append(app_info)

    return state


def get_application_windows(app_name: str | None = None) -> list[dict[str, Any]]:
    """
    Get windows for a specific application or all windows.
    
    Args:
        app_name: Application name to filter by (optional)
    
    Returns:
        List of window dictionaries with name, role, extents
    """
    desktop = Atspi.get_desktop(0)
    windows = []
    
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue
        
        if app_name and app.get_name() != app_name:
            continue
            
        # Get windows for this app
        for j in range(app.get_child_count()):
            win = app.get_child_at_index(j)
            if not win:
                continue
            
            win_data = _extract_window(win)
            if win_data:
                win_data['application'] = app.get_name()
                windows.append(win_data)
    
    return windows


def get_focused_element() -> dict[str, Any] | None:
    """
    Get the currently focused element.

    Returns:
        Dictionary with focused element info, or None if nothing focused
    """
    desktop = Atspi.get_desktop(0)

    def find_focused(parent: Any, depth: int = 0, max_depth: int = 15) -> Any | None:
        """Recursively search for element with FOCUSED state."""
        if depth > max_depth:
            return None

        try:
            states = parent.get_state_set()
            if states.contains(Atspi.StateType.FOCUSED):
                return parent
        except Exception:
            pass

        try:
            child_count = parent.get_child_count()
        except Exception:
            return None

        for i in range(child_count):
            try:
                child = parent.get_child_at_index(i)
            except Exception:
                continue

            if not child:
                continue

            result = find_focused(child, depth + 1, max_depth)
            if result:
                return result

        return None

    # First, find the ACTIVE window
    active_window = None
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue

        for j in range(app.get_child_count()):
            win = app.get_child_at_index(j)
            if not win:
                continue

            try:
                states = win.get_state_set()
                if states.contains(Atspi.StateType.ACTIVE):
                    active_window = win
                    break
            except Exception:
                pass

        if active_window:
            break

    # Search in ACTIVE window first
    if active_window:
        focused = find_focused(active_window)
        if focused:
            return _extract_element(focused)

    # Fallback: search all windows
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if not app:
            continue

        for j in range(app.get_child_count()):
            win = app.get_child_at_index(j)
            if not win:
                continue

            focused = find_focused(win)
            if focused:
                return _extract_element(focused)

    return None


# --- Private helpers ---

def _extract_application(app: Any, max_depth: int = 3) -> dict[str, Any]:
    """Extract application info and its windows."""
    # Get application ID as string
    try:
        app_id = app.get_application()
        app_id_str = str(app_id) if app_id else ''
    except Exception:
        app_id_str = ''

    app_info = {
        'name': app.get_name(),
        'role': app.get_role_name(),
        'application_id': app_id_str,
        'windows': [],
    }

    # Get children (windows)
    for j in range(app.get_child_count()):
        win = app.get_child_at_index(j)
        if not win:
            continue

        win_data = _extract_window(win, max_depth=max_depth)
        if win_data:
            app_info['windows'].append(win_data)

    return app_info


def _extract_window(win: Any, max_depth: int = 3) -> dict[str, Any] | None:
    """Extract window info and its element tree."""
    name = win.get_name()
    # Skip unnamed windows
    if not name or name == '':
        return None

    # Get window geometry
    try:
        extents = win.get_extents(0)  # 0 = window coords
        geometry = {
            'x': extents.x,
            'y': extents.y,
            'width': extents.width,
            'height': extents.height,
        }
    except Exception:
        geometry = None

    # Get states
    states = _extract_states(win)

    # Recursively extract children
    children = _extract_children(win, current_depth=1, max_depth=max_depth)

    return {
        'name': name,
        'role': win.get_role_name(),
        'geometry': geometry,
        'states': states,
        'children': children,
    }


def _extract_element(element: Any) -> dict[str, Any]:
    """Extract element info for any accessible element."""
    return {
        'name': element.get_name(),
        'role': element.get_role_name(),
        'description': element.get_description(),
        'states': _extract_states(element),
    }


def _extract_children(parent: Any, current_depth: int, max_depth: int) -> list[dict[str, Any]]:
    """Recursively extract children up to max_depth."""
    if current_depth > max_depth:
        return []

    children = []
    try:
        child_count = parent.get_child_count()
    except Exception:
        return []

    for i in range(child_count):
        try:
            child = parent.get_child_at_index(i)
        except Exception:
            continue

        if not child:
            continue

        # Skip null/empty names
        name = child.get_name()
        role = child.get_role_name()

        # Build element info
        element_info = {
            'name': name,
            'role': role,
        }

        # Add description if non-empty
        try:
            desc = child.get_description()
            if desc and desc.strip():
                element_info['description'] = desc
        except Exception:
            pass

        # Add geometry if available (try component interface)
        try:
            comp = child.get_component_iface()
            if comp:
                extents = comp.get_extents(0)
                element_info['geometry'] = {
                    'x': extents.x,
                    'y': extents.y,
                    'width': extents.width,
                    'height': extents.height,
                }
        except Exception:
            pass

        # Add states
        element_info['states'] = _extract_states(child)

        # Add text content if element has text (limited)
        try:
            text_iface = child.get_text_iface()
            if text_iface:
                text = text_iface.get_text(0, 100)  # First 100 chars
                if text and text.strip():
                    element_info['text'] = text.strip()[:500]
        except Exception:
            pass

        # Recurse into children
        element_info['children'] = _extract_children(child, current_depth + 1, max_depth)
        if not element_info['children']:
            del element_info['children']

        children.append(element_info)

    return children


def _extract_states(obj: Any) -> dict[str, bool]:
    """Extract states from an accessible object."""
    try:
        state_set = obj.get_state_set()
        states = {}
        # Iterate through known state names
        for state_name in [
            'active', 'armed', 'busy', 'checked', 'collapsed',
            'defunct', 'editable', 'enabled', 'expandable', 'expanded',
            'focused', 'grabbed', 'hidden', 'invalid', 'invalid_entry',
            'modal', 'multi_line', 'multiselectable', 'окий',
            'pressed', 'required', 'resizable', 'selectable', 'selected',
            'sensitive', 'showing', 'single_line', 'sticky', 'transient',
            'valid', 'vertical', 'visible', 'visible_footnote',
        ]:
            try:
                states[state_name] = state_set.contains(state_name)
            except Exception:
                pass
        return states
    except Exception:
        return {}


# --- JSON export helpers ---

def get_desktop_json(max_depth: int = 3) -> str:
    """Get desktop state as JSON string."""
    return json.dumps(get_desktop_state(max_depth=max_depth), indent=2)


def get_windows_json(app_name: str | None = None) -> str:
    """Get windows as JSON string."""
    return json.dumps(get_application_windows(app_name), indent=2)


def get_focused_json() -> str:
    """Get focused element as JSON string."""
    focused = get_focused_element()
    if focused is None:
        return json.dumps({'focused': None})
    return json.dumps({'focused': focused}, indent=2)