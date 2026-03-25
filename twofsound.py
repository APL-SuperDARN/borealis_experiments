#!/usr/bin/python

"""
twofsound
~~~~~~~~~
Standard operating Borealis experiment. Alternates transmitting in two different
frequency bands, with clear-frequency search enabled for each band.

:copyright: 2023 SuperDARN Canada
"""

from __future__ import annotations

import copy

from utils.experiment_prototype import ExperimentPrototype
import borealis_experiments.superdarn_common_fields as scf


class Twofsound(ExperimentPrototype):
    cpid = 3503

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
    def _cfs_range(center_khz: int, width_khz: int) -> list[int]:
        half_width = max(1, int(width_khz) // 2)
        return [int(center_khz) - half_width, int(center_khz) + half_width]

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
        tx_freq_1 = int(kwargs.get("freq1", 10200))
        tx_freq_2 = int(kwargs.get("freq2", 12000))

        shared_cfs_width = int(kwargs.get("cfs_width_khz", 300))
        cfs_width_1 = int(kwargs.get("cfs_width1_khz", shared_cfs_width))
        cfs_width_2 = int(kwargs.get("cfs_width2_khz", shared_cfs_width))

        cfs_range_1 = self._sanitize_cfs_range(tx_freq_1, self._cfs_range(tx_freq_1, cfs_width_1))
        cfs_range_2 = self._sanitize_cfs_range(tx_freq_2, self._cfs_range(tx_freq_2, cfs_width_2))

        cfs_duration = int(kwargs.get("cfs_duration", 90))
        cfs_stable_time = int(kwargs.get("cfs_stable_time", 180))

        cfs_pwr_threshold_raw = kwargs.get("cfs_pwr_threshold", 3.0)
        cfs_pwr_threshold = (
            None
            if cfs_pwr_threshold_raw in {None, "", "none", "None"}
            else float(cfs_pwr_threshold_raw)
        )

        cfs_always_run = self._to_bool(kwargs.get("cfs_always_run", False), default=False)

        rxctrfreq = txctrfreq = int((tx_freq_1 + tx_freq_2) / 2)

        slice_1 = {
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
            "cfs_range": cfs_range_1,
            "cfs_duration": cfs_duration,
            "cfs_stable_time": cfs_stable_time,
            "cfs_pwr_threshold": cfs_pwr_threshold,
            "cfs_always_run": cfs_always_run,
            "txctrfreq": txctrfreq,
            "rxctrfreq": rxctrfreq,
            "acf": True,
            "xcf": True,
            "acfint": True,
        }

        slice_2 = copy.deepcopy(slice_1)
        slice_2["cfs_range"] = cfs_range_2

        super().__init__(comment_string="Twofsound scan-by-scan with clear-frequency search")

        self.add_slice(slice_1)
        self.add_slice(slice_2, interfacing_dict={0: "SCAN"})
