import pandas as pd

from src.analysis import get_basic_summary

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}

INSIGHT_TONES = {
    "Budget variance": "tone-risk",
    "Budget exposure": "tone-risk",
    "Category concentration": "tone-structure",
    "Refund adjustment": "tone-adjustment",
    "Peak period": "tone-trend",
    "Monthly volatility": "tone-trend",
    "Priority mix": "tone-structure",
    "Outlier transaction": "tone-risk",
    "Payment pattern": "tone-structure",
    "Needs vs wants": "tone-structure",
    "Financial health": "tone-trend",
    "Savings and debt": "tone-conclusion",
    "Emergency fund": "tone-structure",
    "Budget balance": "tone-trend",
    "Analytical conclusion": "tone-conclusion",
    "Budget cap": "tone-recommendation",
    "Spending shift": "tone-recommendation",
    "Savings target": "tone-recommendation",
    "Emergency savings": "tone-recommendation",
    "Period review": "tone-recommendation",
    "Debt management": "tone-recommendation",
}


def _format_php(value):
    """Format a numeric value as a peso amount for insight text."""
    if value is None or pd.isna(value):
        return "PHP 0.00"
    return f"PHP {value:,.2f}"


def _make_insight(
    insight_id,
    kind,
    text,
    section="finding",
    severity="info",
    tone=None,
    metrics=None,
):
    """Build a structured insight record for rendering and export."""
    return {
        "id": insight_id,
        "kind": kind,
        "tone": tone or INSIGHT_TONES.get(kind, ""),
        "text": text,
        "section": section,
        "severity": severity,
        "priority": SEVERITY_ORDER.get(severity, 2),
        "metrics": metrics or {},
    }


def _sort_insights(items):
    return sorted(items, key=lambda item: (item["priority"], item["kind"]))


def _prepare_insight_data(df):
    """Return a cleaned copy for insight calculations."""
    if df is None or df.empty or "amount_php" not in df.columns:
        return None

    insight_df = df.copy()
    insight_df["amount_php"] = pd.to_numeric(insight_df["amount_php"], errors="coerce")
    insight_df = insight_df.dropna(subset=["amount_php"])

    if insight_df.empty:
        return None

    if "date" in insight_df.columns:
        insight_df["date"] = pd.to_datetime(insight_df["date"], errors="coerce")

    if "month" in insight_df.columns:
        insight_df["month"] = insight_df["month"].astype(str)
    elif "date" in insight_df.columns:
        insight_df["month"] = insight_df["date"].dt.to_period("M").astype(str)

    if "budget_limit_php" in insight_df.columns:
        insight_df["budget_limit_php"] = pd.to_numeric(
            insight_df["budget_limit_php"], errors="coerce"
        ).fillna(0)

    return insight_df


def _filter_context_note(summary):
    if summary and summary.get("is_processed_summary"):
        return (
            "These insights use the full processed analysis dataset. "
            "Sidebar filters still apply to transaction-level charts and tables."
        )
    return "Insights reflect the currently filtered transaction records."


def _transaction_findings(insight_df, summary):
    findings = []
    total_expenses = summary.get("gross_expense_total", 0)
    refund_total = summary.get("refund_total", 0)

    budget_summary = summary.get("budget_summary", {})
    if budget_summary and budget_summary.get("total_budget", 0) > 0:
        budget_usage = budget_summary.get("budget_usage_percent", 0)
        remaining_budget = budget_summary.get("remaining_budget")
        severity = "critical" if budget_usage > 100 else "info"
        if budget_usage > 100:
            text = (
                f"Positive expenses exceed the monthly category budget by "
                f"{_format_php(abs(remaining_budget))}. Budget utilization is "
                f"{budget_usage:.1f}%, indicating that actual spending is materially "
                f"above the planned allocation."
            )
        else:
            text = (
                f"Positive expenses used {budget_usage:.1f}% of the monthly category "
                f"budget, leaving {_format_php(remaining_budget)} unspent. The selected "
                f"period remains within the planned allocation."
            )
        findings.append(
            _make_insight(
                "budget_variance",
                "Budget variance",
                text,
                severity=severity,
                metrics={"budget_usage_percent": budget_usage},
            )
        )

    budget_by_category = summary.get("budget_by_category", {})
    if budget_by_category:
        budget_df = pd.DataFrame.from_dict(budget_by_category, orient="index")
        budget_df = budget_df[budget_df["total_budget"] > 0]
        if not budget_df.empty:
            highest_usage = budget_df.sort_values(
                "usage_percent", ascending=False
            ).iloc[0]
            gap = highest_usage["total_spent"] - highest_usage["total_budget"]
            position = (
                f"over budget by {_format_php(gap)}"
                if gap > 0
                else f"within budget by {_format_php(abs(gap))}"
            )
            severity = "critical" if gap > 0 else "warning"
            findings.append(
                _make_insight(
                    "budget_exposure",
                    "Budget exposure",
                    f"{highest_usage.name} has the highest category-level utilization at "
                    f"{highest_usage['usage_percent']:.1f}% and is {position}. This category "
                    f"should be reviewed first because it contributes the strongest budget pressure.",
                    severity=severity,
                    metrics={
                        "category": highest_usage.name,
                        "usage_percent": float(highest_usage["usage_percent"]),
                    },
                )
            )

    category_totals = summary.get("category_totals", {})
    if category_totals and total_expenses:
        category_count = len(category_totals)
        top_category, top_category_total = next(iter(category_totals.items()))
        category_share = (top_category_total / total_expenses) * 100
        if category_count == 1:
            text = (
                f"All selected positive expenses fall under {top_category} at "
                f"{_format_php(top_category_total)}. Narrow filters can hide cross-category "
                f"concentration, so compare against the full dataset when possible."
            )
        else:
            text = (
                f"{top_category} is the largest expense category at "
                f"{_format_php(top_category_total)}, representing {category_share:.1f}% of "
                f"total positive expenses. Monitoring this category will have the highest impact "
                f"on overall spending control."
            )
        findings.append(
            _make_insight(
                "category_concentration",
                "Category concentration",
                text,
                severity="warning" if category_share >= 40 else "info",
                metrics={"category": top_category, "share_percent": category_share},
            )
        )

    if refund_total:
        refund_share = (refund_total / total_expenses) * 100 if total_expenses else 0
        findings.append(
            _make_insight(
                "refund_adjustment",
                "Refund adjustment",
                f"Refunds reduced the net amount by {_format_php(refund_total)}, equivalent "
                f"to {refund_share:.1f}% of positive expenses. Reporting both gross expenses "
                f"and net amount prevents refunds from hiding the true spending level.",
                severity="info",
                metrics={"refund_total": refund_total},
            )
        )

    monthly_trends = summary.get("monthly_trends", {})
    if monthly_trends:
        monthly_df = pd.DataFrame.from_dict(monthly_trends, orient="index")
        expense_series = monthly_df["gross_expense_total"].sort_index()
        if not expense_series.empty:
            peak_month = expense_series.idxmax()
            peak_month_total = expense_series.loc[peak_month]
            findings.append(
                _make_insight(
                    "peak_period",
                    "Peak period",
                    f"Expenses reached their highest monthly value in {peak_month} at "
                    f"{_format_php(peak_month_total)}. This period should be used as the "
                    f"reference point for investigating unusual activity or seasonal spending.",
                    severity="info",
                    metrics={"month": str(peak_month)},
                )
            )

        if len(expense_series) >= 2:
            month_changes = expense_series.diff().dropna()
            if not month_changes.empty:
                biggest_change = month_changes.loc[month_changes.abs().idxmax()]
                change_month = month_changes.abs().idxmax()
                direction = "increased" if biggest_change >= 0 else "decreased"
                findings.append(
                    _make_insight(
                        "monthly_volatility",
                        "Monthly volatility",
                        f"The largest month-to-month movement occurred in {change_month}, when "
                        f"expenses {direction} by {_format_php(abs(biggest_change))}. This "
                        f"indicates the strongest short-term shift in spending behavior.",
                        severity="warning",
                        metrics={"month": str(change_month), "change": float(biggest_change)},
                    )
                )

    amount_stats = summary.get("amount_statistics", {})
    average_expense = summary.get("average_expense")
    largest_transaction = amount_stats.get("largest_transaction")
    if largest_transaction and average_expense and average_expense > 0:
        uplift = ((largest_transaction - average_expense) / average_expense) * 100
        if uplift >= 50:
            findings.append(
                _make_insight(
                    "outlier_transaction",
                    "Outlier transaction",
                    f"The largest single expense is {_format_php(largest_transaction)}, which is "
                    f"{uplift:.1f}% above the average expense of {_format_php(average_expense)}. "
                    f"Review this transaction to confirm whether it is recurring or one-off.",
                    severity="warning" if uplift >= 100 else "info",
                    metrics={"largest_transaction": largest_transaction},
                )
            )

    frequency_distributions = summary.get("frequency_distributions", {})
    payment_distribution = frequency_distributions.get("payment_method", {})
    if payment_distribution and total_expenses and "payment_method" in insight_df.columns:
        top_payment = max(
            payment_distribution.items(),
            key=lambda item: item[1].get("count", 0),
        )
        payment_name, payment_stats = top_payment
        payment_share = payment_stats.get("percentage", 0)
        if payment_share >= 35:
            findings.append(
                _make_insight(
                    "payment_pattern",
                    "Payment pattern",
                    f"{payment_name} accounts for {payment_share:.1f}% of filtered transactions. "
                    f"If this method carries fees or rewards trade-offs, consolidating spend "
                    f"through one primary channel may simplify monitoring.",
                    severity="info",
                    metrics={"payment_method": payment_name, "share_percent": payment_share},
                )
            )

    if "necessity_type" in insight_df.columns:
        necessity_totals = (
            insight_df[insight_df["amount_php"] > 0]
            .groupby("necessity_type", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        if not necessity_totals.empty:
            top_necessity = necessity_totals.index[0]
            priority_share = (
                necessity_totals.iloc[0] / total_expenses * 100 if total_expenses else 0
            )
            findings.append(
                _make_insight(
                    "priority_mix",
                    "Priority mix",
                    f"{top_necessity} transactions account for the largest priority-group "
                    f"expense at {_format_php(necessity_totals.iloc[0])}, or "
                    f"{priority_share:.1f}% of positive expenses. This helps distinguish "
                    f"essential spending pressure from discretionary behavior.",
                    severity="info",
                    metrics={"necessity_type": str(top_necessity)},
                )
            )

            needs_total = necessity_totals.get("Need", 0) + necessity_totals.get("Needs", 0)
            wants_total = necessity_totals.get("Want", 0) + necessity_totals.get("Wants", 0)
            classified_total = needs_total + wants_total
            if classified_total > 0:
                needs_percent = needs_total / classified_total * 100
                wants_percent = wants_total / classified_total * 100
                findings.append(
                    _make_insight(
                        "needs_vs_wants",
                        "Needs vs wants",
                        f"Needs represent {needs_percent:.1f}% and wants represent "
                        f"{wants_percent:.1f}% of classified spending. A balanced target is "
                        f"closer to 50% needs and 30% wants when savings are tracked separately.",
                        severity="warning" if wants_percent > 45 else "info",
                        metrics={
                            "needs_percent": needs_percent,
                            "wants_percent": wants_percent,
                        },
                    )
                )

    return _sort_insights(findings)


def _processed_findings(summary):
    findings = []
    budget_rows = summary.get("budget_by_category", {})
    if budget_rows:
        category, values = max(
            budget_rows.items(),
            key=lambda item: item[1].get("total_spent", 0)
            - item[1].get("total_budget", 0),
        )
        variance = values.get("total_spent", 0) - values.get("total_budget", 0)
        findings.append(
            _make_insight(
                "processed_budget_variance",
                "Budget variance",
                f"{category} has the largest processed budget variance at "
                f"{_format_php(variance)}.",
                severity="critical" if variance > 0 else "info",
                metrics={"category": category, "variance": variance},
            )
        )

    latest_score = summary.get("latest_financial_health_score")
    health = summary.get("financial_health_summary", {})
    average_score = health.get("average_financial_health_score")
    if latest_score is not None:
        average_score_text = (
            f"{average_score:.2f}" if average_score is not None else "N/A"
        )
        severity = "critical" if latest_score < 50 else "warning" if latest_score < 70 else "info"
        findings.append(
            _make_insight(
                "financial_health",
                "Financial health",
                f"Latest score is {latest_score:.2f}; average score across observed months "
                f"is {average_score_text}.",
                severity=severity,
                metrics={"latest_score": latest_score},
            )
        )

    savings_rate = summary.get("average_savings_rate")
    debt_ratio = summary.get("average_debt_ratio")
    if savings_rate is not None and debt_ratio is not None:
        severity = "warning" if savings_rate < 10 or debt_ratio > 30 else "info"
        findings.append(
            _make_insight(
                "savings_and_debt",
                "Savings and debt",
                f"Average savings rate is {savings_rate:.2f}% and average debt ratio is "
                f"{debt_ratio:.2f}% from processed monthly summaries.",
                severity=severity,
                metrics={"savings_rate": savings_rate, "debt_ratio": debt_ratio},
            )
        )

    emergency = summary.get("emergency_fund_summary", {})
    consistency = emergency.get("consistency_rate_percent")
    months_with = emergency.get("months_with_contribution")
    months_total = emergency.get("months_observed")
    if consistency is not None:
        severity = "warning" if consistency < 60 else "info"
        findings.append(
            _make_insight(
                "emergency_fund",
                "Emergency fund",
                f"Emergency fund contributions appear in {months_with} of {months_total} "
                f"months, a {consistency:.2f}% consistency rate.",
                severity=severity,
                metrics={"consistency_percent": consistency},
            )
        )

    expense_group_df = summary.get("expense_group_summary")
    if isinstance(expense_group_df, pd.DataFrame) and not expense_group_df.empty:
        group_column = "expense_group" if "expense_group" in expense_group_df.columns else None
        if group_column:
            grouped = expense_group_df.copy()
            grouped["total_spent"] = pd.to_numeric(
                grouped["total_spent"], errors="coerce"
            ).fillna(0)
            total_spent = grouped["total_spent"].sum()
            if total_spent > 0:
                labels = grouped[group_column].astype(str).str.strip().str.lower()
                needs_total = grouped.loc[
                    labels.isin(["need", "needs"]), "total_spent"
                ].sum()
                wants_total = grouped.loc[
                    labels.isin(["want", "wants"]), "total_spent"
                ].sum()
                classified_total = needs_total + wants_total
                if classified_total > 0:
                    needs_percent = needs_total / classified_total * 100
                    wants_percent = wants_total / classified_total * 100
                    findings.append(
                        _make_insight(
                            "processed_needs_vs_wants",
                            "Needs vs wants",
                            f"Processed needs spending is {needs_percent:.1f}% and wants "
                            f"spending is {wants_percent:.1f}% of classified expenses. Compare "
                            f"this against the 50/30/20 guideline for budget balance.",
                            severity="warning" if wants_percent > 45 else "info",
                            metrics={
                                "needs_percent": needs_percent,
                                "wants_percent": wants_percent,
                            },
                        )
                    )

    health_targets = health.get("targets", {})
    monthly_scores = health.get("monthly_scores", [])
    if monthly_scores and health_targets:
        latest_month = monthly_scores[-1]
        needs_target = health_targets.get("needs_percent", 50)
        wants_target = health_targets.get("wants_percent", 30)
        savings_target = health_targets.get("savings_percent", 20)
        needs_percent = latest_month.get("needs_percent") or 0
        wants_percent = latest_month.get("wants_percent") or 0
        savings_percent = latest_month.get("savings_percent") or 0
        deviation = (
            abs(needs_percent - needs_target)
            + abs(wants_percent - wants_target)
            + abs(savings_percent - savings_target)
        )
        if deviation >= 15:
            findings.append(
                _make_insight(
                    "budget_balance",
                    "Budget balance",
                    f"The latest month deviates from 50/30/20 targets by {deviation:.1f} "
                    f"percentage points across needs, wants, and savings. Needs are at "
                    f"{needs_percent:.1f}%, wants at {wants_percent:.1f}%, and savings at "
                    f"{savings_percent:.1f}%.",
                    severity="warning",
                    metrics={"deviation": deviation},
                )
            )

    return _sort_insights(findings)


def _transaction_recommendations(insight_df, summary):
    recommendations = []
    total_expenses = summary.get("gross_expense_total", 0)

    budget_by_category = summary.get("budget_by_category", {})
    if budget_by_category:
        budget_df = pd.DataFrame.from_dict(budget_by_category, orient="index")
        budget_df = budget_df[budget_df["total_budget"] > 0]
        overspent = budget_df[budget_df["total_spent"] > budget_df["total_budget"]]
        if not overspent.empty:
            target = overspent.sort_values("usage_percent", ascending=False).iloc[0]
            gap = target["total_spent"] - target["total_budget"]
            recommendations.append(
                _make_insight(
                    "recommend_budget_cap",
                    "Budget cap",
                    f"Set a tighter monthly cap for {target.name} at "
                    f"{_format_php(target['total_budget'])} and track weekly totals to reduce "
                    f"the current overspend of {_format_php(gap)}.",
                    section="recommendation",
                    severity="critical",
                    metrics={"category": target.name, "gap": float(gap)},
                )
            )

    monthly_trends = summary.get("monthly_trends", {})
    if monthly_trends:
        monthly_df = pd.DataFrame.from_dict(monthly_trends, orient="index")
        expense_series = monthly_df["gross_expense_total"].sort_index()
        if len(expense_series) >= 2:
            month_changes = expense_series.diff().dropna()
            if not month_changes.empty:
                biggest_change = month_changes.loc[month_changes.abs().idxmax()]
                if biggest_change > 0:
                    change_month = month_changes.abs().idxmax()
                    recommendations.append(
                        _make_insight(
                            "recommend_period_review",
                            "Period review",
                            f"Review all transactions in {change_month} to separate recurring "
                            f"costs from one-off spikes worth {_format_php(biggest_change)}.",
                            section="recommendation",
                            severity="warning",
                            metrics={"month": str(change_month)},
                        )
                    )

    if "necessity_type" in insight_df.columns and total_expenses:
        necessity_totals = (
            insight_df[insight_df["amount_php"] > 0]
            .groupby("necessity_type", observed=True)["amount_php"]
            .sum()
        )
        wants_total = necessity_totals.get("Want", 0) + necessity_totals.get("Wants", 0)
        needs_total = necessity_totals.get("Need", 0) + necessity_totals.get("Needs", 0)
        classified_total = wants_total + needs_total
        if classified_total > 0 and wants_total / classified_total > 0.4:
            shift_amount = wants_total * 0.1
            recommendations.append(
                _make_insight(
                    "recommend_spending_shift",
                    "Spending shift",
                    f"Redirect about {_format_php(shift_amount)} from Want transactions toward "
                    f"savings or debt reduction over the next month to improve balance.",
                    section="recommendation",
                    severity="warning",
                    metrics={"shift_amount": float(shift_amount)},
                )
            )

    budget_summary = summary.get("budget_summary", {})
    if budget_summary and budget_summary.get("remaining_budget", 0) > 0:
        remaining = budget_summary.get("remaining_budget", 0)
        recommendations.append(
            _make_insight(
                "recommend_savings_target",
                "Savings target",
                f"Allocate the unused budget headroom of {_format_php(remaining)} to savings or "
                f"emergency fund contributions before the period ends.",
                section="recommendation",
                severity="info",
                metrics={"remaining_budget": float(remaining)},
            )
        )

    return _sort_insights(recommendations)


def _processed_recommendations(summary):
    recommendations = []
    budget_rows = summary.get("budget_by_category", {})
    if budget_rows:
        overspent = [
            (category, values)
            for category, values in budget_rows.items()
            if values.get("total_spent", 0) > values.get("total_budget", 0)
        ]
        if overspent:
            category, values = max(
                overspent,
                key=lambda item: item[1].get("total_spent", 0)
                - item[1].get("total_budget", 0),
            )
            gap = values.get("total_spent", 0) - values.get("total_budget", 0)
            recommendations.append(
                _make_insight(
                    "recommend_processed_budget_cap",
                    "Budget cap",
                    f"Prioritize {category} in the next budget cycle and hold spending to "
                    f"{_format_php(values.get('total_budget', 0))} to recover "
                    f"{_format_php(gap)} in variance.",
                    section="recommendation",
                    severity="critical",
                    metrics={"category": category, "gap": gap},
                )
            )

    savings_rate = summary.get("average_savings_rate")
    if savings_rate is not None and savings_rate < 15:
        recommendations.append(
            _make_insight(
                "recommend_processed_savings",
                "Savings target",
                f"Increase the monthly savings rate from {savings_rate:.2f}% toward the 15% "
                f"target used in the financial health score.",
                section="recommendation",
                severity="warning",
                metrics={"savings_rate": savings_rate},
            )
        )

    debt_ratio = summary.get("average_debt_ratio")
    if debt_ratio is not None and debt_ratio > 30:
        recommendations.append(
            _make_insight(
                "recommend_debt_management",
                "Debt management",
                f"Average debt ratio is {debt_ratio:.2f}%. Consider reducing discretionary "
                f"spending or refinancing high-interest debt to move closer to the 36% DTI "
                f"reference threshold.",
                section="recommendation",
                severity="warning",
                metrics={"debt_ratio": debt_ratio},
            )
        )

    emergency = summary.get("emergency_fund_summary", {})
    consistency = emergency.get("consistency_rate_percent")
    if consistency is not None and consistency < 75:
        recommendations.append(
            _make_insight(
                "recommend_emergency_savings",
                "Emergency savings",
                f"Set a fixed monthly emergency fund contribution to improve the current "
                f"{consistency:.2f}% consistency rate across observed months.",
                section="recommendation",
                severity="warning",
                metrics={"consistency_percent": consistency},
            )
        )

    return _sort_insights(recommendations)


def _build_conclusions(summary, net_amount=None, refund_total=None):
    if summary and summary.get("is_processed_summary"):
        total_expenses = summary.get("gross_expense_total", 0)
        health_score = summary.get("latest_financial_health_score")
        score_text = f"{health_score:.2f}" if health_score is not None else "N/A"
        text = (
            f"The processed view combines income, expenses, savings, debt payments, and monthly "
            f"health scoring. Total processed expenses are {_format_php(total_expenses)} and "
            f"the latest financial health score is {score_text} out of 100."
        )
    else:
        net_amount = net_amount if net_amount is not None else summary.get("net_amount", 0)
        refund_total = refund_total if refund_total is not None else summary.get(
            "refund_total", 0
        )
        text = (
            f"The dashboard should be interpreted using three separate measures: positive "
            f"expenses for spending behavior, refunds for adjustments, and net amount for final "
            f"cash impact. Under this view, the current net amount is {_format_php(net_amount)} "
            f"after refunds totaling {_format_php(refund_total)}."
        )

    return [
        _make_insight(
            "analytical_conclusion",
            "Analytical conclusion",
            text,
            section="conclusion",
            severity="info",
        )
    ]


def _build_export_text(bundle, filter_note):
    lines = ["FinSys Insights", filter_note, ""]
    for section_name, key in [
        ("Key priorities", "priorities"),
        ("Findings", "findings"),
        ("Recommendations", "recommendations"),
        ("Conclusion", "conclusions"),
    ]:
        items = bundle.get(key, [])
        if not items:
            continue
        lines.append(section_name)
        lines.append("-" * len(section_name))
        for item in items:
            lines.append(f"- {item['kind']}: {item['text']}")
        lines.append("")
    return "\n".join(lines).strip()


def generate_insight_bundle(df, summary=None):
    """Generate prioritized findings, recommendations, and conclusions."""
    empty_bundle = {
        "priorities": [],
        "findings": [],
        "recommendations": [],
        "conclusions": [
            _make_insight(
                "empty_data",
                "Analytical conclusion",
                "No insight can be generated because the selected data is empty.",
                section="conclusion",
                severity="info",
            )
        ],
        "filter_note": _filter_context_note(summary),
        "export_text": "",
    }

    if summary and summary.get("is_processed_summary"):
        findings = _processed_findings(summary)
        recommendations = _processed_recommendations(summary)
        conclusions = _build_conclusions(summary)
    else:
        insight_df = _prepare_insight_data(df)
        if insight_df is None:
            empty_bundle["export_text"] = _build_export_text(
                empty_bundle, empty_bundle["filter_note"]
            )
            return empty_bundle

        summary = summary or get_basic_summary(insight_df)
        findings = _transaction_findings(insight_df, summary)
        recommendations = _transaction_recommendations(insight_df, summary)
        conclusions = _build_conclusions(
            summary,
            net_amount=summary.get("net_amount", 0),
            refund_total=summary.get("refund_total", 0),
        )

    priorities = _sort_insights(findings + recommendations)[:3]
    bundle = {
        "priorities": priorities,
        "findings": findings,
        "recommendations": recommendations,
        "conclusions": conclusions,
        "filter_note": _filter_context_note(summary),
    }
    bundle["export_text"] = _build_export_text(bundle, bundle["filter_note"])
    return bundle


def insight_to_legacy_string(insight):
    """Convert a structured insight to the legacy label-colon-text format."""
    return f"{insight['kind']}: {insight['text']}"


def generate_insights(df, summary=None):
    """Generate analytical findings from the filtered dashboard data."""
    bundle = generate_insight_bundle(df, summary=summary)
    legacy_items = []
    for key in ("findings", "recommendations", "conclusions"):
        legacy_items.extend(insight_to_legacy_string(item) for item in bundle[key])
    return legacy_items or [
        "Analytical conclusion: No insight can be generated because the selected data is empty."
    ]


def generate_placeholder_insights(df, summary=None):
    """Backward-compatible wrapper for the dashboard import."""
    return generate_insights(df, summary=summary)
