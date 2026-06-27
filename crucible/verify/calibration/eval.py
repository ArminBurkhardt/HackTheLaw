"""SECV calibration eval — AUROC + confusion matrix.

Usage (requires Neo4j + credentials):
    python -m crucible.verify.calibration.eval [--theta-high 0.7] [--M 5]
"""
from __future__ import annotations
import sys


def auroc(y_true: list[bool], scores: list[float]) -> float:
    """Trapezoidal AUROC — no external dependencies required."""
    pairs = sorted(zip(scores, y_true), key=lambda t: t[0], reverse=True)
    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 1.0  # degenerate — treat as perfect
    tp = fp = area = 0.0
    prev_tp = prev_fp = 0.0
    for _, label in pairs:
        if label:
            tp += 1
        else:
            fp += 1
        area += (fp - prev_fp) * (tp + prev_tp) / 2
        prev_tp, prev_fp = tp, fp
    return area / (n_pos * n_neg)


def confusion(y_true: list[bool], y_pred: list[bool]) -> dict[str, int]:
    tp = sum(int(a and b) for a, b in zip(y_true, y_pred))
    tn = sum(int(not a and not b) for a, b in zip(y_true, y_pred))
    fp = sum(int(not a and b) for a, b in zip(y_true, y_pred))
    fn = sum(int(a and not b) for a, b in zip(y_true, y_pred))
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn}


def run_eval(
    examples: list[dict],
    store,
    model_client,
    model: str,
    entailment_oracle=None,
    M: int = 5,
    theta_high: float = 0.7,
) -> dict:
    """Run SECV on every example and return auroc, confusion, scores, labels."""
    from crucible.verify.secv import verify_citation

    scores: list[float] = []
    labels: list[bool] = []
    predictions: list[bool] = []

    for ex in examples:
        result = verify_citation(
            claim=ex["claim"],
            celex=ex["celex"],
            pinpoint=ex.get("pinpoint"),
            store=store,
            model_client=model_client,
            model=model,
            entailment_oracle=entailment_oracle,
            M=M,
            theta_high=theta_high,
        )
        scores.append(result.citation_score)
        labels.append(bool(ex["correct"]))
        predictions.append(result.status == "verified")

    auc = auroc(labels, scores)
    cm = confusion(labels, predictions)
    return {"auroc": auc, "confusion": cm, "scores": scores, "labels": labels}


if __name__ == "__main__":
    import argparse
    from crucible.config import get_settings
    from crucible.agents.base import make_client
    from crucible.verify.calibration.examples import LABELLED_EXAMPLES

    parser = argparse.ArgumentParser(description="SECV calibration eval")
    parser.add_argument("--theta-high", type=float, default=0.7)
    parser.add_argument("--M", type=int, default=5)
    args = parser.parse_args()

    settings = get_settings()

    try:
        from crucible.grounding.cellar.neo4j_store import Neo4jGraphStore
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        store = Neo4jGraphStore(driver)
    except Exception as exc:
        print(f"ERROR: Could not connect to Neo4j: {exc}", file=sys.stderr)
        sys.exit(1)

    client = make_client(settings)
    model = settings.get_entailment_model()

    results = run_eval(
        LABELLED_EXAMPLES,
        store=store,
        model_client=client,
        model=model,
        M=args.M,
        theta_high=args.theta_high,
    )

    print(f"\nAUROC: {results['auroc']:.3f}")
    print(f"Confusion: {results['confusion']}")
    print()
    for ex, score, label in zip(LABELLED_EXAMPLES, results["scores"], results["labels"]):
        ok = (score >= args.theta_high) == label
        mark = "✓" if ok else "✗"
        print(f"  {mark} [{ex['id']:40s}] score={score:.2f}  correct={label}")
