"""
normalscan_500khz
~~~~~~~~~~~~~~~~~
Standard normalscan-style experiment with 500 kHz TX/RX bandwidth.

:copyright: 2026 SuperDARN APL
"""

import math

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype

LAB_FREQ_MIN_KHZ = 9000
LAB_FREQ_MAX_KHZ = 18000
CENTER_GUARD_KHZ = 0.1


def decimation_500khz():
    """
    Build a decimation scheme for 500 kHz input and 3.333 kHz output.

    Total decimation is 150 (10 * 15), so:
        500000 / 150 = 3333.333... Hz
    """
    sample_rate = 500e3
    dm_rates = [10, 15]
    transition_widths = [40e3, 8e3]
    cutoffs = [10e3, 5e3]
    ripple_dbs = [115, 50]
    scaling_factors = [1000.0, 10000.0]

    stages = []
    dm_rate_so_far = 1
    for i, dm_rate in enumerate(dm_rates):
        rate = sample_rate / dm_rate_so_far
        taps = scaling_factors[i] * dm.create_firwin_filter_by_attenuation(
            rate,
            transition_widths[i],
            cutoffs[i],
            ripple_dbs[i],
        )
        stages.append(dm.DecimationStage(i, rate, dm_rate, taps.tolist()))
        dm_rate_so_far *= dm_rate

    return dm.DecimationScheme(sample_rate, sample_rate / dm_rate_so_far, stages=stages)


def auto_center_freq_khz(freq_khz: int, bandwidth_hz: float, preferred_offset_khz: float) -> float:
    """
    Compute a hardware-valid center frequency that keeps the operating frequency
    safely inside the slice passband after USRP clock quantization.
    """
    half_usable_khz = 0.35 * (bandwidth_hz / 1e3)
    min_center_khz = freq_khz + 50 + CENTER_GUARD_KHZ
    max_center_khz = freq_khz + half_usable_khz - CENTER_GUARD_KHZ
    if min_center_khz > max_center_khz:
        raise ValueError(
            f"No valid center frequency for freq={freq_khz} kHz and bandwidth={bandwidth_hz} Hz"
        )

    target_center_khz = freq_khz + preferred_offset_khz
    target_center_khz = min(max(target_center_khz, min_center_khz), max_center_khz)

    clock_multiple_hz = scf.config.usrp_master_clock_rate / 2**32
    min_divider = math.ceil(min_center_khz * 1e3 / clock_multiple_hz)
    max_divider = math.floor(max_center_khz * 1e3 / clock_multiple_hz)
    if min_divider > max_divider:
        raise ValueError(
            f"No quantized center frequency for freq={freq_khz} kHz and bandwidth={bandwidth_hz} Hz"
        )

    target_divider = math.ceil(target_center_khz * 1e3 / clock_multiple_hz)
    divider = min(max(target_divider, min_divider), max_divider)
    return (divider * clock_multiple_hz) / 1e3


class Normalscan500khz(ExperimentPrototype):
    cpid = 1010

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int
            Operating frequency in kHz.
            Must satisfy 9000 <= freq <= 18000.
        ctr_freq_offset: int, optional
            Preferred offset from operating frequency to TX/RX center frequency in kHz.
            Optional tuning knob; defaults to 100 kHz.
        """
        super().__init__(
            tx_bandwidth=500e3,
            rx_bandwidth=500e3,
            comment_string="Normalscan with 500 kHz TX/RX bandwidth",
        )

        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        if not (LAB_FREQ_MIN_KHZ <= freq <= LAB_FREQ_MAX_KHZ):
            raise ValueError(f"freq must satisfy {LAB_FREQ_MIN_KHZ} <= freq <= {LAB_FREQ_MAX_KHZ} kHz")

        ctr_freq_offset = float(kwargs.get("ctr_freq_offset", 100))
        if abs(ctr_freq_offset) < 50:
            raise ValueError("ctr_freq_offset must have absolute value >= 50 kHz")

        ctr_freq = auto_center_freq_khz(freq, self.tx_bandwidth, ctr_freq_offset)

        self.add_slice(
            {
                "pulse_sequence": scf.SEQUENCE_7P,
                "tau_spacing": scf.TAU_SPACING_7P,
                "pulse_len": scf.PULSE_LEN_45KM,
                "num_ranges": scf.STD_NUM_RANGES,
                "first_range": scf.STD_FIRST_RANGE,
                "intt": scf.INTT_MS,
                "beam_angle": scf.STD_BEAM_ANGLES,
                "rx_beam_order": scf.STD_BEAM_ORDER,
                "tx_beam_order": scf.STD_BEAM_ORDER,
                "scanbound": scf.STD_SCANBOUND,
                "freq": freq,
                # Explicit center frequencies avoid auto-center calc that assumes
                # a wider fixed transition band than 500 kHz.
                "txctrfreq": ctr_freq,
                "rxctrfreq": ctr_freq,
                "acf": True,
                "xcf": True,
                "acfint": True,
                "wait_for_first_scanbound": False,
                "decimation_scheme": decimation_500khz(),
            }
        )
