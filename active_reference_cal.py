#!/usr/bin/python
"""
active_reference_cal
~~~~~~~~~~~~~~~~~~~~
Short single-transmit-antenna calibration experiment for array self-calibration.
"""

import borealis_experiments.superdarn_common_fields as scf
from utils.experiment_prototype import ExperimentPrototype


class ActiveReferenceCal(ExperimentPrototype):
    cpid = 3991

    def __init__(self, **kwargs):
        super().__init__(comment_string="Single-TX active reference calibration")

        freq = int(kwargs.get("freq", 12000))
        tx_ant = int(kwargs.get("tx_ant", 9))
        intt_ms = int(kwargs.get("intt", 2000))
        num_ranges = int(kwargs.get("num_ranges", 25))

        self.add_slice(
            {
                "pulse_sequence": [0],
                "tau_spacing": 300,
                "pulse_len": scf.PULSE_LEN_45KM,
                "num_ranges": num_ranges,
                "first_range": 0,
                "intt": intt_ms,
                "beam_angle": [0.0],
                "tx_beam_order": [0],
                "rx_beam_order": [0],
                "freq": freq,
                "tx_antennas": [tx_ant],
                "acf": False,
                "xcf": False,
                "acfint": False,
                "align_sequences": True,
                "wait_for_first_scanbound": False,
            }
        )
