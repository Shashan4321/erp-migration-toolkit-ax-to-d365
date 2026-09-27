"""End-to-end and unit tests for the migration toolkit."""

import pandas as pd
import pytest

from erpmig import generate_ax, migrate, reconcile
from erpmig.rules import apply_rules


@pytest.fixture(scope="module")
def results():
    generate_ax.generate(migrate.ROOT / "data" / "source_ax")
    return migrate.run()


def test_every_source_row_is_accounted_for(results):
    for r in results.values():
        assert len(r.loaded) + len(r.rejects) == r.source_rows, r.entity


def test_all_reconciliation_checks_pass(results):
    checks = reconcile.reconcile(results)
    failed = [c for c in checks if not c.passed]
    assert not failed, failed


def test_duplicates_and_orphans_are_quarantined_with_reasons(results):
    cust = results["customer"].rejects
    assert set(cust["reject_reason"]) == {"duplicate_after_normalisation"}
    inv = results["open_invoice"].rejects
    assert (inv["ACCOUNTNUM"] == "C99999").all()
    assert set(inv["reject_reason"]) == {"orphan:Customer No."}


def test_target_keys_are_unique_and_clean(results):
    keys = results["customer"].loaded["No."]
    assert keys.is_unique
    assert (keys == keys.str.strip().str.upper()).all()


def test_local_currency_is_blank_in_bc(results):
    assert "INR" not in set(results["customer"].loaded["Currency Code"])


def test_tampering_is_detected(results):
    """If an amount changes in flight, the financial check must fail."""
    tampered = dict(results)
    inv = results["open_invoice"]
    loaded = inv.loaded.copy()
    loaded.loc[0, "Amount"] += 1.00
    tampered["open_invoice"] = migrate.EntityResult(
        inv.entity, inv.source_rows, loaded, inv.rejects, inv.warnings
    )
    assert not all(c.passed for c in reconcile.reconcile(tampered))


@pytest.mark.parametrize(
    "rules,value,expected",
    [
        (["trim", "upper"], "  c00001 ", "C00001"),
        (["trim", "upper", "map_posting_group"], "dom  ", "DOMESTIC"),
        (["trim", "upper", "lcy_blank"], "INR", ""),
        (["trim", "upper", "lcy_blank"], "usd", "USD"),
        (["trim", "lower", "valid_email_or_blank"], "not-an-email", ""),
        (["trim", "lower", "valid_email_or_blank"], "A@B.COM", "a@b.com"),
    ],
)
def test_rules(rules, value, expected):
    assert apply_rules(pd.Series([value]), rules).iloc[0] == expected


def test_unknown_rule_raises():
    with pytest.raises(KeyError):
        apply_rules(pd.Series(["x"]), ["does_not_exist"])
