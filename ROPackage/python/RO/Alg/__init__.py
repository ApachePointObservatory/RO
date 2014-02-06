"""Basic algorithms.

Many of these are from other authors (as noted in the code).

Some are obsolete:
- GenericCallback: use functools.partial
- OrderedDictuse: use collections.OrderedDict
- MultiListIter: use itertools.izip
"""
from .GenericCallback import *
from .IDGen import *
from .MatchList import *
from .MultiDict import *
from .MultiListIter import *
from .OrderedDict import *
from .RandomWalk import *
from .SavedDict import *
