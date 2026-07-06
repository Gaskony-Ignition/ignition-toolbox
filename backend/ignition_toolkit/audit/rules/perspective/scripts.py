"""
Script rules — background-daemon threads started from view scripts (belongs
in a gateway timer script instead), and script click-handlers that duplicate
what a native nav/dock/open action already does.
"""

import logging
from typing import Any

from ignition_toolkit.audit.engine import Finding, Rule, Severity
from ignition_toolkit.audit.project import ComponentRef, PerspectiveProject

logger = logging.getLogger(__name__)

_CLICK_EVENT_NAMES = {"onclick", "onactionperformed"}


def _find_script_strings(obj: Any) -> list[str]:
    """Recursively collect every string found under a "script" or "code" key.

    Covers component event scripts (``events.<domain>.<event>.config.script``),
    message handlers and custom methods (``scripts.messageHandlers[].script``,
    ``scripts.customMethods[].script``), and binding transform scripts
    (``propConfig.<prop>.binding.transforms[].code``) without needing to model
    each of those shapes individually.
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("script", "code") and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_find_script_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_script_strings(item))
    return found


def _iter_event_actions(events: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Yield (event name, action config) for every event action on a component.

    Perspective events are nested two levels deep: domain (``dom``,
    ``system``, ``component``) -> event name (``onClick``, ``onStartup``,
    ...) -> action dict with ``type``/``config``/``scope`` keys.
    """
    actions: list[tuple[str, dict[str, Any]]] = []
    for domain_events in events.values():
        if not isinstance(domain_events, dict):
            continue
        for event_name, action in domain_events.items():
            if isinstance(action, dict) and "type" in action and "config" in action:
                actions.append((event_name, action))
    return actions


class InvokeAsynchronousDaemonRule(Rule):
    """Flags system.util.invokeAsynchronous calls in view scripts."""

    rule_id = "scripts-invoke-asynchronous-daemon"
    severity = Severity.HIGH
    description = (
        "system.util.invokeAsynchronous used from a view script instead of a gateway timer script."
    )

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                scripts = (
                    _find_script_strings(ref.node.events)
                    + _find_script_strings(ref.node.scripts)
                    + _find_script_strings(ref.node.prop_config)
                )
                if not any("invokeAsynchronous" in code for code in scripts):
                    continue
                findings.append(self._finding(ref))
        return findings

    def _finding(self, ref: ComponentRef) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            location=ref.location,
            message=(
                f'Component "{ref.node.name}" starts a background thread with '
                "system.util.invokeAsynchronous."
            ),
            recommendation=(
                f'Move the periodic work started from "{ref.node.name}" in {ref.view_path} '
                "into a gateway timer script instead of system.util.invokeAsynchronous. "
                "Threads started this way run outside the project script context (sibling "
                "module imports can fail) and keep running with stale code after the next "
                "project scan, since nothing stops them when the view that started them "
                "closes."
            ),
        )


class ClickHandlerVsNativeNavRule(Rule):
    """Flags script click-handlers that only call system.perspective.navigate."""

    rule_id = "scripts-click-handler-vs-native-nav"
    severity = Severity.MEDIUM
    description = "Script click-handler navigates where a native nav action would do."

    def evaluate(self, target: Any) -> list[Finding]:
        project: PerspectiveProject = target
        findings: list[Finding] = []
        for view in project.views.values():
            for ref in view.walk():
                for event_name, action in _iter_event_actions(ref.node.events):
                    if event_name.lower() not in _CLICK_EVENT_NAMES:
                        continue
                    if action.get("type") != "script":
                        continue
                    script = action.get("config", {}).get("script", "")
                    if "system.perspective.navigate" not in script:
                        continue
                    findings.append(self._finding(ref, event_name))
        return findings

    def _finding(self, ref: ComponentRef, event_name: str) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            severity=self.severity,
            location=ref.location,
            message=(
                f'Component "{ref.node.name}" navigates via a script in its {event_name} '
                "handler."
            ),
            recommendation=(
                f'Replace the script in the {event_name} handler of "{ref.node.name}" in '
                f'{ref.view_path} with a native navigation action (type "nav"). Native nav '
                "actions are more reliable than script-driven navigation calls and are "
                "easier for another engineer to spot and edit without opening the script "
                "editor."
            ),
        )
