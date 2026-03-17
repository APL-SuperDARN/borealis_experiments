#!/usr/bin/python
"""
full_fov_barker13
~~~~~~~~~~~~~~~
Full-FOV widebeam experiment using Barker-13 phase coding for offline pulse
compression and standard receive beamforming across the full SuperDARN FOV.
"""

from __future__ import annotations

import numpy as np

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype


BARKER13 = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.int8)
BASE_SEQUENCE_7P = scf.SEQUENCE_7P
BASE_TAU_US = scf.TAU_SPACING_7P


def _build_chip_sequence(base_sequence: list[int], base_tau_us: int, chip_us: int, chips_per_pulse: int) -> list[int]:
    # Borealis schedules pulse times, not arbitrary intra-pulse chip boundaries. Expand each coarse
    # 7-pulse slot into contiguous chip pulses so Barker coding can be emitted without DSP changes.
    coarse_starts = [int(round(p * base_tau_us / chip_us)) for p in base_sequence]

    chip_sequence: list[int] = []
    for start in coarse_starts:
        chip_sequence.extend(range(start, start + chips_per_pulse))

    if any(b <= a for a, b in zip(chip_sequence, chip_sequence[1:])):
        raise ValueError("chip pulse sequence must be strictly increasing")

    return chip_sequence


def barker13_phase_encode(_beam_iter, _sequence_num, num_pulses):
    chips_per_pulse = len(BARKER13)
    expected = len(BASE_SEQUENCE_7P) * chips_per_pulse
    if num_pulses != expected:
        raise ValueError(f"Expected {expected} pulses, got {num_pulses}")

    phase = np.zeros(num_pulses, dtype=np.float64)
    # Map Barker +1/-1 chips to BPSK phase flips in degrees.
    chip_phase = np.where(BARKER13 > 0, 0.0, 180.0)
    for i in range(len(BASE_SEQUENCE_7P)):
        start = i * chips_per_pulse
        phase[start : start + chips_per_pulse] = chip_phase
    return phase


def oversampled_rx_scheme(output_rate_hz: float = 200_000.0) -> dm.DecimationScheme:
    sample_rate = 5.0e6
    dm_rate = int(round(sample_rate / output_rate_hz))

    if not np.isclose(sample_rate / dm_rate, output_rate_hz, atol=1.0):
        raise ValueError(f"output_rate_hz={output_rate_hz} is not an integer decimation of 5 MHz")

    transition_hz = 20e3
    cutoff_hz = 60e3
    ripple_db = 80
    scale = 1000.0

    # Keep enough coded-waveform bandwidth for offline matched filtering while exporting a denser
    # receive grid than standard rawacf production would use.
    taps = scale * dm.create_firwin_filter_by_attenuation(sample_rate, transition_hz, cutoff_hz, ripple_db)
    stage = dm.DecimationStage(0, sample_rate, dm_rate, taps.tolist())
    return dm.DecimationScheme(sample_rate, sample_rate / dm_rate, stages=[stage])


class FullFOVBarker13(ExperimentPrototype):
    cpid = 3923

    def __init__(self, **kwargs):
        freq_khz = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        intt_ms = int(kwargs.get("intt_ms", scf.INTT_MS))
        num_ranges = int(kwargs.get("num_ranges", scf.STD_NUM_RANGES * 3))
        first_range_km = float(kwargs.get("first_range_km", 90))
        chip_us = int(kwargs.get("chip_us", 83))
        output_rx_rate_hz = float(kwargs.get("output_rx_rate_hz", 200_000.0))

        sample_spacing_km = 299_792_458.0 / (2.0 * output_rx_rate_hz) / 1000.0
        comment = (
            f"Full FOV Barker-13 oversampled RX; rx_sample_spacing_km={sample_spacing_km:.3f}"
        )
        # Include the effective output sample spacing in the experiment comment so downstream IQ
        # analysis can recover the intended pulse-compression grid from the metadata alone.
        super().__init__(comment_string=comment)

        chips_per_pulse = len(BARKER13)
        chip_sequence = _build_chip_sequence(BASE_SEQUENCE_7P, BASE_TAU_US, chip_us, chips_per_pulse)

        self.add_slice(
            {
                "pulse_sequence": chip_sequence,
                "tau_spacing": chip_us,
                "pulse_len": chip_us,
                "num_ranges": num_ranges,
                "first_range": first_range_km,
                "intt": intt_ms,
                "beam_angle": scf.STD_BEAM_ANGLES,
                "rx_beam_order": [[i for i in range(len(scf.STD_BEAM_ANGLES))]],
                "tx_beam_order": [0],
                "tx_antenna_pattern": scf.easy_widebeam,
                "freq": freq_khz,
                "decimation_scheme": oversampled_rx_scheme(output_rx_rate_hz),
                "pulse_phase_offset": barker13_phase_encode,
                # This mode is intended for IQ capture plus offline pulse compression, so skip the
                # real-time ACF/XCF products that assume the uncoded standard processing chain.
                "acf": False,
                "xcf": False,
                "acfint": False,
            }
        )
