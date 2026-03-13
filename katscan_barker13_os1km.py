"""
katscan_barker13_os1km
~~~~~~~~~~~~~~~~~~~~~~
Standalone Barker-13 coded 8-pulse experiment with oversampled receive output.

Design intent:
- Keep instantaneous coded bandwidth modest (~12 kHz with 83-us chips).
- Increase receive sample rate so pulse-compressed outputs can be produced on a
  ~1-km grid (0.75 km sample spacing at 200 kHz output).

Important:
- Oversampling improves grid spacing only.
- True range resolution is still set by effective signal bandwidth.
"""

from __future__ import annotations

import numpy as np

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype


BARKER13 = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.int8)
BASE_SEQUENCE_8P = scf.SEQUENCE_8P
BASE_TAU_US = scf.TAU_SPACING_8P


def _build_chip_sequence(
    base_sequence: list[int],
    base_tau_us: int,
    chip_us: int,
    chips_per_pulse: int,
) -> list[int]:
    """Expand each coarse pulse into contiguous chip pulses on a chip_us grid."""
    coarse_starts = [int(round(p * base_tau_us / chip_us)) for p in base_sequence]

    chip_sequence: list[int] = []
    for start in coarse_starts:
        chip_sequence.extend(range(start, start + chips_per_pulse))

    if any(b <= a for a, b in zip(chip_sequence, chip_sequence[1:])):
        raise ValueError("chip pulse sequence must be strictly increasing")

    return chip_sequence


def barker13_phase_encode(_beam_iter, _sequence_num, num_pulses):
    """Per-chip BPSK phases in degrees (0/180), repeated per coarse pulse."""
    chips_per_pulse = len(BARKER13)
    expected = len(BASE_SEQUENCE_8P) * chips_per_pulse
    if num_pulses != expected:
        raise ValueError(f"Expected {expected} pulses, got {num_pulses}")

    phase = np.zeros(num_pulses, dtype=np.float64)
    chip_phase = np.where(BARKER13 > 0, 0.0, 180.0)
    for i in range(len(BASE_SEQUENCE_8P)):
        start = i * chips_per_pulse
        phase[start : start + chips_per_pulse] = chip_phase
    return phase


def oversampled_rx_scheme(output_rate_hz: float = 200_000.0) -> dm.DecimationScheme:
    """Single-stage decimation to high-rate output for oversampled pulse compression."""
    sample_rate = 5.0e6
    dm_rate = int(round(sample_rate / output_rate_hz))

    if not np.isclose(sample_rate / dm_rate, output_rate_hz, atol=1.0):
        raise ValueError(
            f"output_rate_hz={output_rate_hz} is not an integer decimation of 5 MHz"
        )

    # Wide enough passband to preserve the coded waveform while staying conservative.
    transition_hz = 20e3
    cutoff_hz = 60e3
    ripple_db = 80
    scale = 1000.0

    taps = scale * dm.create_firwin_filter_by_attenuation(
        sample_rate,
        transition_hz,
        cutoff_hz,
        ripple_db,
    )

    stage = dm.DecimationStage(0, sample_rate, dm_rate, taps.tolist())
    return dm.DecimationScheme(sample_rate, sample_rate / dm_rate, stages=[stage])


class KatscanBarker13OS1Km(ExperimentPrototype):
    cpid = 3922

    def __init__(self, **kwargs):
        """
        kwargs:
        - freq (kHz), default COMMON_MODE_FREQ_1
        - intt_ms, default INTT_MS
        - first_range_km, default 180
        - num_ranges, default 40 (~first 500 km at 83-us coarse range spacing)
        - chip_us, default 83
        - output_rx_rate_hz, default 200000

        This mode is intended for IQ capture plus standalone matched filtering.
        """
        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        intt_ms = int(kwargs.get("intt_ms", scf.INTT_MS))
        first_range_km = float(kwargs.get("first_range_km", scf.STD_FIRST_RANGE))
        num_ranges = int(kwargs.get("num_ranges", 40))
        chip_us = int(kwargs.get("chip_us", 83))
        output_rx_rate_hz = float(kwargs.get("output_rx_rate_hz", 200_000.0))

        sample_spacing_km = 299_792_458.0 / (2.0 * output_rx_rate_hz) / 1000.0
        comment = (
            f"Katscan Barker-13 oversampled RX (1-km grid product); "
            f"rx_sample_spacing_km={sample_spacing_km:.3f}"
        )
        super().__init__(comment_string=comment)

        chips_per_pulse = len(BARKER13)
        chip_sequence = _build_chip_sequence(
            BASE_SEQUENCE_8P,
            BASE_TAU_US,
            chip_us,
            chips_per_pulse,
        )

        self.add_slice(
            {
                "pulse_sequence": chip_sequence,
                "tau_spacing": chip_us,
                "pulse_len": chip_us,
                "num_ranges": num_ranges,
                "first_range": first_range_km,
                "intt": intt_ms,
                "beam_angle": scf.STD_BEAM_ANGLES,
                "rx_beam_order": scf.STD_BEAM_ORDER,
                "tx_beam_order": scf.STD_BEAM_ORDER,
                "scanbound": scf.STD_SCANBOUND,
                "freq": freq,
                "decimation_scheme": oversampled_rx_scheme(output_rx_rate_hz),
                "pulse_phase_offset": barker13_phase_encode,
                "acf": False,
                "xcf": False,
                "acfint": False,
                "wait_for_first_scanbound": False,
            }
        )
