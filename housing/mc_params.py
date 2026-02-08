"""Monte Carlo simulation configuration."""

from dataclasses import dataclass, field

import numpy as np

# Variable ordering used throughout: indices into arrays/matrices
VAR_NAMES = [
    "property_appreciation",
    "investment_return",
    "rent_increase",
    "inflation",
    "mortgage_rate",
]

# Default floors and ceilings for each variable
FLOORS = np.array([-0.20, -0.40, 0.00, 0.00, 0.01])
CEILINGS = np.array([0.30, 0.50, 0.15, 0.12, 0.15])

# Default correlation matrix (5x5, symmetric, positive definite)
#                        prop_appr  inv_ret  rent_inc  inflation  mort_rate
DEFAULT_CORRELATION = np.array([
    [1.00,  0.20,  0.30,  0.40, -0.25],  # property_appreciation
    [0.20,  1.00,  0.05, -0.10, -0.15],  # investment_return
    [0.30,  0.05,  1.00,  0.60,  0.30],  # rent_increase
    [0.40, -0.10,  0.60,  1.00,  0.65],  # inflation
    [-0.25, -0.15,  0.30,  0.65,  1.00],  # mortgage_rate
])


@dataclass
class MCConfig:
    """Configuration for Monte Carlo simulation."""

    n_runs: int = 5_000
    seed: int | None = None

    # Per-variable annual volatility (standard deviation)
    std_property_appreciation: float = 0.10
    std_investment_return: float = 0.15
    std_rent_increase: float = 0.02
    std_inflation: float = 0.015
    std_mortgage_rate: float = 0.01

    # Override correlation matrix (None = use default)
    correlation_override: np.ndarray | None = field(default=None, repr=False)

    def std_vector(self) -> np.ndarray:
        """Return (5,) array of standard deviations in variable order."""
        return np.array([
            self.std_property_appreciation,
            self.std_investment_return,
            self.std_rent_increase,
            self.std_inflation,
            self.std_mortgage_rate,
        ])

    def correlation_matrix(self) -> np.ndarray:
        """Return 5x5 correlation matrix."""
        if self.correlation_override is not None:
            return self.correlation_override
        return DEFAULT_CORRELATION.copy()


def build_cov_matrix(config: MCConfig) -> np.ndarray:
    """Build 5x5 covariance matrix from config stds and correlations.

    cov[i,j] = corr[i,j] * std[i] * std[j]
    """
    stds = config.std_vector()
    corr = config.correlation_matrix()
    # outer product of stds gives the scaling matrix
    return corr * np.outer(stds, stds)
