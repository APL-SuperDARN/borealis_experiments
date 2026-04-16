#!/usr/bin/python
"""
active_reference_cal
~~~~~~~~~~~~~~~~~~~~
Short single-transmit-antenna calibration experiment for array self-calibration.
"""

from __future__ import annotations

import numpy as np

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


def _single_tx_pattern(scale: float, tx_ant: int):
    def tx_antenna_pattern(tx_freq_khz, tx_antennas, antenna_locations):
        del tx_freq_khz, tx_antennas
        pattern = np.zeros((1, len(antenna_locations)), dtype=np.complex64)
        pattern[0, tx_ant] = np.complex64(scale)
        return pattern

    return tx_antenna_pattern


def _parse_pulse_sequence(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [int(part) for part in text.split(",") if part.strip()]
    return [int(item) for item in value]


def _resolve_pulse_timing(kwargs):
    scheme = str(kwargs.get("pulse_scheme", "single")).strip().lower()
    explicit_sequence = _parse_pulse_sequence(kwargs.get("pulse_sequence"))
    explicit_tau_spacing = kwargs.get("tau_spacing")
    pulse_len = int(kwargs.get("pulse_len", scf.PULSE_LEN_45KM))

    if explicit_sequence is not None:
        if explicit_tau_spacing is None:
            raise ValueError("pulse_sequence requires tau_spacing")
        return explicit_sequence, int(explicit_tau_spacing), pulse_len, "custom"

    presets = {
        "single": ([0], 300, pulse_len),
        "mccm7": ([0, 2, 4, 6, 8, 10, 12], 300, pulse_len),
        "mccm8": ([0, 2, 4, 6, 8, 10, 12, 14], 300, pulse_len),
        "7p": (list(scf.SEQUENCE_7P), scf.TAU_SPACING_7P, pulse_len),
        "8p": (list(scf.SEQUENCE_8P), scf.TAU_SPACING_8P, pulse_len),
    }
    if scheme not in presets:
        raise ValueError(
            f"Unsupported pulse_scheme '{scheme}'. Use single, mccm7, mccm8, 7p, 8p, or explicit pulse_sequence/tau_spacing"
        )
    pulse_sequence, tau_spacing, resolved_pulse_len = presets[scheme]
    if explicit_tau_spacing is not None:
        tau_spacing = int(explicit_tau_spacing)
    return pulse_sequence, int(tau_spacing), int(resolved_pulse_len), scheme


class ActiveReferenceCal(ExperimentPrototype):
    cpid = 3991

    def __init__(self, **kwargs):
        freq = int(kwargs.get("freq", 12000))
        tx_ant = int(kwargs.get("tx_ant", 9))
        intt_ms = int(kwargs.get("intt", 2000))
        num_ranges = int(kwargs.get("num_ranges", 25))
        tx_scale = float(kwargs.get("tx_scale", 0.001))
        if tx_scale <= 0.0 or tx_scale > 1.0:
            raise ValueError("tx_scale must satisfy 0 < tx_scale <= 1")

        if tx_ant not in scf.config.tx_main_antennas:
            raise ValueError(
                f"tx_ant {tx_ant} not in configured TX antenna list {scf.config.tx_main_antennas}"
            )

        rx_main_antennas = _parse_antennas(
            kwargs.get("rx_main_antennas"), scf.config.rx_main_antennas
        )
        rx_intf_antennas = _parse_antennas(
            kwargs.get("rx_intf_antennas"), scf.config.rx_intf_antennas
        )
        pulse_sequence, tau_spacing, pulse_len, pulse_scheme = _resolve_pulse_timing(kwargs)

        comment = (
            f"Single-TX active reference calibration tx_ant={tx_ant} tx_scale={tx_scale:.6f} "
            f"pulse_scheme={pulse_scheme} pulse_count={len(pulse_sequence)}"
        )
        super().__init__(comment_string=comment)

        self.add_slice(
            {
                "pulse_sequence": pulse_sequence,
                "tau_spacing": tau_spacing,
                "pulse_len": pulse_len,
                "num_ranges": num_ranges,
                "first_range": 0,
                "intt": intt_ms,
                "beam_angle": [0.0],
                "tx_beam_order": [0],
                "rx_beam_order": [0],
                "freq": freq,
                "tx_antennas": [tx_ant],
                "tx_antenna_pattern": _single_tx_pattern(tx_scale, tx_ant),
                "rx_main_antennas": rx_main_antennas,
                "rx_intf_antennas": rx_intf_antennas,
                "acf": False,
                "xcf": False,
                "acfint": False,
                "align_sequences": True,
                "wait_for_first_scanbound": False,
            }
        )
