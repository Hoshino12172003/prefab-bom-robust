"""Frozen source identities and deterministic content addressing."""
import hashlib
import json
from pathlib import Path

XLSB_SHA256 = "1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e"
ZIP_SHA256 = "dec8343a2c63f434452efc3e9ec31fac2f81f508b77baeb9a80b3b8035595ed5"
PHASE_A = "artifacts/v3_phase32a_20261111_212045"
PHASE_B = "artifacts/v3_phase32b_20261111_214914"
SOURCE_HASHES = {
    "src/prefab_v25/data.py": "f1a9601c7ff2ecad262524c6003d3238c36b880cc04d51cb15f5ff31732e0cc4",
    "src/prefab_v25/source.py": "c85d305dd3fb04e7ef3c5d8b650557036b7af519368764d1332a9bb8cbc9b21b",
    "src/prefab_v3/base.py": "46dce2984d728f537ee17af89411c45fd1f0d864998ccbe57c00eb2d0402646f",
    "src/prefab_v3/plain_ccg.py": "6811ee2baa397426f14dd1896db94cd9ddd56e3b5869f942a439012df16b86de",
    "src/prefab_v3/robust.py": "1c11eaed09f6d0d8d47db1796ecc312deb95abd7c972d3ecb136f8f18d2b623b",
    "src/prefab_v3/interface.py": "20f438d675132763d638b326439a8736109d4d3a9855685869c86f88cdbf6bda",
    "artifacts/v3_phase31r_20261111_202237/design.py": "fbb3472e70ff6c2db76ebefc1dd90028e09be9a76fc0c197ca627e945c89bb35",
    "artifacts/v3_phase31r_20261111_202237/run_matrix.py": "af0740f5424c290bbace038bf5cedc5fc95a423f293ad127687673ebfaf7c31b",
    PHASE_A + "/run_benchmark.py": "180bc448d2b8880436a500829e50c061951497851d6daac69c4606beeb7e2096",
    PHASE_B + "/profile_runs.py": "a9a121417e3918d0d8ea698d80f8464bf38b58e9501bbe10f219c82999833014",
    PHASE_B + "/structure.py": "d81b3ea9ec25a0b7378eec52bfd187e95278068e42329701898175bcdc7e6d2c",
    PHASE_B + "/risk_pattern_signature.csv": "5d4355fdabbaf0feb5715bfd9245041473316153bfc4e230b66daf2b79527338",
    PHASE_B + "/rhs_equivalence_audit.csv": "f1728761a3973fb31e4d485a820264fa252dd0483867a571533871d369eda693",
    PHASE_A + "/sha256_manifest.csv": "71a0b673b46e4f4a4b0427cb6bcfc45966007dbf13768dde564e0377b2fa99da",
    PHASE_B + "/sha256_manifest.csv": "7a6cfbc96232630b9f25300ddae8b87c7ac09f1808c2650c18162a87c5193bd5",
}
MODEL_SPEC = {
    "version": "V3_HISTORICAL_SERVICE", "periods": list(range(61, 75)),
    "objective": "max_worst_on_time_count", "buffer_names": ["x_C", "x_T", "x_O"],
    "costs": ["1", "27/19", "297/190"], "budget": "17388/19",
    "oem_seat_inventory_upper": 0, "recovery": "ABRUPT", "capacity": "RAW_XLSB",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def identity(prefix, value):
    return prefix + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_hash(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"Source SHA-256 conflict: {path}: {actual} != {expected}")


MODEL_INSTANCE_ID = identity("v3-", {"spec": MODEL_SPEC, "xlsb": XLSB_SHA256, "sources": SOURCE_HASHES})
