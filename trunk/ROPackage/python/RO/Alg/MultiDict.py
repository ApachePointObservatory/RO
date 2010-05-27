#!/usr/bin/env python
"""A dictionary that stores a list of values for each key.

Note: one could subclass dict but this requires writing
explicit methods for setdefault, copy, and possibly others.
Only do this if extra performance is required.

History
1-1 Russell Owen 8/8/00
1-2 corrected an indentation error
2003-05-06 ROwen    Test copy and setdefault; renamed to ListDict
                    and added SetDict.
2010-05-18 ROwen    Modified SetDict to use sets
"""
import UserDict

class ListDict(UserDict.UserDict):
    """A dictionary whose values are a list of items.
    """
    def __setitem__(self, key, val):
        """Add a value to the list of values for a given key, creating a new entry if necessary.

        Supports the notation: aListDict[key] = val
        """
        if self.data.has_key(key):
            self.data[key].append(val)
        else:
            self.data[key] = [val]
    
    def addList(self, key, valList):
        """Append values to the list of values for a given key, creating a new entry if necessary.
        
        Inputs:
        - valList: an iterable collection (preferably ordered) of values
        """
        valList = list(valList)
        if self.data.has_key(key):
            self.data[key] += valList
        else:
            self.data[key] = valList

    def remove(self, key, val):
        """removes the specified value from the list of values for the specified key;

        raise KeyError if key not found
        raise ValueError if val not found
        """
        self.data.get(key).remove(val)

class SetDict(ListDict):
    """A dictionary whose values are a set of items, meaning
    a list of unique items. Duplicate items are silently not added.
    """
    
    def __setitem__(self, key, val):
        """Add a value to the set of values for a given key, creating a new entry if necessary.
        
        Duplicate values are silently ignored.
        
        Supports the notation: aListDict[key] = val
        """
        valSet = self.data.get(key)
        if valSet == None:
            self.data[key] = set([val])
        else:
            valSet.add(val)
    
    def addList(self, key, valList):
        """Add values to the set of values for a given key, creating a new entry if necessary.
        
        Duplicate values are silently ignored.
        
        Inputs:
        - valList: an iterable collection of values
        """
        valSet = self.data.get(key)
        if valSet == None:
            self.data[key] = set(valList)
        else:
            valSet.update(valList)


if __name__ == "__main__":
    import RO.StringUtil

    ad = ListDict()
    ad["a"] = "foo a"
    ad["a"] = "foo a"
    ad["a"] = "bar a"
    ad[1] = "foo 1"
    ad[1] = "foo 2"
    ad[1] = "foo 2"
    ad2 = ad.copy()
    ad2.setdefault("a", "foo")
    ad2.setdefault("a", "foo")
    ad2.setdefault("b", "bar")
    ad2.setdefault("b", "bar")
    print "listdict:"
    print RO.StringUtil.prettyDict(ad)
    print "listdict copy (modified):"
    print RO.StringUtil.prettyDict(ad2)
    

    ad = SetDict()
    ad["a"] = "foo a"
    ad["a"] = "foo a"
    ad["a"] = "bar a"
    ad[1] = "foo 1"
    ad[1] = "foo 2"
    ad[1] = "foo 2"
    ad2 = ad.copy()
    ad2.setdefault("a", "foo")
    ad2.setdefault("a", "foo")
    ad2.setdefault("b", "bar")
    ad2.setdefault("b", "bar")
    print "setdict:"
    print RO.StringUtil.prettyDict(ad)
    print "setdict copy (modified):"
    print RO.StringUtil.prettyDict(ad2)
