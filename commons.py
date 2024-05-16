import json
import typing
from pathlib import Path

import PySide6.QtCore as qc


def dict_add_value(d: dict, key: str, value: typing.Any):
    """Pythonic way to add a value to an arbitrarly nested dictionary (and without using defaultdict)

    Args:
        d (dict): the dictionnary to add value to
        key (str): a string representing the key to add
        value (Any): the value to add
    """
    if "." in key:
        key, sub_key = key.split(".", 1)
        if key not in d:
            d[key] = {}
        dict_add_value(d[key], sub_key, value)
    else:
        d[key] = value


def save_user_prefs(prefs: dict):

    user_prefs = Path(
        qc.QStandardPaths().writableLocation(
            qc.QStandardPaths.StandardLocation.AppDataLocation
        )
    )
    user_prefs.mkdir(parents=True, exist_ok=True)
    old_prefs = {}
    if (user_prefs / "config.json").exists():
        with open(user_prefs / "config.json", "r") as f:
            old_prefs = json.load(f)

    old_prefs.update(prefs)

    with open(user_prefs / "config.json", "w") as f:
        json.dump(old_prefs, f)


def load_user_prefs():
    user_prefs = Path(
        qc.QStandardPaths().writableLocation(
            qc.QStandardPaths.StandardLocation.AppDataLocation
        )
    )
    prefs = {}
    if (user_prefs / "config.json").exists():
        with open(user_prefs / "config.json", "r") as f:
            prefs = json.load(f)
    return prefs
