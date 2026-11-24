"""Isolate hash-pinned historical replay without editing the checkout's legacy sources."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory


@contextmanager
def portable_replay_root(root):
    """The original historical design differed only in its external ZIP locator."""
    root=Path(root).resolve()
    data=root/"experiments/scenario_agent_v1/data/v3"
    manifest=json.loads((data/"feature_manifest_v3.json").read_text(encoding="utf-8"))
    paths=set(manifest["pinned_sources"])|set(manifest["historical_sources"])|set(manifest["extractor_code_sha256"])
    paths.update(p.relative_to(root).as_posix() for p in data.iterdir() if p.is_file())
    dataset_manifest=json.loads((data/"training_dataset_manifest.json").read_text(encoding="utf-8"))
    paths.update(dataset_manifest["outputs"])
    if (root/"src/scenario_agent/policy_cv_protocol_v1.py").exists():
        paths.add("src/scenario_agent/policy_cv_protocol_v1.py")
    paths.add("src/scenario_agent/training_dataset_v1.py")
    with TemporaryDirectory(prefix="scenario-v3-replay-") as directory:
        target=Path(directory)
        for rel in paths:
            destination=target/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            source=root/rel
            if rel=="artifacts/v3_phase31r_20261111_202237/design.py":
                source=root/"experiments/scenario_agent_v1/provenance/design_v3_original.py"
            shutil.copyfile(source,destination)
        for rel,expected in manifest["pinned_sources"].items():
            if hashlib.sha256((target/rel).read_bytes()).hexdigest()!=expected:
                raise ValueError(f"Pinned replay source mismatch: {rel}")
        yield target
