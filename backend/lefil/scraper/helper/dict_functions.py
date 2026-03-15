def get_dict_value(iterable: dict, path: str, separator: str = "/", default=None, modifier=None):
    """
    Read a dict as if it was a folder. If the given path doesn't exist, return the `default` value
    :param iterable: the dictionary that will be iterated
    :param path: the path that will be navigated inside the dictionary
    :param separator: the separator used between each `folders`
    :param default: the default value returned if the path doesn't exist
    :param modifier: a callable modifier applied to the returned value
    :return: the value inside the dictionary with the modifier applied if it exists
    """
    if iterable is None:
        return default
    iterable_ptr = iterable
    for leaf in path.split(separator):
        if leaf not in iterable_ptr:
            return default
        iterable_ptr = iterable_ptr[leaf]
    if modifier is not None and iterable_ptr != default:
        return modifier(iterable_ptr)
    return iterable_ptr