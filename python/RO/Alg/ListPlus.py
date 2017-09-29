
"""A ListPlus adds a few methods to a standard list
to make it more consistent with dict.

History:
2003-03-13 ROwen    First release
2005-06-03 ROwen    Fixed indentation quirks (needless spaces before tabs)
"""
__all__ = ["ListPlus"]

class ListPlus (list):
    def get(self, key, defValue = None):
        try:
            return self[key]
        except (LookupError, TypeError):
            return defValue

    def has_key(self, key):
        try:
            self[key]
            return True
        except (LookupError, TypeError):
            return False

    def iteritems(self):
        for key in self.keys():
            yield (key, self[key])

    def iterkeys(self):
        return iter(range(len(self)))

    def itervalues(self):
        return iter(self)

    def keys(self):
        return list(range(len(self)))

    def values(self):
        return self[:]
