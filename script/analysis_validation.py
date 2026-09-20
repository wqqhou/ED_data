"""Checks for divisions in the analysis script; no extra dependencies required."""

import numpy as np
import pandas as pd


def checked_divide(numerator, denominator, *, label="ratio"):
    """Divide numeric scalars/Series, requiring finite values and positive denominators.

    A zero numerator is allowed. Empty Series, missing values, nonfinite results,
    and mismatched Series indexes raise ValueError instead of yielding invalid output.
    """
    if isinstance(numerator, pd.Series) and isinstance(denominator, pd.Series):
        if not numerator.index.equals(denominator.index):
            raise ValueError(f"{label}: numerator and denominator indexes differ.")

    def as_array(value):
        if isinstance(value, pd.Series):
            return value.to_numpy(dtype=float, na_value=np.nan)
        return np.asarray(value, dtype=float)

    for name, value in (("numerator", numerator), ("denominator", denominator)):
        array = as_array(value)
        if array.size == 0:
            raise ValueError(f"{label}: empty {name}.")
        bad = ~np.isfinite(array)
        if name == "denominator":
            bad = bad | (array <= 0)
        if bad.any():
            examples = value.loc[bad].head(5).to_dict() if isinstance(value, pd.Series) else value
            requirement = "finite and strictly positive" if name == "denominator" else "finite"
            raise ValueError(
                f"{label}: {name} must be {requirement}. Invalid values: {examples}"
            )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        result = numerator / denominator
    if not np.isfinite(as_array(result)).all():
        raise ValueError(f"{label}: division produced a non-finite result.")
    return result
