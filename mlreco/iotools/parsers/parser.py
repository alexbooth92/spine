"""Contains Parser class which all parsers inherit from."""

class Parser:
    """Parent class of all parser classes.

    Provides basic functionality shared by all parsers:
    1. Defines a :meth:`__call__` function shared by all classes

    Attributes
    ----------
    """
    name = None
    aliases = []
    unwrap_rule = None

    def __init__(self, **kwargs):
        """Loops over data product names, stores them.

        Parameters
        ----------
        **kwargs : dict, optional
            Keyword arguments passed to the parser function

        Notes
        -----
        All parser argument which correspond to the name of a tree in the
        LArCV file must be contain either the `_event` or `_event_list` suffix.
        """
        # Find data keys, append them to the map
        self.data_map = {}
        self.tree_keys = []
        for key, value in kwargs.items():
            assert '_event' in key, (
                    "Data arguments must contain `_event` or `_event_list` "
                    "and must point to an existing tree in the LArCV file.")
            if value is not None:
                self.data_map[key] = value
                if isinstance(value, str):
                    if value not in self.tree_keys:
                        self.tree_keys.append(value)
                else:
                    for v in value:
                        if v not in self.tree_keys:
                            self.tree_keys.append(v)

    def __call__(self, trees):
        """Fetches the required data products from the LArCV data trees, pass
        them to the parser function.

        Parameters
        ----------
        trees : dict
            Dictionary which maps each data product name to a LArCV object

        Results
        -------
        object
            Output(s) of the parser function
        """
        # Build the input to the parser function
        data_dict = {}
        for key, value in self.data_map.items():
            if isinstance(value, str):
                if value not in trees:
                    raise ValueError(
                            f"Must provide {value} for parser {self.name}")
                data_dict[key] = trees[value]
            elif isinstance(value, list):
                for v in value:
                    if v not in trees:
                        raise ValueError(
                                f"Must provide {v} for parser {self.name}")
                data_dict[key] = [trees[v] for v in value]

        return self.process(**data_dict)

    def process(self):
        """Parse one entry.

        This is a place-holder, must be defined in inheriting class
        """
        raise NotImplementedError("Must define `process` method")