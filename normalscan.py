"""
normalscan
~~~~~~~~~~
Standard radar operating experiment. Transmits a single frequency signal.

This variant also supports optional clear-frequency search and LFM-coded
transmit pulses while preserving the default CW normalscan behavior.

:copyright: 2023 SuperDARN Canada
"""

from __future__ import annotations

import math

import borealis_experiments.superdarn_common_fields as scf
from utils import decimation_scheme as dm
from utils.experiment_prototype import ExperimentPrototype


def lfm_rx_scheme(
    output_rate_hz: float = 100_000.0,
    lfm_bandwidth_hz: float = 12_500.0,
) -> dm.DecimationScheme:
    sample_rate = 5.0e6
    dm_rate = int(round(sample_rate / output_rate_hz))

    if not math.isclose(sample_rate / dm_rate, output_rate_hz, abs_tol=1.0):
        raise ValueError(f"output_rate_hz={output_rate_hz} is not an integer decimation of 5 MHz")

    if output_rate_hz <= 4.0 * lfm_bandwidth_hz:
        raise ValueError(
            f"output_rate_hz={output_rate_hz} must be comfortably above lfm_bandwidth_hz={lfm_bandwidth_hz}"
        )

    cutoff_hz = min(0.45 * output_rate_hz, max(60e3, 3.0 * lfm_bandwidth_hz))
    transition_hz = min(cutoff_hz * 0.5, max(10e3, lfm_bandwidth_hz))
    ripple_db = 80
    scale = 1000.0

    # Keep the chirp plus matched-filter sidelobes while exporting a denser receive grid than
    # standard rawacf production would use.
    taps = scale * dm.create_firwin_filter_by_attenuation(sample_rate, transition_hz, cutoff_hz, ripple_db)
    stage = dm.DecimationStage(0, sample_rate, dm_rate, taps.tolist())
    return dm.DecimationScheme(sample_rate, sample_rate / dm_rate, stages=[stage])


class Normalscan(ExperimentPrototype):
    cpid = 151

    @staticmethod
    def _to_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "f", "no", "n", "off"}:
            return False
        return default

    @staticmethod
    def _sanitize_cfs_range(center_khz: int, cfs_range: list[int], guard_khz: int = 10) -> list[int]:
        start_khz, stop_khz = [int(value) for value in cfs_range]

        for restricted_start, restricted_stop in scf.config.restricted_ranges:
            if restricted_stop < start_khz or restricted_start > stop_khz:
                continue

            left = [start_khz, min(stop_khz, int(restricted_start) - guard_khz)]
            right = [max(start_khz, int(restricted_stop) + guard_khz), stop_khz]
            candidates = []

            if left[0] < left[1]:
                candidates.append(left)
            if right[0] < right[1]:
                candidates.append(right)
            if not candidates:
                raise ValueError(
                    f"CFS range {cfs_range} is fully blocked by restricted range "
                    f"{(restricted_start, restricted_stop)}"
                )

            containing_center = [
                candidate for candidate in candidates if candidate[0] <= center_khz <= candidate[1]
            ]
            selected = max(containing_center or candidates, key=lambda item: item[1] - item[0])
            start_khz, stop_khz = selected

        return [start_khz, stop_khz]

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int
            Requested operating frequency in kHz when CFS is disabled. Also used as the default CFS
            search-band center when CFS is enabled.
        pulse_waveform: str
            Either "cw" or "lfm". Defaults to CW.
        lfm_bandwidth_hz: float
            Chirp bandwidth for LFM mode. Defaults to 12.5 kHz.
        lfm_sweep: str
            Either "up" or "down". Defaults to "up".
        output_rx_rate_hz: float
            Exported IQ sample rate for LFM mode. Defaults to 100 kHz.
        enable_cfs: bool
            Enable clear-frequency search using the band defined by the cfs_* kwargs.
        cfs_center_khz: int
            Center frequency of the CFS search window in kHz. Defaults to freq.
        cfs_width_khz: int
            Width of the CFS search window in kHz. Defaults to 300.
        cfs_min_khz, cfs_max_khz: int
            Optional explicit CFS bounds in kHz.
        cfs_duration, cfs_stable_time, cfs_pwr_threshold, cfs_always_run
            Optional clear-frequency-search control knobs passed through to the slice.
        """
        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        pulse_waveform = str(kwargs.get("pulse_waveform", "cw")).lower()
        lfm_bandwidth_hz = float(kwargs.get("lfm_bandwidth_hz", 12_500.0))
        lfm_sweep = str(kwargs.get("lfm_sweep", "up")).lower()
        output_rx_rate_hz = float(kwargs.get("output_rx_rate_hz", 100_000.0))
        cfs_kwarg_names = (
            "cfs_center_khz",
            "cfs_width_khz",
            "cfs_min_khz",
            "cfs_max_khz",
            "cfs_duration",
            "cfs_stable_time",
            "cfs_pwr_threshold",
            "cfs_always_run",
        )
        default_enable_cfs = any(name in kwargs for name in cfs_kwarg_names)
        enable_cfs = self._to_bool(kwargs.get("enable_cfs", default_enable_cfs), default=default_enable_cfs)

        if pulse_waveform not in {"cw", "lfm"}:
            raise ValueError(f"Unsupported pulse_waveform {pulse_waveform!r}")
        if lfm_sweep not in {"up", "down"}:
            raise ValueError(f"Unsupported lfm_sweep {lfm_sweep!r}")

        cfs_range = None
        cfs_duration = None
        cfs_stable_time = None
        cfs_pwr_threshold = None
        cfs_always_run = False
        if enable_cfs:
            cfs_center_khz = int(kwargs.get("cfs_center_khz", freq))
            cfs_width_khz = int(kwargs.get("cfs_width_khz", 300))
            half_width = max(1, cfs_width_khz // 2)
            cfs_min_khz = int(kwargs.get("cfs_min_khz", cfs_center_khz - half_width))
            cfs_max_khz = int(kwargs.get("cfs_max_khz", cfs_center_khz + half_width))

            if cfs_max_khz <= cfs_min_khz:
                raise ValueError(
                    f"Invalid CFS bounds: cfs_min_khz={cfs_min_khz}, cfs_max_khz={cfs_max_khz}"
                )

            cfs_range = self._sanitize_cfs_range(cfs_center_khz, [cfs_min_khz, cfs_max_khz])
            cfs_duration = int(kwargs.get("cfs_duration", 90))
            cfs_stable_time = int(kwargs.get("cfs_stable_time", 180))

            cfs_pwr_threshold_raw = kwargs.get("cfs_pwr_threshold", 3.0)
            cfs_pwr_threshold = (
                None
                if cfs_pwr_threshold_raw in {None, "", "none", "None"}
                else float(cfs_pwr_threshold_raw)
            )
            cfs_always_run = self._to_bool(kwargs.get("cfs_always_run", False), default=False)

        comment_parts = []
        if enable_cfs:
            comment_parts.append(f"CFS {cfs_range[0]}-{cfs_range[1]} kHz")
        if pulse_waveform == "lfm":
            sample_spacing_km = 299_792_458.0 / (2.0 * output_rx_rate_hz) / 1000.0
            comment_parts.append(
                "LFM "
                f"lfm_bw_hz={lfm_bandwidth_hz:.1f} "
                f"lfm_sweep={lfm_sweep} "
                f"rx_sample_spacing_km={sample_spacing_km:.3f}"
            )

        super().__init__(comment_string="; ".join(comment_parts))

        slice_config = {
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
            "wait_for_first_scanbound": False,
        }

        if enable_cfs:
            slice_config.update(
                {
                    "cfs_range": cfs_range,
                    "cfs_duration": cfs_duration,
                    "cfs_stable_time": cfs_stable_time,
                    "cfs_pwr_threshold": cfs_pwr_threshold,
                    "cfs_always_run": cfs_always_run,
                }
            )
        else:
            slice_config["freq"] = freq

        if pulse_waveform == "lfm":
            slice_config.update(
                {
                    "pulse_waveform": "lfm",
                    "pulse_waveform_bandwidth": lfm_bandwidth_hz,
                    "pulse_waveform_sweep": lfm_sweep,
                    "decimation_scheme": lfm_rx_scheme(output_rx_rate_hz, lfm_bandwidth_hz),
                    # The coded mode is intended for IQ capture plus offline pulse compression.
                    "acf": False,
                    "xcf": False,
                    "acfint": False,
                }
            )
        else:
            slice_config.update(
                {
                    "acf": True,
                    "xcf": True,
                    "acfint": True,
                }
            )

        self.add_slice(slice_config)
