#!/usr/bin/python

"""
full_fov_interleaved
~~~~~~~~~~~~~~
The mode transmits with a pre-calculated phase progression across the array which illuminates
a 60-degree FOV, and receives on all antennas. This mode is AVEPERIOD interleaved with narrow-beam scanning
at the same frequency.

:copyright: 2024 SuperDARN Canada
:author: Remington Rohel
"""

import copy

import borealis_experiments.superdarn_common_fields as scf
from borealis_experiments.full_fov import rx_phase_pattern
from utils.experiment_prototype import ExperimentPrototype


class FullFOVInterleaved(ExperimentPrototype):
    cpid = 3808

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int

        """
        super().__init__()

        # On WAL, COMMON_MODE_FREQ_1 resolves to 12000 kHz, so this comparison mode defaults to
        # interleaving the current 12 MHz FullFOV setup with a narrowbeam normalscan-style slice.
        freq = kwargs.get("freq", scf.COMMON_MODE_FREQ_1)

        slice_0 = {
            "pulse_sequence": scf.SEQUENCE_7P,
            "tau_spacing": scf.TAU_SPACING_7P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": scf.STD_NUM_RANGES,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": scf.INTT_MS,  # duration of an integration, in ms
            "beam_angle": scf.STD_BEAM_ANGLES,
            "rx_beam_order": [[i for i in range(len(scf.STD_BEAM_ANGLES))]],
            "tx_beam_order": [0],  # only one pattern
            "tx_antenna_pattern": scf.easy_widebeam,
            "rx_antenna_pattern": rx_phase_pattern,
            "freq": freq,  # kHz
            "acf": True,
            "xcf": True,
            "acfint": True,
        }

        slice_1 = copy.deepcopy(slice_0)
        slice_1.pop("tx_antenna_pattern")
        slice_1.pop("rx_antenna_pattern")
        slice_1["rx_beam_order"] = scf.STD_BEAM_ORDER
        slice_1["tx_beam_order"] = scf.STD_BEAM_ORDER

        self.add_slice(slice_0)
        self.add_slice(slice_1, interfacing_dict={0: "AVEPERIOD"})
