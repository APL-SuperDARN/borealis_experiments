"""
normalscan_cfs
~~~~~~~~~~~~~~
Normalscan with clear-frequency search (CFS) enabled.

This mode reuses the standard normalscan timing/beam schedule, but chooses
operating frequency from a requested CFS band to avoid local interference.

Example radar_control usage:
    python3 -O -u src/radar_control.py normalscan_cfs discretionary \
      --kwargs cfs_min_khz=11850 cfs_max_khz=12150 cfs_stable_time=180 cfs_pwr_threshold=3.0
"""

from __future__ import annotations

import borealis_experiments.superdarn_common_fields as scf
from utils.experiment_prototype import ExperimentPrototype


class NormalscanCfs(ExperimentPrototype):
    cpid = 3825

    @staticmethod
    def _to_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "f", "no", "n", "off"}:
            return False
        return default

    def __init__(self, **kwargs):
        super().__init__()

        default_center_khz = int(scf.COMMON_MODE_FREQ_1)
        cfs_center_khz = int(kwargs.get("cfs_center_khz", default_center_khz))
        cfs_width_khz = int(kwargs.get("cfs_width_khz", 300))
        half_width = max(1, cfs_width_khz // 2)

        cfs_min_khz = int(kwargs.get("cfs_min_khz", cfs_center_khz - half_width))
        cfs_max_khz = int(kwargs.get("cfs_max_khz", cfs_center_khz + half_width))

        if cfs_max_khz <= cfs_min_khz:
            raise ValueError(
                f"Invalid CFS bounds: cfs_min_khz={cfs_min_khz}, cfs_max_khz={cfs_max_khz}"
            )

        cfs_duration = int(kwargs.get("cfs_duration", 90))
        cfs_stable_time = int(kwargs.get("cfs_stable_time", 180))

        cfs_pwr_threshold_raw = kwargs.get("cfs_pwr_threshold", 3.0)
        cfs_pwr_threshold = (
            None if cfs_pwr_threshold_raw in {None, "", "none", "None"} else float(cfs_pwr_threshold_raw)
        )

        cfs_always_run = self._to_bool(kwargs.get("cfs_always_run", False), default=False)

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
                "cfs_range": [cfs_min_khz, cfs_max_khz],
                "cfs_duration": cfs_duration,
                "cfs_stable_time": cfs_stable_time,
                "cfs_pwr_threshold": cfs_pwr_threshold,
                "cfs_always_run": cfs_always_run,
                "acf": True,
                "xcf": True,
                "acfint": True,
                "wait_for_first_scanbound": False,
            }
        )
