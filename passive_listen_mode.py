"""
passive_listen_mode
~~~~~~~~~~~~~~~~~
Purpose-built receive-only passive listening mode for external HF signals such as
CHU, WWV, and other narrowband sources within the SuperDARN tuning range.

Designed for later per-channel audio rendering from the captured receive data.
"""

import borealis_experiments.superdarn_common_fields as scf
import math
from borealis_experiments.normalscan_500khz import auto_center_freq_khz, decimation_500khz
from utils.experiment_prototype import ExperimentPrototype

LISTEN_FREQ_MIN_KHZ = 8000
LISTEN_FREQ_MAX_KHZ = 20000


class PassiveListenMode(ExperimentPrototype):
    cpid = 1820

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int
            Listening frequency in kHz.
            Examples: 14670 for CHU, 10000 for WWV.
        intt_ms: int, optional
            Receive integration length in milliseconds. Default 4000.
        rx_bandwidth_khz: int, optional
            Receive bandwidth in kHz. Default 500.
        rx_ctr_freq_offset: float, optional
            Requested RX center offset from `freq` in kHz. Default 100.
            Must satisfy abs(rx_ctr_freq_offset) >= 50.
        beam: int, optional
            Receive beam index. Default 0 (boresight-style single beam product).
        include_intf: bool/int/str, optional
            Include interferometer channels. Default True.
        """
        freq = int(kwargs.get("freq", 14670))
        if not (LISTEN_FREQ_MIN_KHZ <= freq <= LISTEN_FREQ_MAX_KHZ):
            raise ValueError(
                f"freq must satisfy {LISTEN_FREQ_MIN_KHZ} <= freq <= {LISTEN_FREQ_MAX_KHZ} kHz"
            )

        intt_ms = int(kwargs.get("intt_ms", 4000))
        if intt_ms <= 0:
            raise ValueError("intt_ms must be positive")

        raw_window_ms = float(kwargs.get("raw_window_ms", 500.0))
        if raw_window_ms <= 0:
            raise ValueError("raw_window_ms must be positive")

        rx_bandwidth_khz = int(kwargs.get("rx_bandwidth_khz", 500))
        if rx_bandwidth_khz != 500:
            raise ValueError("rx_bandwidth_khz currently must be 500")

        rx_ctr_freq_offset = float(kwargs.get("rx_ctr_freq_offset", 100.0))
        if abs(rx_ctr_freq_offset) < 50:
            raise ValueError("rx_ctr_freq_offset must satisfy abs(rx_ctr_freq_offset) >= 50 kHz")

        beam = int(kwargs.get("beam", 0))
        if beam < 0 or beam >= len(scf.STD_BEAM_ANGLES):
            raise ValueError(f"beam must satisfy 0 <= beam < {len(scf.STD_BEAM_ANGLES)}")

        include_intf_raw = kwargs.get("include_intf", True)
        if isinstance(include_intf_raw, str):
            include_intf = include_intf_raw.strip().lower() not in {"0", "false", "no", "off"}
        else:
            include_intf = bool(include_intf_raw)

        rx_bandwidth_hz = rx_bandwidth_khz * 1.0e3
        rxctrfreq = auto_center_freq_khz(freq, rx_bandwidth_hz, rx_ctr_freq_offset)

        pulse_len_us = scf.PULSE_LEN_45KM
        decimation = decimation_500khz()
        dm_rate = math.prod(stage.dm_rate for stage in decimation.stages)
        output_rx_rate_hz = rx_bandwidth_hz / dm_rate
        output_sample_period_us = 1.0e6 / output_rx_rate_hz
        requested_tau_us = max(raw_window_ms * 1000.0, pulse_len_us)
        tau_spacing_us = int(round(requested_tau_us / output_sample_period_us) * output_sample_period_us)
        tau_spacing_us = max(tau_spacing_us, pulse_len_us)

        comment = (
            "Passive receive-only listening mode for external HF signals; "
            f"freq={freq} kHz, rx_bw={rx_bandwidth_khz} kHz, intt={intt_ms} ms, "
            f"raw_window_ms={raw_window_ms}, beam={beam}, include_intf={include_intf}"
        )

        super().__init__(
            tx_bandwidth=5.0e6,
            rx_bandwidth=rx_bandwidth_hz,
            comment_string=comment,
        )

        self.add_slice(
            {
                "pulse_sequence": [0, 1],
                "tau_spacing": tau_spacing_us,
                "pulse_len": pulse_len_us,
                "num_ranges": 1,
                "first_range": 0,
                "intt": intt_ms,
                "beam_angle": [scf.STD_BEAM_ANGLES[beam]],
                "rx_beam_order": [0],
                "freq": freq,
                "rxctrfreq": rxctrfreq,
                "tx_antennas": [],
                "rx_main_antennas": list(scf.config.rx_main_antennas),
                "rx_intf_antennas": list(scf.config.rx_intf_antennas) if include_intf else [],
                "acf": False,
                "xcf": False,
                "acfint": False,
                "rxonly": True,
                "wait_for_first_scanbound": False,
                "decimation_scheme": decimation,
            }
        )
