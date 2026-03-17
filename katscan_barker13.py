"""
katscan_barker13
~~~~~~~~~~~~~~
Barker-13 coded variant of the SuperDARN 8-pulse (katscan-style) timing.

Implementation note:
- Borealis currently applies pulse_phase_offset per pulse, not per-sample.
- To synthesize intra-pulse Barker chips without touching core signal code,
  each 8-pulse slot is expanded into contiguous chip pulses.
- This is intended for IQ capture and offline matched filtering / A-B tests.
"""

import numpy as np

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype


# ~12 kHz occupied bandwidth target.
CHIP_US = 83
CHIPS_PER_PULSE = 13
BASE_TAU_US = scf.TAU_SPACING_8P  # 1500 us
BASE_SEQUENCE_8P = scf.SEQUENCE_8P

# +/-1 Barker-13 chips.
BARKER13 = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.int8)


def _build_chip_sequence(base_sequence, base_tau_us, chip_us, chips_per_pulse):
    """
    Expand each coarse pulse into contiguous chip pulses.

    Because slice timing is integer microseconds, we approximate 1500-us katscan
    spacing on the CHIP_US grid by rounding each coarse pulse start.
    """
    coarse_starts = [int(round(p * base_tau_us / chip_us)) for p in base_sequence]

    chip_sequence = []
    for start in coarse_starts:
        chip_sequence.extend(range(start, start + chips_per_pulse))

    if any(b <= a for a, b in zip(chip_sequence, chip_sequence[1:])):
        raise ValueError("chip pulse sequence must be strictly increasing")

    return chip_sequence


CHIP_SEQUENCE = _build_chip_sequence(
    BASE_SEQUENCE_8P,
    BASE_TAU_US,
    CHIP_US,
    CHIPS_PER_PULSE,
)


def barker13_phase_encode(_beam_iter, _sequence_num, num_pulses):
    """Return per-chip BPSK phases in degrees, repeated for each coarse pulse."""
    expected = len(BASE_SEQUENCE_8P) * CHIPS_PER_PULSE
    if num_pulses != expected:
        raise ValueError(f"Expected {expected} pulses, got {num_pulses}")

    phase = np.zeros(num_pulses, dtype=np.float64)
    chip_phase = np.where(BARKER13 > 0, 0.0, 180.0)
    for i in range(len(BASE_SEQUENCE_8P)):
        start = i * CHIPS_PER_PULSE
        phase[start : start + CHIPS_PER_PULSE] = chip_phase
    return phase


def filter_coded_mode():
    """Conservative decimation profile used for IQ-first coded mode."""
    sample_rate = 5e6
    dm_rate = [25, 20]
    transition_width = [150e3, 30e3]
    cutoff_hz = [10e3, 5e3]
    ripple_db = [115, 50]
    scaling_factors = [1000.0, 10000.0]

    dm_rate_so_far = 1
    stages = []

    taps = scaling_factors[0] * dm.create_firwin_filter_by_attenuation(
        sample_rate, transition_width[0], cutoff_hz[0], ripple_db[0]
    )
    stages.append(dm.DecimationStage(0, sample_rate, dm_rate[0], taps.tolist()))
    dm_rate_so_far *= dm_rate[0]

    taps = scaling_factors[1] * dm.create_firwin_filter_by_num_taps(
        sample_rate / dm_rate_so_far, cutoff_hz[1], 41
    )
    stages.append(
        dm.DecimationStage(1, sample_rate / dm_rate_so_far, dm_rate[1], taps.tolist())
    )

    return dm.DecimationScheme(sample_rate, sample_rate / (25 * 20), stages=stages)


class KatscanBarker13(ExperimentPrototype):
    cpid = 3921

    def __init__(self, **kwargs):
        """
        kwargs:
        freq: int (kHz)

        IQ-focused coded mode for offline pulse compression. Uses the 8-pulse
        katscan timing skeleton and 13 BPSK chips per coarse pulse.
        """
        super().__init__(comment_string="Katscan Barker-13 coded (83us chips, IQ-first)")

        freq = kwargs.get("freq", scf.COMMON_MODE_FREQ_1)

        self.add_slice(
            {
                # Reuse the standard katscan timing skeleton, but replace each coarse pulse with a
                # run of Barker chips so matched filtering can be done from saved IQ later.
                "pulse_sequence": CHIP_SEQUENCE,
                "tau_spacing": CHIP_US,
                "pulse_len": CHIP_US,
                "num_ranges": scf.STD_NUM_RANGES,
                "first_range": scf.STD_FIRST_RANGE,
                "intt": scf.INTT_MS,
                "beam_angle": scf.STD_BEAM_ANGLES,
                "rx_beam_order": scf.STD_BEAM_ORDER,
                "tx_beam_order": scf.STD_BEAM_ORDER,
                "scanbound": scf.STD_SCANBOUND,
                "freq": freq,
                "decimation_scheme": filter_coded_mode(),
                "pulse_phase_offset": barker13_phase_encode,
                # As with the FullFOV coded mode, these products are meant for offline decoding
                # rather than real-time ACF/XCF generation inside Borealis.
                "acf": False,
                "xcf": False,
                "acfint": False,
                "wait_for_first_scanbound": False,
            }
        )
