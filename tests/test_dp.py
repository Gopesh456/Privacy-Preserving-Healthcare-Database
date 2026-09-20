"""
Unit tests for Differential Privacy Engine.
Verifies Laplace & Gaussian mechanisms, confidence intervals,
budget tracking, and small-cohort suppression.
"""

import math
from backend.privacy.differential_privacy import (
    DifferentialPrivacyEngine,
    PrivacyBudgetExhaustedError,
    SmallCohortSuppressionError
)

def test_laplace_mechanism_output():
    dp = DifferentialPrivacyEngine(total_epsilon_budget=10.0)
    true_count = 100.0
    epsilon = 1.0

    res = dp.laplace_mechanism(true_count, epsilon, sensitivity=1.0)
    assert res["true_value"] == 100.0
    assert "perturbed_value" in res
    assert res["epsilon"] == 1.0
    assert res["scale"] == 1.0
    assert res["variance"] == 2.0
    assert res["confidence_interval_95"]["lower"] <= res["perturbed_value"]
    assert res["confidence_interval_95"]["upper"] >= res["perturbed_value"]

def test_privacy_budget_exhaustion():
    dp = DifferentialPrivacyEngine(total_epsilon_budget=2.0)
    dp.check_and_deduct_budget(1.5, "Query 1")
    assert dp.remaining_budget == 0.5

    # Should raise error when attempting to spend 1.0 with only 0.5 remaining
    caught = False
    try:
        dp.check_and_deduct_budget(1.0, "Query 2")
    except PrivacyBudgetExhaustedError:
        caught = True
    assert caught, "Expected PrivacyBudgetExhaustedError was not raised"

def test_small_cohort_suppression():
    dp = DifferentialPrivacyEngine(min_cohort_threshold=5)
    caught = False
    try:
        dp.laplace_mechanism(true_value=3.0, epsilon=1.0, enforce_suppression=True)
    except SmallCohortSuppressionError:
        caught = True
    assert caught, "Expected SmallCohortSuppressionError was not raised"

    # When suppression is disabled, should allow execution
    res = dp.laplace_mechanism(true_value=3.0, epsilon=1.0, enforce_suppression=False)
    assert res["true_value"] == 3.0

def test_gaussian_mechanism():
    dp = DifferentialPrivacyEngine()
    res = dp.gaussian_mechanism(true_value=50.0, epsilon=1.0, delta=1e-5)
    assert res["true_value"] == 50.0
    assert "perturbed_value" in res
    assert res["delta"] == 1e-5
    assert res["sigma"] > 0
