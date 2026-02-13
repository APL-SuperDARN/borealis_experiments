"""
normalscan_500khz_singlechan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Low-compute transmitter test mode using normalscan-style 7-pulse timing
at 500 kHz TX/RX bandwidth on a single TX/RX channel.

:copyright: 2026 SuperDARN Canada
"""

import borealis_experiments.superdarn_common_fields as scf
from borealis_experiments.normalscan_500khz import decimation_500khz
from utils.experiment_prototype import ExperimentPrototype


class Normalscan500khzSingleChan(ExperimentPrototype):
    cpid = 1818

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
            comment_string="Normalscan 7-pulse timing at 500 kHz on a single channel",
        )

        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        ctr_freq_offset = int(kwargs.get("ctr_freq_offset", 100))
        if abs(ctr_freq_offset) < 50:
            raise ValueError("ctr_freq_offset must have absolute value >= 50 kHz")
        ctr_freq = freq + ctr_freq_offset

        tx_ant = scf.config.tx_main_antennas[0]
        rx_ant = scf.config.rx_main_antennas[0]

        self.add_slice(
            {
                "pulse_sequence": scf.SEQUENCE_7P,
                "tau_spacing": scf.TAU_SPACING_7P,
                "pulse_len": scf.PULSE_LEN_45KM,
                "num_ranges": 1,
                "first_range": scf.STD_FIRST_RANGE,
                "intt": scf.INTT_MS,
                "beam_angle": [0.0],
                "rx_beam_order": [0],
                "tx_beam_order": [0],
                "tx_antennas": [tx_ant],
                "rx_main_antennas": [rx_ant],
                "rx_intf_antennas": [],
                "freq": freq,
                "txctrfreq": ctr_freq,
                "rxctrfreq": ctr_freq,
                "acf": False,
                "xcf": False,
                "acfint": False,
                "wait_for_first_scanbound": False,
                "decimation_scheme": decimation_500khz(),
            }
        )
