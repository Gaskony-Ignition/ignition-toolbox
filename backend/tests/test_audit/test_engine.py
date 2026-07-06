"""Tests for the generic rule engine — deliberately uses a dummy target and
dummy rules, never PerspectiveProject, to prove the engine has no domain
coupling (a future UDT linter can reuse it unmodified)."""

from ignition_toolkit.audit.engine import Finding, Rule, RuleEngine, Severity


class _AlwaysFiresRule(Rule):
    rule_id = "dummy-always-fires"
    severity = Severity.INFO
    description = "Always produces one finding, for engine testing."

    def evaluate(self, target: object) -> list[Finding]:
        return [
            Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                location="dummy-location",
                message="dummy message",
                recommendation="dummy recommendation",
            )
        ]


class _NeverFiresRule(Rule):
    rule_id = "dummy-never-fires"
    severity = Severity.INFO
    description = "Never produces a finding."

    def evaluate(self, target: object) -> list[Finding]:
        return []


class _BrokenRule(Rule):
    rule_id = "dummy-broken"
    severity = Severity.CRITICAL
    description = "Always raises, to test engine resilience."

    def evaluate(self, target: object) -> list[Finding]:
        raise ValueError("boom")


def test_engine_collects_findings_from_all_rules() -> None:
    engine = RuleEngine([_AlwaysFiresRule(), _NeverFiresRule()])

    findings = engine.run(target="anything, the engine doesn't care")

    assert len(findings) == 1
    assert findings[0].rule_id == "dummy-always-fires"


def test_engine_is_domain_agnostic() -> None:
    """The engine must accept any target type — a plain dict works fine."""
    engine = RuleEngine([_AlwaysFiresRule()])

    findings = engine.run(target={"not": "a-perspective-project"})

    assert len(findings) == 1


def test_engine_skips_a_broken_rule_without_aborting_the_run() -> None:
    engine = RuleEngine([_BrokenRule(), _AlwaysFiresRule()])

    findings = engine.run(target=None)

    assert len(findings) == 1
    assert findings[0].rule_id == "dummy-always-fires"


def test_finding_is_immutable() -> None:
    finding = Finding(
        rule_id="x",
        severity=Severity.MEDIUM,
        location="loc",
        message="msg",
        recommendation="rec",
    )
    try:
        finding.message = "changed"  # type: ignore[misc]
        assert False, "Finding should be frozen"
    except AttributeError:
        pass
