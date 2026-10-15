"""Energy-curve helpers (pure functions)."""

from services.chrono_service import (
    DEFAULT_ENERGY_CURVE,
    _energy_label,
    _fit_energy_curve,
    _interpolate_energy,
)


def test_interpolation_returns_exact_values_and_blends_gaps():
    curve = {8: 0.0, 12: 1.0}
    assert _interpolate_energy(8, curve) == 0.0
    assert _interpolate_energy(10, curve) == 0.5
    assert _interpolate_energy(23, curve) == 0.3  # outside the curve -> neutral default


def test_fitted_curve_peaks_at_one_at_the_users_busiest_hour():
    curve = _fit_energy_curve([9, 9, 9, 9, 14, 14, 20])
    assert curve[9] == 1.0
    assert curve[14] == 0.5
    assert curve[20] == 0.25


def test_no_history_uses_the_default_curve():
    assert _fit_energy_curve([]) == DEFAULT_ENERGY_CURVE


def test_energy_labels():
    assert _energy_label(1.0) == "peak"
    assert _energy_label(0.7) == "high"
    assert _energy_label(0.5) == "medium"
    assert _energy_label(0.1) == "low"
