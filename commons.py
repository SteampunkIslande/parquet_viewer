import typing


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
