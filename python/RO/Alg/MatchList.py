
"""
History:
2003-10-23 ROwen    Renamed from GetByPrefix and enhanced.
2005-06-08 ROwen    Changed MatchList to a new style class.
2008-01-04 ROwen    Bug fix: was not compatible with unicode entries (the match test would fail).
2014-10-24 ROwen    Refined the error reporting for getUniqueMatch:
                    - if there is more than one match the exception lists the matches in alphabetical order
                    - if there are no matches then the exception lists all items in alphabetical order
"""
__all__ = ["MatchList"]

class MatchList(object):
    """Find matches for a string in a list of strings,
    optionally allowing abbreviations and ignoring case.

    Inputs:
    - valueList: a list of values; non-string entries are ignored
    - abbrevOK: allow abbreviations?
    - ignoreCase: ignore case?
    """
    def __init__(self,
        valueList = (),
        abbrevOK = True,
        ignoreCase = True,
    ):
        self.abbrevOK = bool(abbrevOK)
        self.ignoreCase = bool(ignoreCase)

        self.setList(valueList)

    def getAllMatches(self, prefix):
        """Return a list of matches (an empty list if no matches)
        """
        if self.ignoreCase:
            prefix = prefix.lower()
        if self.abbrevOK:
            return [valItem[-1] for valItem in self.valueList if valItem[0].startswith(prefix)]
        else:
            return [valItem[-1] for valItem in self.valueList if valItem[0] == prefix]

    def getUniqueMatch(self, prefix):
        """If there is a unique match, return it, else raise ValueError.
        """
        matchList = self.getAllMatches(prefix)
        if len(matchList) == 1:
            return matchList[0]
        else:
            if matchList:
                raise ValueError("too many matches for %r in %r" % (prefix, matchList))
            else:
                errList = [val[-1] for val in self.valueList]
                raise ValueError("no matches for %r in %r" % (prefix, errList))

    def matchKeys(self, fromDict):
        """Returns a copy of fromDict with keys replaced by their unique match.

        If any key does not have a unique match in the list, raises ValueError.
        If more than one key in fromDict has the same match, raises ValueError
        """
        toDict = {}
        for fromKey, val in fromDict.items():
            toKey = self.getUniqueMatch(fromKey)
            if toKey in toDict:
                raise ValueError("%r contains multiple keys that match %s" % (fromDict, toKey,))
            toDict[toKey] = val
        return toDict

    def setList(self, valueList):
        """Set the list of values to match.
        Non-string-like items are silently ignored.
        """
        if self.ignoreCase:
            self.valueList = [
                (val.lower(), val) for val in valueList if hasattr(val, "lower")
            ]
        else:
            self.valueList = [
                (val,) for val in valueList if hasattr(val, "lower")
            ]
        self.valueList.sort()
