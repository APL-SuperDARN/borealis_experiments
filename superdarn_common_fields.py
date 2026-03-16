import numpy as np

from utils.options import Options

config = Options()

# TODO: We should protect these values from changing, I noticed during testing that I used a
# TODO: call to reverse() on one and it affected the rest of the testing afterwards

SEQUENCE_7P = [0, 9, 12, 20, 22, 26, 27]
TAU_SPACING_7P = 2400  # us

SEQUENCE_8P = [0, 14, 22, 24, 27, 31, 42, 43]
TAU_SPACING_8P = 1500  # us

STD_8P_LAG_TABLE = [
    [0, 0],
    [42, 43],
    [22, 24],
    [24, 27],
    [27, 31],
    [22, 27],
    [24, 31],
    [14, 22],
    [22, 31],
    [14, 24],
    [31, 42],
    [31, 43],
    [14, 27],
    [0, 14],
    [27, 42],
    [27, 43],
    [14, 31],
    [24, 42],
    [24, 43],
    [22, 42],
    [22, 43],
    [0, 22],
    [0, 24],
    [43, 43],
]

PULSE_LEN_45KM = 300  # us
PULSE_LEN_15KM = 100  # us

STD_FIRST_RANGE = 180  # km
STD_NUM_RANGES = config.num_ranges

STD_BEAM_ANGLES = [
    config.beam_sep * (beam_dir - (config.num_beams - 1) / 2) for beam_dir in range(config.num_beams)
]
if config.scan_direction == "clockwise":
    STD_BEAM_ORDER = [i for i in range(config.num_beams)]
elif config.scan_direction == "counterclockwise":
    STD_BEAM_ORDER = reversed([i for i in range(config.num_beams)])
else:
    raise ValueError("Unknown scan direction from config file: expected `clockwise` or `counterclockwise`")

# Calculate integration time per beam, rounded to nearest tenth of a second
INTT_MS = int(600 // config.num_beams) * 100
__integration_time_s__ = INTT_MS / 1000.0

# set common mode operating frequencies with a slight offset.
__default_freqs__ = {
    "sas": {
        "common": [10800, 13000],
        "sounding": [9690, 10500, 11000, 11700, 12400, 12900, 13150]
    },
    "pgr": {
        "common": [10900, 13100],
        "sounding": [9600, 10590, 11050, 11750, 13090, 12850, 12400]
    },
    "cly": {
        "common": [10700, 12500],
        "sounding": [11900, 12400, 11100, 10400, 9600, 12800, 13050]
    },
    "rkn": {
        "common": [10600, 12300],
        "sounding": [11100, 9600, 10500, 12350, 11800, 13090, 12850]
    },
    "inv": {
        "common": [10500, 12200],
        "sounding": [11150, 9690, 12400, 10590, 11850, 12800, 13100]
    },
    "lab": {
        "common": [10400, 13200],
        "sounding": [10600, 11250, 11950, 13150]
    },
    "wal": {
        "common": [12000, 13700],
        "sounding": [10200, 11120, 12080, 13080, 14890, 16000]
    },
    "default": {
        "common": [10400, 13200],
        "sounding": [10600, 11250, 11950, 13150]
    },
}

__site_freqs__ = __default_freqs__.get(config.site_id, __default_freqs__["default"])
COMMON_MODE_FREQ_1 = __site_freqs__["common"][0]
COMMON_MODE_FREQ_2 = __site_freqs__["common"][1]
SOUNDING_FREQS = __site_freqs__["sounding"]


def easy_scanbound(intt, beams):
    """
    Create integration time boundaries for the scan at the exact
    integration time (intt) boundaries. For new experiments, you
    may wish to ensure that your intt * len(beams) approaches a
    minute mark to reduce delay in waiting for the next scanbound.
    """
    return [i * (intt * 1e-3) for i in range(len(beams))]


STD_SCANBOUND = easy_scanbound(
    INTT_MS,
    STD_BEAM_ANGLES
)

def easy_widebeam(frequency_khz, tx_antennas, antenna_locations):
    """
    Returns complex antenna weights for the main array that generate a wide transmit pattern
    that illuminates the full FOV.

    Supported operating points:
    - 16 or 8 antennas with the legacy cached phase laws.
    - The current WAL sparse 11-element TX set at 12000/13700 kHz.
    """
    num_antennas = config.main_antenna_count
    phases = np.zeros(num_antennas, dtype=np.complex64)
    tx_idx = np.asarray(tx_antennas, dtype=int)

    # Wallops currently runs FullFOV with TX channels 0, 1, 11, 14, and 15 down, leaving the
    # sparse active set [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13].
    #
    # These per-frequency phases are manual copies of the chosen offline optimization result for
    # that sparse array: NEC element-factor export -> genetic-array/batch_genetic_solver.py ->
    # select a preferred solution from the plots/HDF5 output -> paste the relative phases here.
    #
    # Keys are physical antenna indices and values are relative phases in degrees. Antenna 2 is
    # held at 0 degrees as the phase reference used when the solution was copied into Borealis.
    wal_sparse_cached = {
        12000: {
            2: 0.0,
            3: 161.87851,
            4: 153.453079,
            5: 305.665375,
            6: 329.709198,
            7: 144.071167,
            8: 58.509125,
            9: 34.303589,
            10: 42.588226,
            12: 343.550934,
            13: 167.465164,
        },               
        13700: {
            2: 0.0,
            3: 117.205616,
            4: 338.268733,
            5: 32.710628,
            6: 27.898531,
            7: 46.891061,
            8: 116.232303,
            9: 292.800707,
            10: 234.136463,
            12: 132.31838,
            13: 11.733696,
        },
    }

    freq_key = int(round(float(frequency_khz)))
    if config.site_id == "wal" and freq_key in wal_sparse_cached:
        wal_tx = np.array(sorted(wal_sparse_cached[freq_key].keys()), dtype=int)
        if np.array_equal(np.sort(tx_idx), wal_tx):
            for ant, phase_deg in wal_sparse_cached[freq_key].items():
                phases[ant] = np.exp(1j * np.deg2rad(phase_deg))
            return phases.reshape(1, num_antennas) * 0.999999

    antenna_spacing_m = (
        antenna_locations[1, 0] - antenna_locations[0, 0]
    )  # difference in x-position of first two antennas
    if not (np.isclose(antenna_spacing_m, 15.24) or np.isclose(antenna_spacing_m, 12.8016)):
        raise ValueError(
            f"Antenna spacing must be 15.24m (or 12.8016m at WAL). Given value: {antenna_spacing_m}"
        )

    cached_values_16_antennas = {
        10400: [
            0.0,
            102.96177116,
            138.18081147,
            222.01613585,
            296.53455455,
            370.4859424,
            391.33134311,
            354.02453951,
            354.02453951,
            391.33134311,
            370.4859424,
            296.53455455,
            222.01613585,
            138.18081147,
            102.96177116,
            0.0,
        ],
        10500: [
            0.0,
            80.44283403,
            109.48744289,
            214.83502266,
            280.52619912,
            335.14851476,
            375.59632077,
            295.4515181,
            295.4515181,
            375.59632077,
            335.14851476,
            280.52619912,
            214.83502266,
            109.48744289,
            80.44283403,
            0.0,
        ],
        10600: [
            0.0,
            77.82410539,
            105.42021451,
            206.22185399,
            281.17191033,
            333.47601486,
            375.83276115,
            293.76835248,
            293.76835248,
            375.83276115,
            333.47601486,
            281.17191033,
            206.22185399,
            105.42021451,
            77.82410539,
            0.0,
        ],
        10700: [
            0.0,
            119.25520118,
            154.67891796,
            246.09065234,
            311.72748683,
            382.80492241,
            414.82741105,
            371.91794781,
            371.91794781,
            414.82741105,
            382.80492241,
            311.72748683,
            246.09065234,
            154.67891796,
            119.25520118,
            0.0,
        ],
        10800: [
            0.0,
            92.60936645,
            127.62619639,
            208.5566689,
            291.31175873,
            354.27697977,
            398.79110485,
            324.66603882,
            324.66603882,
            398.79110485,
            354.27697977,
            291.31175873,
            208.5566689,
            127.62619639,
            92.60936645,
            0.0,
        ],
        10900: [
            0.0,
            93.30613356,
            125.16534842,
            206.51840349,
            290.22196672,
            355.81710571,
            397.82221852,
            323.55700502,
            323.55700502,
            397.82221852,
            355.81710571,
            290.22196672,
            206.51840349,
            125.16534842,
            93.30613356,
            0.0,
        ],
        12200: [
            0.0,
            96.07497475,
            208.42258709,
            287.2379694,
            369.73993686,
            440.5011788,
            510.15977841,
            476.53702585,
            476.53702585,
            510.15977841,
            440.5011788,
            369.73993686,
            287.2379694,
            208.42258709,
            96.07497475,
            0.0,
        ],
        12300: [
            0.0,
            80.50182428,
            196.46546035,
            263.58060242,
            354.91524796,
            433.83518586,
            502.04261954,
            459.18645715,
            459.18645715,
            502.04261954,
            433.83518586,
            354.91524796,
            263.58060242,
            196.46546035,
            80.50182428,
            0.0,
        ],
        12500: [
            0.0,
            82.12076029,
            196.06309521,
            274.07100579,
            362.25525702,
            440.53954548,
            516.49029078,
            476.97987124,
            476.97987124,
            516.49029078,
            440.53954548,
            362.25525702,
            274.07100579,
            196.06309521,
            82.12076029,
            0.0,
        ],
        13000: [
            0.0,
            50.43556708,
            120.17720381,
            151.36779025,
            89.67641224,
            225.27830457,
            254.59953879,
            81.60952527,
            81.60952527,
            254.59953879,
            225.27830457,
            89.67641224,
            151.36779025,
            120.17720381,
            50.43556708,
            0.0,
        ],
        13100: [
            0.0,
            93.66538642,
            205.24967949,
            284.06583487,
            377.05856963,
            443.42958097,
            534.86860819,
            490.77237812,
            490.77237812,
            534.86860819,
            443.42958097,
            377.05856963,
            284.06583487,
            205.24967949,
            93.66538642,
            0.0,
        ],
        13200: [
            0.0,
            76.47696612,
            154.0441776,
            88.27019201,
            139.28169901,
            230.76759739,
            278.5674701,
            114.63090199,
            114.63090199,
            278.5674701,
            230.76759739,
            139.28169901,
            88.27019201,
            154.0441776,
            76.47696612,
            0.0,
        ],
    }
    cached_values_8_antennas = {
        10400: [
            0.0,
            25.65596691,
            78.37293679,
            139.64736262,
            139.64736262,
            78.37293679,
            25.65596691,
            0.0,
        ],
        10500: [
            0.0,
            25.08958919,
            77.59100768,
            140.85808655,
            140.85808655,
            77.59100768,
            25.08958919,
            0.0,
        ],
        10600: [
            0.0,
            24.57335302,
            76.75481191,
            141.98499171,
            141.98499171,
            76.75481191,
            24.57335302,
            0.0,
        ],
        10700: [
            0.0,
            23.8098711,
            75.90392693,
            143.01444351,
            143.01444351,
            75.90392693,
            23.8098711,
            0.0,
        ],
        10800: [
            0.0,
            22.11931133,
            73.23562257,
            143.47732068,
            143.47732068,
            73.23562257,
            22.11931133,
            0.0,
        ],
        10900: [
            0.0,
            22.85211015,
            72.76130323,
            144.37536937,
            144.37536937,
            72.76130323,
            22.85211015,
            0.0,
        ],
        12200: [
            0.0,
            24.12132192,
            67.43277427,
            160.59421469,
            160.59421469,
            67.43277427,
            24.12132192,
            0.0,
        ],
        12300: [
            0.0,
            25.79888664,
            68.32548572,
            162.24856417,
            162.24856417,
            68.32548572,
            25.79888664,
            0.0,
        ],
        12500: [
            0.0,
            29.73310292,
            70.83940609,
            166.04550735,
            166.04550735,
            70.83940609,
            29.73310292,
            0.0,
        ],
        13000: [
            0.0,
            41.4313578,
            82.16477044,
            175.25809179,
            175.25809179,
            82.16477044,
            41.4313578,
            0.0,
        ],
        13100: [
            0.0,
            43.20693263,
            84.14234248,
            175.38631445,
            175.38631445,
            84.14234248,
            43.20693263,
            0.0,
        ],
        13200: [
            0.0,
            43.42908842,
            84.21675093,
            174.68458927,
            174.68458927,
            84.21675093,
            43.42908842,
            0.0,
        ],
    }
    if tx_idx.size < 2:
        raise ValueError(
            f"Invalid parameters for easy_widebeam(): tx_antennas: {tx_antennas}, "
            f"frequency_khz: {frequency_khz}, main_antenna_count: {num_antennas}. "
            f"Need at least 2 TX antennas for a deterministic widebeam pattern."
        )

    # The legacy cached phase laws only exist at discrete optimization frequencies. If a nearby
    # frequency is requested, reuse the closest solved entry instead of failing outright.
    nearest_16 = min(cached_values_16_antennas.keys(), key=lambda k: abs(float(frequency_khz) - float(k)))
    nearest_8 = min(cached_values_8_antennas.keys(), key=lambda k: abs(float(frequency_khz) - float(k)))

    if tx_idx.size == 8:
        phases[tx_idx] = np.exp(1j * np.deg2rad(cached_values_8_antennas[nearest_8]))
        return phases.reshape(1, num_antennas) * 0.999999

    cached16 = np.exp(1j * np.deg2rad(cached_values_16_antennas[nearest_16]))
    if tx_idx.size == 16:
        phases[tx_idx] = cached16
    else:
        # If we do not have a dedicated sparse solution for this exact active set, fall back to
        # the nearest 16-element phase law and sample it at the enabled antenna indices.
        phases[tx_idx] = cached16[tx_idx]

    return phases.reshape(1, num_antennas) * 0.999999
