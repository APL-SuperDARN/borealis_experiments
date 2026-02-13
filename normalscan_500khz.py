"""
normalscan_500khz
~~~~~~~~~~~~~~~~~
Standard normalscan-style experiment with 500 kHz TX/RX bandwidth.

:copyright: 2026 SuperDARN APL
"""

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype


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


class Normalscan500khz(ExperimentPrototype):
    cpid = 1010

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int
            Operating frequency in kHz.
        ctr_freq_offset: int
            Offset from operating frequency to TX/RX center frequency in kHz.
            Must be at least 50 kHz away from freq due center-null restrictions.
        """
        super().__init__(
            tx_bandwidth=500e3,
            rx_bandwidth=500e3,
            comment_string="Normalscan with 500 kHz TX/RX bandwidth",
        )

        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        ctr_freq_offset = int(kwargs.get("ctr_freq_offset", 100))
        if abs(ctr_freq_offset) < 50:
            raise ValueError("ctr_freq_offset must have absolute value >= 50 kHz")
        ctr_freq = freq + ctr_freq_offset

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
