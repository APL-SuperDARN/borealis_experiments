"""
normalscan_tx_test_singlechan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Single-channel transmitter test experiment that preserves *Normalscan* TX pulse behavior
(5 MHz TX sample rate, 7-pulse timing, scan cadence), while minimizing compute and network load
by using a lower RX sample rate and disabling correlation processing.

Intended use-case: lab testing of a single transmitter chain driven by one N200 channel.
"""

import borealis_experiments.superdarn_common_fields as scf
from borealis_experiments.normalscan_500khz import decimation_500khz
from utils.experiment_prototype import ExperimentPrototype


class NormalscanTxTestSingleChan(ExperimentPrototype):
    """
    Normalscan-like TX on a single channel, reduced RX bandwidth, and no ACF/XCF.

    This keeps the TX waveform generation comparable to field *Normalscan* by keeping:
    - 5 MHz TX sample rate
    - standard 7-pulse sequence timing
    - standard scan cadence (scanbound + beam order)

    While reducing load by:
    - 500 kHz RX sample rate (10x less RX network traffic than 5 MHz)
    - no ACF/XCF/ACFINT processing
    - single TX/RX channel with no interferometer
    """

    cpid = 1819

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int
            Operating frequency in kHz.
        rx_ctr_freq_offset: int
            Offset from operating frequency to RX center frequency in kHz.
            Must satisfy 50 <= abs(offset) <= 175 for 500 kHz bandwidth.
        tx_ctr_freq_offset: int
            Offset from operating frequency to TX center frequency in kHz.
            Defaults to 1750 kHz, matching the typical center frequency placement
            produced by Borealis for 5 MHz TX bandwidth in normalscan-style experiments.
        """
        super().__init__(
            tx_bandwidth=5.0e6,
            rx_bandwidth=500e3,
            comment_string="Normalscan TX test (single channel, 5 MHz TX, 500 kHz RX, no ACF/XCF)",
        )

        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))

        rx_ctr_freq_offset = int(kwargs.get("rx_ctr_freq_offset", 100))
        if not (50 <= abs(rx_ctr_freq_offset) <= 175):
            raise ValueError(
                "rx_ctr_freq_offset must satisfy 50 <= abs(rx_ctr_freq_offset) <= 175 kHz"
            )

        # Keep TX center placement comparable to normalscan's auto-centering for 5 MHz TX.
        tx_ctr_freq_offset = int(kwargs.get("tx_ctr_freq_offset", 1750))
        if abs(tx_ctr_freq_offset) < 50:
            raise ValueError("tx_ctr_freq_offset must have absolute value >= 50 kHz")

        txctrfreq = freq + tx_ctr_freq_offset
        rxctrfreq = freq + rx_ctr_freq_offset

        tx_ant = scf.config.tx_main_antennas[0]
        rx_ant = scf.config.rx_main_antennas[0]

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
                "tx_antennas": [tx_ant],
                "rx_main_antennas": [rx_ant],
                "rx_intf_antennas": [],
                "freq": freq,
                "txctrfreq": txctrfreq,
                "rxctrfreq": rxctrfreq,
                "acf": False,
                "xcf": False,
                "acfint": False,
                "wait_for_first_scanbound": False,
                "decimation_scheme": decimation_500khz(),
            }
        )

