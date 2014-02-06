"""A dictionary that is automatically persisted to a file

Useful for managing saved configurations and similar purposes.
"""
import collections
import json
import os.path

__all__ = ["SavedDict"]

class SavedDict(collections.MutableMapping):
    """A dictionary that is automatically read from and written to a file

    The data is saved to the file for every update, so this is intended only for
    slowly varying data, e.g. saving configurations.
    """
    def __init__(self, filePath):
        """Create a SavedDict and load data from the file, if found
        
        Inputs:
        - filePath: default file path
        """
        collections.MutableMapping.__init__(self)
        self._filePath = filePath
        self._data = dict()
        if os.path.isfile(filePath):
            with open(self._filePath, "rU") as inFile:
                dataStr = inFile.read()
            self._data = json.loads(dataStr)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, config):
        self._data[key] = config
        self._dump()

    def __delitem__(self, key):
        del self._data[key]
        self._dump()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def _dump(self):
        """Write data to file, overwriting the previous file (if any)
        """
        dataStr = json.dumps(self._data)
        with open(self._filePath, "w") as outFile:
            outFile.write(dataStr)
