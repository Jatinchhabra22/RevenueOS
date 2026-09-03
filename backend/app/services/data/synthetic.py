"""Correlated synthetic merchant ecosystem generator.

Latent customer traits drive observed payments, failures, events, and labels.
Targets are sampled from structured probabilities — not independent random bits.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.services.data.validation import validate_dataset

FAILURE_REASONS = (
    "insufficient_funds",
    "card_expired",
    "bank_declined",
    "network_error",
    "authentication_failed",
    "payment_timeout",
    "upi_failure",
    "technical_error",
)

PAYMENT_METHODS = ("card", "upi", "netbanking", "wallet")
ACTION_TYPES = (
    "retry_now",
    "retry_later",
    "payment_link",
    "email",
    "whatsapp",
    "payment_method_update",
    "retention_offer",
    "escalate_to_human",
    "stop_recovery",
)


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    n_customers: int = 3000
    merchant_id: str = "MERCHANT_001"
    as_of: str = "2026-09-01"
    currency: str = "INR"
    subscription_rate: float = 0.42


def _pad(prefix: str, index: int, width: int = 6) -> str:
    return f"{prefix}_{index:0{width}d}"


def _clip01(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.02, 0.98)


def _choice(rng: np.random.Generator, options: tuple[str, ...], size: int, p: np.ndarray | None = None) -> np.ndarray:
    return rng.choice(np.array(options), size=size, p=p)


def _failure_reason(rng: np.random.Generator, reliability: float) -> str:
    if reliability >= 0.7:
        weights = np.array([0.10, 0.06, 0.08, 0.28, 0.08, 0.22, 0.08, 0.10], dtype=float)
    elif reliability >= 0.4:
        weights = np.array([0.28, 0.12, 0.16, 0.14, 0.08, 0.10, 0.06, 0.06], dtype=float)
    else:
        weights = np.array([0.32, 0.16, 0.22, 0.06, 0.08, 0.06, 0.05, 0.05], dtype=float)
    weights = weights / weights.sum()
    return str(rng.choice(FAILURE_REASONS, p=weights))


def _suitable_action(failure_reason: str | None, churn_risk: bool) -> str:
    mapping = {
        "network_error": "retry_now",
        "payment_timeout": "retry_now",
        "technical_error": "retry_now",
        "insufficient_funds": "retry_later",
        "authentication_failed": "retry_later",
        "upi_failure": "payment_link",
        "card_expired": "payment_method_update",
        "bank_declined": "payment_link",
    }
    if churn_risk:
        return "retention_offer"
    if failure_reason in mapping:
        return mapping[failure_reason]
    return "retry_later"


def _action_success_probability(
    action: str,
    failure_reason: str | None,
    reliability: float,
    attempt_number: int,
    engagement: float,
) -> float:
    base = 0.18 + 0.28 * reliability + 0.10 * engagement
    if failure_reason in {"network_error", "payment_timeout", "technical_error"}:
        if action == "retry_now":
            base += 0.22
        elif action == "retry_later":
            base += 0.14
        else:
            base += 0.02
    elif failure_reason == "insufficient_funds":
        if action == "retry_later":
            base += 0.18
        elif action == "payment_link":
            base += 0.10
        elif action == "retry_now":
            base -= 0.10
    elif failure_reason == "card_expired":
        if action == "payment_method_update":
            base += 0.26
        elif action == "payment_link":
            base += 0.12
        elif action == "retry_now":
            base -= 0.24
    elif failure_reason == "bank_declined":
        if action in {"payment_link", "payment_method_update"}:
            base += 0.10
        elif action == "retry_now":
            base -= 0.12
    if action == "retention_offer":
        base += 0.05
    if action == "escalate_to_human":
        base += 0.02
    if action == "stop_recovery":
        return 0.0
    base -= 0.10 * max(attempt_number - 1, 0)
    return float(np.clip(base, 0.04, 0.88))


def generate_tables(config: GeneratorConfig | None = None) -> dict[str, pd.DataFrame]:
    cfg = config or GeneratorConfig()
    rng = np.random.default_rng(cfg.seed)
    as_of = datetime.fromisoformat(cfg.as_of)
    n = cfg.n_customers

    reliability = _clip01(rng.beta(5, 2, size=n))
    engagement = _clip01(rng.beta(3.2, 2.4, size=n))
    value_tendency = _clip01(rng.beta(2.4, 3.1, size=n))
    churn_tendency = _clip01(0.65 * (1 - engagement) + 0.25 * rng.beta(2, 4, size=n) + 0.1 * (1 - reliability))

    tenure_days = rng.integers(20, 900, size=n)
    signup = np.array([as_of - timedelta(days=int(d)) for d in tenure_days])
    preferred_method = _choice(rng, PAYMENT_METHODS, n, p=np.array([0.48, 0.32, 0.12, 0.08]))

    customer_ids = np.array([_pad("CUS", i + 1) for i in range(n)])

    has_subscription = (rng.random(n) < cfg.subscription_rate) & (tenure_days > 40)
    sub_ids = np.array([_pad("SUB", i + 1) if flag else "" for i, flag in enumerate(has_subscription)])
    recurring_amount = np.round(199 + value_tendency * 4800, 2)

    subscriptions_rows: list[dict[str, Any]] = []
    for i in range(n):
        if not has_subscription[i]:
            continue
        freq = "yearly" if value_tendency[i] > 0.8 and rng.random() < 0.25 else "monthly"
        start = signup[i] + timedelta(days=int(rng.integers(0, min(45, max(tenure_days[i] // 4, 1)))))
        status = "active"
        if churn_tendency[i] > 0.72 and rng.random() < 0.35:
            status = "cancelled"
        elif engagement[i] < 0.25 and rng.random() < 0.15:
            status = "paused"
        subscriptions_rows.append(
            {
                "subscription_id": sub_ids[i],
                "customer_id": customer_ids[i],
                "merchant_id": cfg.merchant_id,
                "subscription_start_date": start.isoformat(),
                "subscription_status": status,
                "recurring_amount": float(recurring_amount[i] * (10 if freq == "yearly" else 1)),
                "billing_frequency": freq,
                "successful_cycles": 0,
                "failed_cycles": 0,
                "next_billing_date": (as_of + timedelta(days=int(rng.integers(1, 28)))).date().isoformat()
                if status == "active"
                else "",
            }
        )
    subscriptions = pd.DataFrame(subscriptions_rows)
    recurring_by_customer = {
        row["customer_id"]: float(row["recurring_amount"])
        for row in subscriptions_rows
    }

    txn_rows: list[dict[str, Any]] = []
    txn_index = 1

    for i in range(n):
        expected = max(2, int(2 + tenure_days[i] / 40 * (0.4 + engagement[i])))
        n_txns = int(np.clip(rng.poisson(expected), 2, 28))
        for _k in range(n_txns):
            age = int(rng.integers(0, max(tenure_days[i], 1)))
            ts = as_of - timedelta(days=age, hours=int(rng.integers(0, 23)), minutes=int(rng.integers(0, 59)))
            is_recurring = bool(has_subscription[i] and rng.random() < 0.55)
            if is_recurring:
                amount = float(recurring_by_customer.get(customer_ids[i], recurring_amount[i]))
            else:
                amount = float(np.round(max(99.0, rng.lognormal(mean=6.4 + value_tendency[i], sigma=0.45)), 2))

            success_p = float(np.clip(0.52 + 0.42 * reliability[i] - 0.08 * (1 - engagement[i]), 0.18, 0.96))
            status = "success" if rng.random() < success_p else "failed"
            if rng.random() < 0.015:
                status = "pending"
            reason = _failure_reason(rng, float(reliability[i])) if status == "failed" else ""
            method = str(preferred_method[i])
            if rng.random() < 0.08:
                method = str(rng.choice(PAYMENT_METHODS))

            record = {
                "transaction_id": _pad("TXN", txn_index, 7),
                "customer_id": customer_ids[i],
                "merchant_id": cfg.merchant_id,
                "transaction_timestamp": ts.isoformat(),
                "amount": amount,
                "currency": cfg.currency,
                "payment_method": method,
                "transaction_status": status,
                "failure_reason": reason,
                "attempt_number": 1 if status != "failed" else int(rng.integers(1, 4)),
                "subscription_id": sub_ids[i] if is_recurring and sub_ids[i] else "",
                "is_recurring": is_recurring,
            }
            txn_rows.append(record)
            txn_index += 1

    transactions = pd.DataFrame(txn_rows)

    successful_cycles: dict[str, int] = {}
    failed_cycles: dict[str, int] = {}
    for row in txn_rows:
        sid = row["subscription_id"]
        if not sid:
            continue
        if row["transaction_status"] == "success":
            successful_cycles[sid] = successful_cycles.get(sid, 0) + 1
        elif row["transaction_status"] == "failed":
            failed_cycles[sid] = failed_cycles.get(sid, 0) + 1
    if not subscriptions.empty:
        subscriptions["successful_cycles"] = subscriptions["subscription_id"].map(lambda s: successful_cycles.get(s, 0))
        subscriptions["failed_cycles"] = subscriptions["subscription_id"].map(lambda s: failed_cycles.get(s, 0))

    event_rows: list[dict[str, Any]] = []
    event_index = 1
    failed_txns = transactions[transactions["transaction_status"] == "failed"].copy()
    failed_txns["_ts"] = pd.to_datetime(failed_txns["transaction_timestamp"])
    failed_txns = failed_txns.sort_values("_ts")

    recent_cutoff = as_of - timedelta(days=45)
    sampled_failed = failed_txns.sample(frac=0.55, random_state=cfg.seed) if len(failed_txns) else failed_txns

    customer_fail_counts = failed_txns.groupby("customer_id").size().to_dict()

    for row in sampled_failed.itertuples(index=False):
        ts = pd.Timestamp(row.transaction_timestamp).to_pydatetime()
        n_fails = int(customer_fail_counts.get(row.customer_id, 1))
        amount = float(row.amount)
        is_sub = bool(row.is_recurring and row.subscription_id)
        if n_fails >= 3:
            event_type = "repeated_payment_failure"
        elif is_sub:
            event_type = "subscription_payment_failed"
        elif amount >= 15000:
            event_type = "high_value_payment_failure"
        else:
            event_type = "payment_failed"

        is_open = ts >= recent_cutoff
        urgency = "high" if amount >= 8000 or n_fails >= 3 else ("medium" if amount >= 2000 else "low")
        event_rows.append(
            {
                "event_id": _pad("EVT", event_index),
                "event_timestamp": ts.isoformat(),
                "merchant_id": cfg.merchant_id,
                "customer_id": row.customer_id,
                "event_type": event_type,
                "amount_at_risk": amount,
                "payment_method": row.payment_method,
                "failure_reason": row.failure_reason,
                "attempt_number": int(row.attempt_number),
                "transaction_id": row.transaction_id,
                "subscription_id": row.subscription_id or "",
                "urgency": urgency,
                "event_status": "open" if is_open else "resolved",
            }
        )
        event_index += 1

    revenue_events = pd.DataFrame(event_rows)
    if len(revenue_events) > 3200:
        open_mask = revenue_events["event_status"].eq("open")
        open_events = revenue_events[open_mask]
        resolved = revenue_events[~open_mask]
        keep_resolved = resolved.sample(n=min(len(resolved), 3200 - len(open_events)), random_state=cfg.seed)
        revenue_events = pd.concat([open_events, keep_resolved], ignore_index=True)

    reliability_by_customer = dict(zip(customer_ids, reliability, strict=True))
    engagement_by_customer = dict(zip(customer_ids, engagement, strict=True))
    churn_by_customer = dict(zip(customer_ids, churn_tendency, strict=True))

    intervention_rows: list[dict[str, Any]] = []
    int_index = 1
    recovered_by_customer: dict[str, int] = {cid: 0 for cid in customer_ids}
    event_recovered: dict[str, bool] = {}

    historical_events = revenue_events[revenue_events["event_status"].eq("resolved")]
    for row in historical_events.itertuples(index=False):
        n_actions = int(rng.integers(1, 4))
        recovered = False
        last_ts = pd.Timestamp(row.event_timestamp).to_pydatetime()
        for attempt in range(1, n_actions + 1):
            if recovered:
                break
            high_churn = float(churn_by_customer[row.customer_id]) > 0.7 and attempt > 1
            suitable = _suitable_action(row.failure_reason or None, high_churn)
            if rng.random() < 0.38:
                action = str(rng.choice(ACTION_TYPES))
            else:
                action = suitable
            p = _action_success_probability(
                action,
                row.failure_reason or None,
                float(reliability_by_customer[row.customer_id]),
                attempt,
                float(engagement_by_customer[row.customer_id]),
            )
            p = float(np.clip(p + rng.normal(0, 0.05), 0.02, 0.98))
            success = bool(rng.random() < p)
            hours = float(np.round(max(0.2, rng.lognormal(1.1, 0.7)), 2))
            last_ts = last_ts + timedelta(hours=hours)
            outcome = "recovered" if success and action != "stop_recovery" else (
                "escalated" if action == "escalate_to_human" else ("stopped" if action == "stop_recovery" else "failed")
            )
            if outcome == "failed" and rng.random() < 0.12:
                outcome = "ignored"
            amount_recovered = float(row.amount_at_risk) if outcome == "recovered" else 0.0
            if outcome == "recovered":
                recovered = True
                recovered_by_customer[row.customer_id] += 1
            intervention_rows.append(
                {
                    "intervention_id": _pad("INT", int_index),
                    "event_id": row.event_id,
                    "customer_id": row.customer_id,
                    "action_type": action,
                    "action_timestamp": last_ts.isoformat(),
                    "attempt_number": attempt,
                    "outcome": outcome,
                    "amount_recovered": amount_recovered,
                    "response_time_hours": hours,
                }
            )
            int_index += 1
        event_recovered[row.event_id] = recovered

    if event_recovered:
        recovered_ids = {eid for eid, flag in event_recovered.items() if flag}
        revenue_events.loc[
            revenue_events["event_id"].isin(recovered_ids),
            "event_status",
        ] = "resolved"

    intervention_history = pd.DataFrame(intervention_rows)

    customer_rows: list[dict[str, Any]] = []
    txn_by_customer = transactions.groupby("customer_id")
    for i, cid in enumerate(customer_ids):
        group = txn_by_customer.get_group(cid) if cid in txn_by_customer.groups else pd.DataFrame()
        total_orders = int(len(group))
        total_spend = float(group.loc[group["transaction_status"].eq("success"), "amount"].sum()) if total_orders else 0.0
        successes = int(group["transaction_status"].eq("success").sum()) if total_orders else 0
        failures = int(group["transaction_status"].eq("failed").sum()) if total_orders else 0
        success_rate = float(successes / max(total_orders, 1))
        last_activity = (
            pd.to_datetime(group["transaction_timestamp"]).max().to_pydatetime()
            if total_orders
            else signup[i]
        )
        days_inactive = (as_of - last_activity).days
        if engagement[i] > 0.65 and days_inactive < 21:
            trend = "increasing"
        elif engagement[i] < 0.28 or days_inactive > 60:
            trend = "declining" if days_inactive < 120 else "inactive"
        else:
            trend = "stable"

        if tenure_days[i] < 75:
            segment = "NEW"
        elif churn_tendency[i] > 0.68 or trend in {"declining", "inactive"}:
            segment = "AT_RISK"
        elif value_tendency[i] > 0.88:
            segment = "VIP"
        elif value_tendency[i] > 0.68:
            segment = "HIGH_VALUE"
        else:
            segment = "REGULAR"

        ltv = float(np.round(total_spend + recurring_amount[i] * (12 if has_subscription[i] else 3) * (0.4 + value_tendency[i]), 2))
        churn_p = float(
            np.clip(
                0.05
                + 0.55 * churn_tendency[i]
                + 0.08 * (failures / max(total_orders, 1))
                + (0.12 if trend in {"declining", "inactive"} else 0.0)
                - 0.08 * reliability[i],
                0.02,
                0.92,
            )
        )
        churned = int(rng.random() < churn_p)

        customer_rows.append(
            {
                "customer_id": cid,
                "merchant_id": cfg.merchant_id,
                "customer_segment": segment,
                "signup_date": signup[i].date().isoformat(),
                "tenure_days": int(tenure_days[i]),
                "total_orders": total_orders,
                "total_spend": float(np.round(total_spend, 2)),
                "avg_order_value": float(np.round(total_spend / max(successes, 1), 2)),
                "payment_success_rate": float(np.round(success_rate, 4)),
                "previous_failures": failures,
                "previous_recoveries": int(recovered_by_customer[cid]),
                "engagement_score": float(np.round(engagement[i], 4)),
                "activity_trend": trend,
                "customer_ltv": ltv,
                "last_activity_date": last_activity.date().isoformat(),
                "churned": churned,
            }
        )

    customers = pd.DataFrame(customer_rows)

    # Intentional missingness (merchant-like incompleteness)
    miss_idx = rng.choice(len(transactions), size=max(1, int(0.03 * len(transactions))), replace=False)
    transactions.loc[transactions.index[miss_idx], "payment_method"] = ""
    failed_idx = transactions.index[transactions["transaction_status"].eq("failed")]
    if len(failed_idx):
        hide = rng.choice(failed_idx, size=max(1, int(0.04 * len(failed_idx))), replace=False)
        transactions.loc[hide, "failure_reason"] = ""
    eng_hide = rng.choice(len(customers), size=max(1, int(0.04 * len(customers))), replace=False)
    customers.loc[customers.index[eng_hide], "engagement_score"] = np.nan

    return {
        "customers": customers,
        "transactions": transactions,
        "subscriptions": subscriptions,
        "revenue_events": revenue_events,
        "intervention_history": intervention_history,
    }


def write_dataset(
    output_dir: Path,
    config: GeneratorConfig | None = None,
    extra_dirs: list[Path] | None = None,
) -> dict[str, Any]:
    cfg = config or GeneratorConfig()
    tables = generate_tables(cfg)
    destinations = [output_dir, *(extra_dirs or [])]
    metadata: dict[str, Any] | None = None

    report = validate_dataset(
        tables["customers"],
        tables["transactions"],
        tables["subscriptions"],
        tables["revenue_events"],
        tables["intervention_history"],
    )
    metadata = {
        "dataset_version": "0.1.0",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": cfg.seed,
        "merchant_id": cfg.merchant_id,
        "config": asdict(cfg),
        "row_counts": report["row_counts"],
        "recovery_rate": report["recovery_rate"],
        "churn_rate": report["churn_rate"],
        "validation": report,
    }
    merchant_config = {
        "merchant_id": cfg.merchant_id,
        "max_retry_attempts": 3,
        "max_contact_attempts": 3,
        "contact_cooldown_hours": 24,
        "high_value_escalation_threshold": 50000,
        "low_value_stop_threshold": 100,
        "allowed_actions": list(ACTION_TYPES),
    }

    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        for name, frame in tables.items():
            frame.to_csv(destination / f"{name}.csv", index=False)
        (destination / "metadata.json").write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )
        (destination / "merchant_config.json").write_text(
            json.dumps(merchant_config, indent=2),
            encoding="utf-8",
        )
    return metadata


def default_output_dirs() -> tuple[Path, Path]:
    root = get_settings().data_path
    return root / "synthetic", root / "demo"
