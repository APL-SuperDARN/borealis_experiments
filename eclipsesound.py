#!/usr/bin/python3

"""
eclipsesound
~~~~~~~~~~~~
Modified version of normalsound with fewer multi-frequency beams.

:copyright: 2026 SuperDARN
:author: Evan Thomas
"""

import itertools

from utils.experiment_prototype import ExperimentPrototype
import borealis_experiments.superdarn_common_fields as scf


class EclipseSound(ExperimentPrototype):
    """Two-second common scan plus two-beam, multi-frequency sounding."""

    cpid = 1103

    def __init__(self):
        sounding_beams = [0, 7]
        # The Wallops site list fits one 5 MHz sampling band after transition
        # margins and is distributed approximately evenly in sqrt(f).
        sounding_freqs = scf.SOUNDING_FREQS
        centerfreq = 12150
        beam_nums = []
        freq_nums = []
        for beam, freq_index in itertools.product(sounding_beams, range(len(sounding_freqs))):
            beam_nums.append(beam)
            freq_nums.append(freq_index)

        common_intt_ms = 2000
        common_slice = {
            "pulse_sequence": scf.SEQUENCE_8P,
            "tau_spacing": scf.TAU_SPACING_8P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": scf.STD_NUM_RANGES,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": common_intt_ms,
            "beam_angle": scf.STD_BEAM_ANGLES,
            "tx_beam_order": scf.STD_BEAM_ORDER,
            "rx_beam_order": scf.STD_BEAM_ORDER,
            "scanbound": scf.easy_scanbound(common_intt_ms, scf.STD_BEAM_ORDER),
            "freq": scf.COMMON_MODE_FREQ_1,
            "txctrfreq": centerfreq,
            "rxctrfreq": centerfreq,
            "acf": True,
            "xcf": True,
            "acfint": False,
            "lag_table": scf.STD_8P_LAG_TABLE,
        }

        sounding_scanbound_spacing = 1.8  # seconds
        sounding_slice = {
            "pulse_sequence": scf.SEQUENCE_8P,
            "tau_spacing": scf.TAU_SPACING_8P,
            "pulse_len": scf.PULSE_LEN_45KM,
            "num_ranges": scf.STD_NUM_RANGES,
            "first_range": scf.STD_FIRST_RANGE,
            "intt": sounding_scanbound_spacing * 1.0e3 - 100,
            "beam_angle": scf.STD_BEAM_ANGLES,
            "tx_beam_order": beam_nums,
            "rx_beam_order": beam_nums,
            "scanbound": [
                32 + index * sounding_scanbound_spacing for index in range(len(beam_nums))
            ],
            "freq": sounding_freqs,
            "freq_order": freq_nums,
            "txctrfreq": centerfreq,
            "rxctrfreq": centerfreq,
            "acf": True,
            "xcf": True,
            "acfint": False,
            "lag_table": scf.STD_8P_LAG_TABLE,
        }

        super().__init__(comment_string="August 2026 total solar eclipse experiment")
        self.add_slice(common_slice)
        self.add_slice(sounding_slice, {0: "SCAN"})
