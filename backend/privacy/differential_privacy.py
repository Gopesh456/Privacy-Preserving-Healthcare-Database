"""
Differential Privacy Engine.
Implements calibrated Laplace and Gaussian perturbation mechanisms for statistical queries,
sensitivity calculation, confidence interval derivation, minimum cohort suppression,
and a session Privacy Budget Accountant (epsilon, delta).
"""

import math
import numpy as np
from typing import Dict, Any, Tuple, Optional

class PrivacyBudgetExhaustedError(Exception):
    """Raised when a query demands more epsilon than remaining in the researcher's budget."""
    pass

class SmallCohortSuppressionError(Exception):
    """Raised when the cohort size is too small (< threshold) to safely release without re-identification."""
    pass

class DifferentialPrivacyEngine:
    def __init__(self, total_epsilon_budget: float = 10.0, min_cohort_threshold: int = 5):
        self.total_budget = total_epsilon_budget
        self.remaining_budget = total_epsilon_budget
        self.min_cohort_threshold = min_cohort_threshold
        self.query_history = []

    def check_and_deduct_budget(self, epsilon: float, query_desc: str):
        if epsilon <= 0:
            raise ValueError("Epsilon must be strictly positive.")
        if epsilon > self.remaining_budget:
            raise PrivacyBudgetExhaustedError(
                f"Privacy budget exceeded! Requested ε={epsilon:.2f}, but only ε={self.remaining_budget:.2f} remaining."
            )
        self.remaining_budget -= epsilon
        self.query_history.append({
            "query": query_desc,
            "epsilon_spent": epsilon,
            "remaining_budget": round(self.remaining_budget, 4)
        })

    def reset_budget(self, new_budget: Optional[float] = None):
        if new_budget:
            self.total_budget = new_budget
        self.remaining_budget = self.total_budget
        self.query_history.clear()

    def get_budget_status(self) -> Dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "remaining_budget": round(self.remaining_budget, 3),
            "consumed_budget": round(self.total_budget - self.remaining_budget, 3),
            "percentage_used": round(((self.total_budget - self.remaining_budget) / self.total_budget) * 100, 1),
            "query_count": len(self.query_history)
        }

    def laplace_mechanism(
        self,
        true_value: float,
        epsilon: float,
        sensitivity: float = 1.0,
        enforce_suppression: bool = True
    ) -> Dict[str, Any]:
        """
        Applies Laplace noise calibrated to Delta f / epsilon.
        For count queries, global sensitivity Delta f = 1.
        """
        # Cell suppression rule (HIPAA / Safe Harbor guideline: counts < 5 should not be released)
        if enforce_suppression and true_value < self.min_cohort_threshold:
            raise SmallCohortSuppressionError(
                f"Cohort size is too small ({int(true_value)} < {self.min_cohort_threshold}). "
                "Query suppressed to prevent single-patient re-identification."
            )

        scale = sensitivity / epsilon
        # Generate Laplace noise: Lap(scale)
        noise = float(np.random.laplace(loc=0.0, scale=scale))
        perturbed_value = max(0.0, true_value + noise)  # Count/size cannot be negative

        # Theoretical 95% Confidence Interval for Laplace:
        # P(|X| <= b * ln(1/alpha)) = 1 - alpha. For 95%, alpha=0.05 -> ln(20) ~ 2.9957
        ci_margin = scale * math.log(1.0 / 0.05)
        ci_lower = max(0.0, perturbed_value - ci_margin)
        ci_upper = perturbed_value + ci_margin

        # Variance of Laplace(scale) = 2 * scale^2
        variance = 2.0 * (scale ** 2)
        std_dev = math.sqrt(variance)

        return {
            "true_value": round(true_value, 2),
            "perturbed_value": round(perturbed_value, 1),
            "noise_added": round(noise, 2),
            "epsilon": epsilon,
            "sensitivity": sensitivity,
            "scale": round(scale, 4),
            "variance": round(variance, 4),
            "std_dev": round(std_dev, 2),
            "confidence_interval_95": {
                "lower": round(ci_lower, 1),
                "upper": round(ci_upper, 1),
                "margin": round(ci_margin, 1)
            }
        }

    def gaussian_mechanism(
        self,
        true_value: float,
        epsilon: float,
        delta: float = 1e-5,
        sensitivity: float = 1.0
    ) -> Dict[str, Any]:
        """
        (epsilon, delta)-Differential Privacy via Gaussian Mechanism.
        sigma = sqrt(2 * ln(1.25 / delta)) * (sensitivity / epsilon)
        """
        sigma = math.sqrt(2 * math.log(1.25 / delta)) * (sensitivity / epsilon)
        noise = float(np.random.normal(loc=0.0, scale=sigma))
        perturbed_value = max(0.0, true_value + noise)

        ci_margin = 1.96 * sigma
        ci_lower = max(0.0, perturbed_value - ci_margin)
        ci_upper = perturbed_value + ci_margin

        return {
            "true_value": round(true_value, 2),
            "perturbed_value": round(perturbed_value, 1),
            "noise_added": round(noise, 2),
            "epsilon": epsilon,
            "delta": delta,
            "sigma": round(sigma, 4),
            "confidence_interval_95": {
                "lower": round(ci_lower, 1),
                "upper": round(ci_upper, 1),
                "margin": round(ci_margin, 1)
            }
        }
