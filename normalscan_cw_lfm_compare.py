#!/usr/bin/python

"""
normalscan_cw_lfm_compare
~~~~~~~~~~~~~~~~~~~~~~~
Scan-aware CW/LFM normalscan comparison experiment. Alternates one full
CW normalscan sweep and one full LFM normalscan sweep on a scan-by-scan
basis while preserving the standard 24-beam normalscan timing.

:copyright: 2026 SuperDARN Canada
"""

from __future__ import annotations

import copy
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
            f"output_rate_hz={output_rate_hz} must be comfortably above "
            f"lfm_bandwidth_hz={lfm_bandwidth_hz}"
        )

    cutoff_hz = min(0.45 * output_rate_hz, max(60e3, 3.0 * lfm_bandwidth_hz))
    transition_hz = min(cutoff_hz * 0.5, max(10e3, lfm_bandwidth_hz))
    ripple_db = 80
    scale = 1000.0

    taps = scale * dm.create_firwin_filter_by_attenuation(sample_rate, transition_hz, cutoff_hz, ripple_db)
    stage = dm.DecimationStage(0, sample_rate, dm_rate, taps.tolist())
    return dm.DecimationScheme(sample_rate, sample_rate / dm_rate, stages=[stage])


class NormalscanCWLFMCompare(ExperimentPrototype):
    cpid = 3826

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
        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        target_pairs = int(kwargs.get("target_pairs", 10))
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

        if lfm_sweep not in {"up", "down"}:
            raise ValueError(f"Unsupported lfm_sweep {lfm_sweep!r}")
        if target_pairs <= 0:
            raise ValueError(f"target_pairs must be positive, got {target_pairs}")

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

        sample_spacing_km = 299_792_458.0 / (2.0 * output_rx_rate_hz) / 1000.0
        comment_parts = [f"target_pairs={target_pairs}", "CW/LFM scan-by-scan normalscan comparison"]
        if enable_cfs:
            comment_parts.append(f"CFS {cfs_range[0]}-{cfs_range[1]} kHz")
        else:
            comment_parts.append(f"freq={freq} kHz")
        comment_parts.append(
            "LFM "
            f"lfm_bw_hz={lfm_bandwidth_hz:.1f} "
            f"lfm_sweep={lfm_sweep} "
            f"rx_sample_spacing_km={sample_spacing_km:.3f}"
        )

        super().__init__(comment_string="; ".join(comment_parts))

        slice_base = {
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
            slice_base.update(
                {
                    "cfs_range": cfs_range,
                    "cfs_duration": cfs_duration,
                    "cfs_stable_time": cfs_stable_time,
                    "cfs_pwr_threshold": cfs_pwr_threshold,
                    "cfs_always_run": cfs_always_run,
                }
            )
        else:
            slice_base["freq"] = freq

        cw_slice = copy.deepcopy(slice_base)
        cw_slice.update(
            {
                "comment": "CW scan slice",
                "acf": True,
                "xcf": True,
                "acfint": True,
            }
        )

        lfm_slice = copy.deepcopy(slice_base)
        lfm_slice.update(
            {
                "comment": "LFM scan slice",
                "pulse_waveform": "lfm",
                "pulse_waveform_bandwidth": lfm_bandwidth_hz,
                "pulse_waveform_sweep": lfm_sweep,
                "decimation_scheme": lfm_rx_scheme(output_rx_rate_hz, lfm_bandwidth_hz),
                "acf": False,
                "xcf": False,
                "acfint": False,
            }
        )

        self.add_slice(cw_slice)
        self.add_slice(lfm_slice, interfacing_dict={0: "SCAN"})
