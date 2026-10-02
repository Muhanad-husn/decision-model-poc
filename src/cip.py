"""CIP questions for the C tasks (PRD §5.2, §6.1). Skeleton: not built yet."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPTIONS = ROOT / "data" / "cip" / "options.yaml"
MANIFEST = ROOT / "manifests" / "cip_options.json"


class OptionsChanged(RuntimeError):
    pass


def questions(task, options=None, manifest=None):
    raise NotImplementedError


def state(item, task):
    raise NotImplementedError


def load_items(task, path=None, limit=None):
    raise NotImplementedError
