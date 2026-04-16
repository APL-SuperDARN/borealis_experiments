#!/usr/bin/python
"""
mccm_noise_survey
~~~~~~~~~~~~~~~~~
Receive-only MCCM helper for comparing per-channel noise floors.
"""

from __future__ import annotations

import borealis_experiments.superdarn_common_fields as scf
from utils.experiment_prototype import ExperimentPrototype


def _parse_antennas(value, default_antennas):
    if value is None:
        return list(default_antennas)
    if isinstance(value, str):
        if value.strip() == "":
            return []
        return [int(part) for part in value.split(",") if part.strip()]
    return [int(ant) for ant in value]


class MccmNoiseSurvey(ExperimentPrototype):
    cpid = 3992

    def __init__(self, **kwargs):
        freq = int(kwargs.get("freq", scf.COMMON_MODE_FREQ_1))
        intt_ms = int(kwargs.get("intt", scf.INTT_MS))
        num_ranges = int(kwargs.get("num_ranges", scf.STD_NUM_RANGES))
        rx_main_antennas = _parse_antennas(
            kwargs.get("rx_main_antennas"), scf.config.rx_main_antennas
        )
        rx_intf_antennas = _parse_antennas(
            kwargs.get("rx_intf_antennas"), scf.config.rx_intf_antennas
        )

        super().__init__(comment_string="Receive-only MCCM noise survey")

        self.add_slice(
            {
                "pulse_sequence": [0],
                "tau_spacing": 300,
                "pulse_len": scf.PULSE_LEN_45KM,
                "num_ranges": num_ranges,
                "first_range": 0,
                "intt": intt_ms,
                "beam_angle": [0.0],
                "rx_beam_order": [0],
                "freq": freq,
                "rx_main_antennas": rx_main_antennas,
                "rx_intf_antennas": rx_intf_antennas,
                "acf": False,
                "xcf": False,
                "acfint": False,
                "rxonly": True,
                "align_sequences": True,
                "wait_for_first_scanbound": False,
            }
        )
