"""
Debugging utilities for Reader Desktop AT-SPI capture.
Run from console to test and visualize captured desktop data.
"""

import sys
import os
import json

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from reader.desktop import capture


def print_tree_element(element: dict, indent: int = 0, max_depth: int = 3, current_depth: int = 1) -> None:
    """Recursively print an element and its children."""
    if current_depth > max_depth:
        return

    prefix = "  " * indent
    name = element.get('name', '(no name)')
    role = element.get('role', '')
    desc = element.get('description', '')

    # Truncate long names
    display_name = name[:50] + '...' if len(name) > 50 else name
    if not display_name:
        display_name = '(no name)'

    # Show text if present
    text = element.get('text', '')
    if text:
        text_short = text[:30] + '...' if len(text) > 30 else text
        print(f"{prefix}├─ {display_name} [{role}] \"{text_short}\"")
    else:
        print(f"{prefix}├─ {display_name} [{role}]")

    # Show states that are True
    states = element.get('states', {})
    active_states = [k for k, v in states.items() if v]
    if active_states:
        print(f"{prefix}|   states: {', '.join(active_states)}")

    # Show geometry if present
    geom = element.get('geometry')
    if geom:
        print(f"{prefix}|   geometry: {geom['width']}x{geom['height']}+{geom['x']}+{geom['y']}")

    # Recurse into children
    children = element.get('children', [])
    for i, child in enumerate(children):
        is_last = (i == len(children) - 1)
        child_prefix = prefix.replace("├─", " ") if not is_last else prefix
        print_tree_element(child, indent + 1, max_depth, current_depth + 1)


def print_desktop_state(max_depth: int = 3):
    """Print full desktop state with element trees."""
    print("=" * 70)
    print("DESKTOP STATE")
    print("=" * 70)

    state = capture.get_desktop_state(max_depth=max_depth)

    print(f"\nDesktop: {state['desktop']['name']} ({state['desktop']['role']})")
    print(f"Applications: {len(state['applications'])}")

    for app in state['applications']:
        print(f"\n  📦 {app['name']} ({app['role']})")
        for win in app['windows']:
            geom = win['geometry']
            if geom:
                geo_str = f" @ {geom['width']}x{geom['height']}+{geom['x']}+{geom['y']}"
            else:
                geo_str = ""
            print(f"    └─ {win['name']} ({win['role']}){geo_str}")

            children = win.get('children', [])
            if children:
                print(f"       │")
                for child in children:
                    print_tree_element(child, indent=4, max_depth=max_depth, current_depth=1)


def print_windows():
    """Print all windows in a flat list."""
    print("=" * 70)
    print("ALL WINDOWS")
    print("=" * 70)

    windows = capture.get_application_windows()
    print(f"Total windows: {len(windows)}\n")

    for win in windows:
        app = win.get('application', 'unknown')
        geo = win.get('geometry')
        if geo:
            geo_str = f" @ {geo['width']}x{geo['height']}+{geo['x']}+{geo['y']}"
        else:
            geo_str = ""
        print(f"[{app}] {win['name']} ({win['role']}){geo_str}")


def print_focused():
    """Print currently focused element."""
    print("=" * 70)
    print("FOCUSED ELEMENT")
    print("=" * 70)

    focused = capture.get_focused_element()
    if focused:
        print(f"Name: {focused.get('name', '(none)')}")
        print(f"Role: {focused.get('role', '(none)')}")
        print(f"Description: {focused.get('description', '')}")

        states = focused.get('states', {})
        if states:
            # Print only states that are True
            active_states = [k for k, v in states.items() if v]
            if active_states:
                print(f"States: {', '.join(active_states)}")

        print(f"Application: {focused.get('application', '(unknown)')}")
        print(f"Window: {focused.get('window', '(unknown)')}")
    else:
        print("No focused element")


def print_json(max_depth: int = 3):
    """Write desktop state as JSON to file."""
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'debug_reader_json_output.json'
    )

    json_output = capture.get_desktop_json(max_depth=max_depth)

    with open(output_file, 'w') as f:
        f.write(json_output)

    print(f"Written to: {output_file}")
    print(f"Size: {len(json_output)} bytes")


def print_roles():
    """Print all unique roles found in the current desktop."""
    print("=" * 70)
    print("ALL ROLES IN DESKTOP")
    print("=" * 70)

    state = capture.get_desktop_state(max_depth=3)
    roles = set()

    def collect_roles(element: dict):
        if 'role' in element:
            roles.add(element['role'])
        for child in element.get('children', []):
            collect_roles(child)

    for app in state['applications']:
        for win in app['windows']:
            collect_roles(win)
            for child in win.get('children', []):
                collect_roles(child)

    print(f"Found {len(roles)} unique roles:\n")
    for role in sorted(roles):
        print(f"  - {role}")


def main():
    """Main entry point for debugging tools."""
    import argparse

    parser = argparse.ArgumentParser(description="Debug Desktop AT-SPI capture")
    parser.add_argument(
        'command',
        choices=['desktop', 'windows', 'focused', 'json', 'roles'],
        help='What to print (default: desktop)',
        nargs='?',
        default='desktop'
    )
    parser.add_argument(
        '-d', '--depth',
        type=int,
        default=3,
        help='Max tree depth (default: 3)'
    )
    args = parser.parse_args()

    commands = {
        'desktop': lambda: print_desktop_state(max_depth=args.depth),
        'windows': print_windows,
        'focused': print_focused,
        'json': lambda: print_json(max_depth=args.depth),
        'roles': print_roles,
    }

    commands[args.command]()


if __name__ == '__main__':
    main()