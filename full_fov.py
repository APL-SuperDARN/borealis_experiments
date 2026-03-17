#!/usr/bin/python

"""
full_fov
~~~~~~~~
The mode transmits with a pre-calculated phase progression across the array which illuminates
the full FOV, and receives on all antennas. The first pulse in each sequence starts on the 0.1
second boundaries, to enable bistatic listening on other radars.

:copyright: 2022 SuperDARN Canada
:author: Remington Rohel
"""

import numpy as np

from utils.signals import get_phase_shift
import borealis_experiments.superdarn_common_fields as scf
from utils.experiment_prototype import ExperimentPrototype


def rx_phase_pattern(beam_angle, freq_khz, antenna_locations):
    # Helper for experiments that want to apply frequency-specific RX beam corrections at runtime.
    # The tuned directions below come from offline widebeam simulations, not from a calculation
    # performed inside Borealis during the experiment.
    # Chebyshev 30-dB window
    window = [
        0.2910,
        0.3173,
        0.4557,
        0.6018,
        0.7424,
        0.8637,
        0.9528,
        1.0000,
        1.0000,
        0.9528,
        0.8637,
        0.7424,
        0.6018,
        0.4557,
        0.3173,
        0.2910,
    ]

    adjusted_rx_beam_directions = {
        10400: [
            -25.0,
            -21.2,
            -18.3,
            -15.5,
            -11.4,
            -7.7,
            -5.0,
            -2.1,
            2.1,
            5.0,
            7.7,
            11.4,
            15.5,
            18.3,
            21.2,
            25.0,
        ],
        10500: [
            -24.8,
            -20.7,
            -17.9,
            -14.8,
            -11.8,
            -8.6,
            -4.9,
            -1.9,
            1.9,
            4.9,
            8.6,
            11.8,
            14.8,
            17.9,
            20.7,
            24.8,
        ],
        10600: [
            -25.0,
            -20.7,
            -17.8,
            -14.9,
            -11.9,
            -8.5,
            -4.8,
            -1.9,
            1.9,
            4.8,
            8.5,
            11.9,
            14.9,
            17.8,
            20.7,
            25.0,
        ],
        10700: [
            -24.5,
            -21.4,
            -18.1,
            -15.3,
            -11.5,
            -7.7,
            -5.1,
            -2.1,
            2.1,
            5.1,
            7.7,
            11.5,
            15.3,
            18.1,
            21.4,
            24.5,
        ],
        10800: [
            -25.0,
            -20.9,
            -17.8,
            -15.3,
            -11.6,
            -7.8,
            -4.8,
            -2.1,
            2.1,
            4.8,
            7.8,
            11.6,
            15.3,
            17.8,
            20.9,
            25.0,
        ],
        10900: [
            -24.9,
            -20.9,
            -17.7,
            -15.3,
            -11.7,
            -7.8,
            -4.7,
            -2.0,
            2.0,
            4.7,
            7.8,
            11.7,
            15.3,
            17.7,
            20.9,
            25.0,
        ],
        12200: [
            -24.4,
            -21.5,
            -17.7,
            -14.2,
            -11.5,
            -8.2,
            -4.8,
            -1.8,
            1.8,
            4.8,
            8.2,
            11.5,
            14.2,
            17.7,
            21.5,
            24.4,
        ],
        12300: [
            -24.2,
            -21.5,
            -17.5,
            -14.4,
            -11.5,
            -7.9,
            -5.0,
            -2.1,
            2.1,
            5.0,
            7.9,
            11.5,
            14.4,
            17.5,
            21.5,
            24.2,
        ],
        12500: [
            -24.3,
            -21.4,
            -17.8,
            -14.1,
            -11.4,
            -8.2,
            -4.9,
            -1.8,
            1.8,
            4.9,
            8.2,
            11.4,
            14.1,
            17.8,
            21.4,
            24.3,
        ],
        13000: [
            -23.9,
            -21.5,
            -18.4,
            -14.8,
            -11.4,
            -7.8,
            -4.6,
            -2.4,
            2.4,
            4.6,
            7.8,
            11.4,
            14.8,
            18.4,
            21.5,
            23.9,
        ],
        13100: [
            -24.5,
            -21.0,
            -18.4,
            -13.7,
            -11.1,
            -8.5,
            -4.7,
            -1.5,
            1.5,
            4.7,
            8.5,
            11.1,
            13.7,
            18.4,
            21.0,
            24.5,
        ],
        13200: [
            -24.8,
            -21.6,
            -18.4,
            -14.0,
            -11.7,
            -8.4,
            -4.6,
            -2.2,
            2.2,
            4.6,
            8.4,
            11.7,
            14.0,
            18.4,
            21.6,
            24.8,
        ],
    }

    # Wallops 12 MHz sparse-array corrections generated from beam_corrections.py using the
    # current 11-element TX widebeam phases and the actual active RX antenna sets from wal_config.
    wallops_adjusted_rx_main_beam_directions = {
        12000: [
            -40.7,
            -34.2,
            -30.7,
            -28.5,
            -25.2,
            -20.8,
            -18.2,
            -15.7,
            -11.5,
            -7.5,
            -4.8,
            -1.7,
            1.7,
            4.6,
            7.6,
            11.4,
            15.2,
            18.0,
            21.1,
            25.6,
            28.8,
            30.9,
            34.0,
            40.3,
        ],
    }
    wallops_adjusted_rx_intf_beam_directions = {
        12000: [
            -36.6,
            -35.0,
            -31.1,
            -28.8,
            -25.3,
            -21.1,
            -18.5,
            -16.0,
            -11.7,
            -7.5,
            -4.6,
            -1.7,
            1.5,
            4.5,
            7.5,
            11.4,
            15.3,
            18.3,
            21.6,
            26.0,
            29.2,
            31.3,
            34.9,
            37.2,
        ],
    }

    # antenna_locations contains the full geometry table for the main or interferometer array.
    # Restrict the steering calculation to the channels that are actually enabled in the config.
    is_main_array = antenna_locations.shape[0] == scf.config.main_antenna_count
    is_intf_array = antenna_locations.shape[0] == scf.config.intf_antenna_count
    if is_main_array:
        active_antennas = np.asarray(scf.config.rx_main_antennas, dtype=int)
    elif is_intf_array:
        active_antennas = np.asarray(scf.config.rx_intf_antennas, dtype=int)
    else:
        active_antennas = np.arange(antenna_locations.shape[0], dtype=int)

    active_locations = antenna_locations[active_antennas, 0]

    if is_main_array:
        tuned_beam_angles = wallops_adjusted_rx_main_beam_directions.get(
            int(freq_khz),
            adjusted_rx_beam_directions.get(int(freq_khz)),
        )
    elif is_intf_array:
        tuned_beam_angles = wallops_adjusted_rx_intf_beam_directions.get(
            int(freq_khz),
            adjusted_rx_beam_directions.get(int(freq_khz)),
        )
    else:
        tuned_beam_angles = adjusted_rx_beam_directions.get(int(freq_khz))

    if tuned_beam_angles is None or len(tuned_beam_angles) != len(beam_angle):
        tuned_beam_angles = beam_angle

    active_shift = get_phase_shift(tuned_beam_angles, [freq_khz], active_locations)[0] * 0.9999999

    # The legacy full-array Canadian mode uses a 16-point Chebyshev taper. For the sparse 11-main-
    # antenna Wallops configuration, the 12 MHz correction sweep worked better with uniform RX
    # weighting, so do not force the subset through the 16-point taper.
    if is_main_array and active_locations.shape[0] == len(window):
        active_shift = np.einsum(
            "ij,j->ij",
            active_shift,
            np.array(window, dtype=np.float32),
        )

    # Borealis indexes the returned phase matrix by physical antenna number for each array, so
    # return a dense array with zeros on inactive channels rather than a sparse active-channel view.
    dense_shift = np.zeros(
        (len(beam_angle), antenna_locations.shape[0]),
        dtype=active_shift.dtype,
    )
    dense_shift[:, active_antennas] = active_shift
    return dense_shift


class FullFOV(ExperimentPrototype):
    cpid = 3800

    def __init__(self, **kwargs):
        """
        kwargs:

        freq: int

        """
        super().__init__()

        # default frequency set here
        freq = kwargs.get("freq", scf.COMMON_MODE_FREQ_1)

        self.add_slice(
            {  # slice_id = 0, there is only one slice.
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
                "xcf": True,  # cross-correlation processing
                "acfint": True,  # interferometer acfs
            }
        )
