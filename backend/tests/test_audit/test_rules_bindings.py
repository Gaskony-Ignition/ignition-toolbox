"""Tests for FastPollingRule and ExpressionShouldBeTagRule."""

from ignition_toolkit.audit.rules.perspective.bindings import (
    ExpressionShouldBeTagRule,
    FastPollingRule,
)

from .conftest import load_project


def test_fast_polling_fires_on_now_expression_and_tag_history_rate() -> None:
    project = load_project("rules/fast_polling/positive")

    findings = FastPollingRule().evaluate(project)

    assert len(findings) == 2
    assert all(f.rule_id == "bindings-fast-polling" for f in findings)
    messages = " ".join(f.message for f in findings)
    assert "1000 ms" in messages  # now(1000)
    assert "2000 ms" in messages  # tag-history polling.rate "2" seconds


def test_fast_polling_silent_when_rate_is_at_or_above_threshold() -> None:
    project = load_project("rules/fast_polling/negative")

    findings = FastPollingRule().evaluate(project)

    assert findings == []


def test_expression_should_be_tag_fires_on_bare_tag_reference() -> None:
    project = load_project("rules/expr_tag/positive")

    findings = ExpressionShouldBeTagRule().evaluate(project)

    assert len(findings) == 1
    assert findings[0].rule_id == "bindings-expression-should-be-tag"
    assert findings[0].location == "View > root/TempLabel"


def test_expression_should_be_tag_silent_when_expression_does_real_work() -> None:
    project = load_project("rules/expr_tag/negative")

    findings = ExpressionShouldBeTagRule().evaluate(project)

    assert findings == []
