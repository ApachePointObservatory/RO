#!/usr/bin/env python
"""A widget to display a scrolling log of information. Log entries
may be categorized and each category may be displayed in a different color.
Each category may be individually shown or hidden.

Sutbleties:
* The display auto-scrolls if the scrollbar is at the bottom.
* If a category is shown or hidden, the display attempts to scroll intelligently:
    * If the text area has focus, it scrolls to keep the insertion cursor in view
    * Otherwise, the usual autoscroll rule applies: if the scrollbar is at the bottom,
      it is kept there, else it is left alone
* Search is backwards, starting from the current end of selection,
    if there is a selection, else from the end. Thus you can search repeatedly
    to get ever older finds. However, the results can be confusing
    if there is an existing selection before you start the search.

To Do:
* Clean up interface to _ShowTagWdg; I don't really want to pass in yscroll
but I don't know any other way to find out if the textWdg is scrolled to
the end -- which is needed to do a good job of maintaining scroll when
showing and hiding categories

History:
2001-11-15 ROwen    The first version with history.
2002-03-05 ROwen    Modified to use GenericCallback.
2002-03-11 ROwen    Added LogWdg.setColor and ColorPrefVar handling.
2002-05-13 ROwen    Support multiple sets of categories.
2002-08-08 ROwen    Moved to RO.Wdg.
2002-11-22 ROwen    Made it difficult or impossible to change the logged data.
2002-12-05 ROwen    Added support for URL-based help.
2002-12-20 ROwen    Removed any attempt to import RO.Wdg...., thanks to pychecker.
2003-03-11 ROwen    Changed to use OptionMenu instead of ROOptionMenu.
2003-04-15 ROwen    Modified to use RO.Wdg.CtxMenu 2003-04-15.
2003-06-18 ROwen    Bug fix: was not initially auto-scrolling if not initially displayed
                    (Tk or Tkinter's changed how it reports scroll position if the
                    window was never displayed);
                    Modified to test for StandardError instead of Exception
2003-09-30 ROwen    Fixed to use 2003-07-09 version of OptionMenu.
2004-05-18 ROwen    Moved import sys to if __name__ ==...
2004-08-11 ROwen    Modified to use RO.Wdg.Text, for an enhanced contextual menu.
                    Modified the other widgets to their RO.Wdg versions
                    to make it easier to set the help URL.
                    Define __all__ to restrict import.
2006-06-01 ROwen    Added helpText argument.
                    Made the control frame explicit so it can be easily hidden.
2006-10-04 ROwen    Type <return> to search backwards, <control-return> to search forwards.
                    Typing in find entry field sets focus to text area, so result is shown.
2006-10-25 ROwen    Major overhaul. Now includes just the log area
                    (users are expected to add the extra controls needed).
                    Includes powerful new methods for filtering and searching.
                    - unified search method
                    - added findAll
                    - addOutput takes tags argument instead of category
                    - removed addOuputNL method.
2006-11-03 ROwen    Added findTag method.
2007-02-13 ROwen    Added setEnable method.
2007-09-19 ROwen    Fixed setEnable method and stopped importing three unused modules. Thanks, pychecker!
2007-12-22 ROwen    Fixed incompatiblity with Tcl/Tk 8.5: text.index returns an object, not a string.
2008-04-22 ROwen    Added addMsg method.
2009-08-25 ROwen    Added doAutoScroll option.
2010-03-05 ROwen    Added tabs option.
2010-11-11 ROwen    Added support for severity.
2010-06-25 ROwen    Added addOutputList and isScrolledToEnd methods.
                    Changed findTag to search from the insertion cursor if there is no selection,
                    rather than the beginning or end. This offers the user a natural way to specify
                    the start of the search.
2010-06-28 ROwen    Removed two statements that had no effect (thanks to pychecker).
"""
__all__ = ['LogWdg']

import Tkinter
import RO.Alg
import Button
import Entry
import Label
import OptionMenu
import Text

_AllTextTag = "__alltext"

_SevTagDict = RO.Alg.OrderedDict(
    (sev, "__sev_%s" % (name,)) for sev, name in RO.Constants.SevNameDict.iteritems())
_SevTagListDict = RO.Alg.OrderedDict(
    (sev, _SevTagDict.values()[ind:]) for ind, sev in enumerate(_SevTagDict.iterkeys()))

class LogWdg(Tkinter.Frame):

    def __init__(self,
        master,
        maxLines = 1000,
        helpText = None,
        helpURL = None,
        width = 80,
        height = 20,
        doAutoScroll = True,
        tabs = "",
    **kargs):
        """
        Inputs:
        - master: master widget
        - maxLines: the max number of lines to display, ignoring wrapping
        - helpText: the help text for the main text widget.
        - helpURL: the URL of a help page
        - height: height of text area, in lines
        - width: width of text area, in characters
        - tabs: set tab stops for Text widget (see Tk documentation for Text)
        - doAutoScroll: auto-scroll to end of text when new messages are added
            (if already at end of text) by default.
        - **kargs: additional keyword arguments for Frame
        """
        Tkinter.Frame.__init__(self, master=master, **kargs)
        
        self.maxLineIndex = maxLines + 1
        self.doAutoScroll = bool(doAutoScroll)
        
        self.yscroll = Tkinter.Scrollbar (
            master = self,
            orient = "vertical",
        )
        self.text = Text.Text (
            master = self,
            yscrollcommand = self.yscroll.set,
            wrap = "word",
            width = width,
            height = height,
            tabs = tabs,
            readOnly = True,
            helpText = helpText,
            helpURL = helpURL,
        )
        self.yscroll.configure(command=self.text.yview)
        self.text.grid(row=1, column=0, sticky="nsew")
        self.yscroll.grid(row=1, column=1, sticky="ns")
        
        self.text.tag_configure(_AllTextTag)

        # set up severity tags and tie them to color preferences
        self._severityPrefDict = RO.Wdg.WdgPrefs.getSevPrefDict()
        for sev, sevTag in _SevTagDict.iteritems():
            pref = self._severityPrefDict[sev]
            if sev == RO.Constants.sevNormal:
                # normal color is already automatically updated
                # but do make tag known to text widget
                self.text.tag_configure(sevTag)
                continue
            pref.addCallback(RO.Alg.GenericCallback(self._updSevTagColor, sevTag), callNow=True)
        
        self.findCountVar = Tkinter.IntVar()

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        
        # disable editing actions
        def killEvent(evt):
            return "break"

        self.text.bind("<<Cut>>", killEvent)
        self.text.bind("<<Paste>>", killEvent)
        self.text.bind("<<Clear>>", killEvent)
        self.text.bind("<Key>", killEvent)
    
    def addMsg(self, astr, tags=(), severity=RO.Constants.sevNormal):
        """Append a line of data to the log, adding a trailing \n
        
        If you do not want a trailing \n added for you then call addOutput instead.
        
        Inputs:
        - astr: data to append (a trailing \n IS added for you)
        - tags: tags for the text. Warning: tags whose names begin with __ (two underscores)
            are reserved for internal use.
        - severity: one of the RO.Constants.sevX constants
        """
        self.addOutput(astr + "\n", tags=tags, severity=severity)
    
    def addOutput(self, astr, tags=(), severity=RO.Constants.sevNormal):
        """Append data to the log without adding a trailing \n.
        
        If you want a trailing \n then you must supply it or call addMsg instead.
        
        Inputs:
        - astr: text to append (a trailing \n is NOT added for you)
        - tags: tags for the text
        - severity: one of the RO.Constants.sevX constants
        """
        #print "addOutput(astr=%r; tags=%r)" % (astr, tags)
        # set auto-scroll flag true if scrollbar is at end
        doScrollToEnd = self.doAutoScroll and self.isScrolledToEnd()
        
        # insert tagged text at end
        tags = (_AllTextTag, _SevTagDict[severity]) + tuple(tags)
        tagStr = " ".join(tags)
        self.text.insert("end", astr, tagStr)
        
        # truncate extra lines, if any
        extraLines = int(float(str(self.text.index("end"))) - self.maxLineIndex)
        if extraLines > 0:
            self.text.delete("1.0", str(extraLines) + ".0")
        
        if doScrollToEnd:
            self.text.see("end")
    
    def addOutputList(self, strTagSevList):
        """Append a list of (text, tags, severity) data to the log.
        
        You are responsible for supplying \n at the end of each line.
        
        Each element of the list must contain exactly three entries:
        - astr: the text to append; you must supply \n for the end of each line
        - tags: a collection of tags
        - severity: one of the RO.Constants.sevX constants
        """
        if not strTagSevList:
            return

        # create strTagList, adding the severity tag and _AllTextTag tag;
        # this also verifies the format of strTagSevList before using it for anything
        try:
            strTagList = [(astr, (_AllTextTag, _SevTagDict[severity]) + tuple(tags))
                for astr, tags, severity in strTagSevList]
        except Exception, e:
            raise RuntimeError("Could not parse strTagSevList: %s" % (RO.StringUtil.strFromException(e),))

        doScrollToEnd = self.doAutoScroll and self.isScrolledToEnd()

        maxLines = self.maxLineIndex - 1
        if maxLines < len(strTagList):
            # new text is so long it overfills the buffer
            self.clearOutput()
            doScrollToEnd = True
            strTagList = strTagList[-maxLines:]
        else:
            extraLines = len(strTagList) + int(float(str(self.text.index("end"))) - self.maxLineIndex)
            if extraLines > 0:
                self.text.delete("1.0", str(extraLines) + ".0")

        # flatten strTagList to str0, tag0, str1, tag1,...
        flatStrTagList = [item for strOrTag in strTagList for item in strOrTag]
        self.text.insert("end", *flatStrTagList)
        
        if doScrollToEnd:
            self.text.see("end")
        
    def clearOutput(self):
        self.text.delete("1.0", "end")

    def findTag(self, tag, backwards=False, doWrap=False):
        """Find and select the next instance of a specified tag.
        The search starts from the current selection, if any,
        else from the insertion cursor.

        Warning: due to a bug in tk or Tkinter, you must not call this directly
        from a callback function that modifies the text being searched for
        (e.g. an Entry callback). If you do this, the count variable
        may not be updated, in which case RuntimeError is raised.
        Call using "after" to avoid the problem.
        
        Inputs:
        - tag: tag for which to search
        - backwards: True to search backwards
        - doWrap: True to wrap search around
        """
        self.text.focus_set()
        if not tag:
            self.bell()
            return
        selRange = self.text.tag_ranges("sel")
        if backwards:
            if selRange:
                startIndex = selRange[0]
            else:
                startIndex = self.text.index("insert")
            stopIndex = "1.0"
            findFunc = self.text.tag_prevrange
        else:
            if selRange:
                startIndex = selRange[1]
            else:
                startIndex = self.text.index("insert")
            stopIndex = "end"
            findFunc = self.text.tag_nextrange

        if doWrap:
            stopIndex = None
        
        foundRange = findFunc(tag, startIndex, stopIndex)
        if not foundRange:
            self.bell()
            return
        
        foundStart, foundEnd = foundRange

        # text found; change selection to it
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", foundStart, foundEnd)
        self.text.see(foundStart)

    def getSeverityTags(self, minSeverity):
        """Return all severity tags that have severity >= minSeverity
        
        Inputs:
        - minSeverity: minimum severity for returned tags; an RO.Constants.sev constant
        """
        return _SevTagListDict[minSeverity]
    
    def isScrolledToEnd(self):
        """Return True if scrollbar is at the end or if not sure (window not yet painted)
        """
        # test two cases:
        # scrollPos[1] = 1.0: scrolled to end
        # scrollPos[1] = scrollPos[0]: window has not yet been painted
        scrollPos = self.yscroll.get()
        return scrollPos[1] == 1.0 or scrollPos[0] == scrollPos[1]
    
    def search(self, searchStr, backwards=False, doWrap=False, elide=True, noCase=False, regExp=False):
        """Find and select the next instance of a specified string.
        The search starts from the current selection, if any,
        else from the beginning/end if forwards/backwards.

        Warning: due to a bug in tk or Tkinter, you must not call this directly
        from a callback function that modifies the text being searched for
        (e.g. an Entry callback). If you do this, the count variable
        may not be updated, in which case RuntimeError is raised.
        Call using "after" to avoid the problem.
        
        Inputs:
        - searchStr: string for which to search
        - backwards: True to search backwards
        - doWrap: True to wrap search around
        - elide: True to search elided text
        - noCase: True to ignore case
        - regExp: True for regular expression search
        """
        self.text.focus_set()
        if not searchStr:
            self.bell()
            return
        selRange = self.text.tag_ranges("sel")
        if backwards:
            if selRange:
                startIndex = selRange[0]
            else:
                startIndex = "end"
            stopIndex = "1.0"
        else:
            if selRange:
                startIndex = selRange[1]
            else:
                startIndex = "1.0"
            stopIndex = "end"

        if doWrap:
            stopIndex = None

        self.findCountVar.set(-1)
        startIndex = self.text.search(
            searchStr,
            startIndex,
            stopindex = stopIndex,
            backwards = backwards,
            elide = elide,
            nocase = noCase,
            regexp = regExp,
            count = self.findCountVar,
        )
        if not startIndex:
            self.bell()
            return
        foundCount = self.findCountVar.get()
        if foundCount < 1:
            if foundCount == 0:
                return
            raise RuntimeError("Found string but count not set; try calling from \"after\"")
        
        # text found; change selection to it
        self.text.tag_remove("sel", "1.0", "end")
        endIndex = "%s + %s chars" % (startIndex, foundCount)
        self.text.tag_add("sel", startIndex, endIndex)
        self.text.see(startIndex)
    
    def findAll(self, searchStr, tag, lineTag=None, removeTags=True, elide=True, noCase=False, regExp=False, startInd="1.0"):
        """Find and tag all instances of a specified string.
        
        Warning: due to a bug in tk or Tkinter, you must not call this directly
        from a callback function that modifies the text being searched for
        (e.g. an Entry callback). If you do this, the count variable
        may not be updated, in which case RuntimeError is raised.
        Call using "after" to avoid the problem.
        
        Inputs:
        - searchStr: string for which to search
        - tag: tag for the found data; if None then only lineTag is applied.
        - lineTag: tag for whole line; if None then only tag is applied.
        - removeTags: remove tag(s) from all text before performing search?
            if True then the search replaces the text that is tagged
            otherwise the search supplements the text that is tagged
        - elide: True to search elided text
        - noCase: True to ignore case
        - regExp: True for regular expression search
        - startInd: starting index (defaults to "1.0" = the beginning)
        
        Returns the number of matches.
        
        Notes:
        - Make sure tag is "above" lineTag if you want its characteristics to dominate.
          You can tag_configure tag later, or use tag_raise.
        - To search elided text, first show all text, then re-elide.
          Tkinter does not support the tk's elide argument to search--
          probably because older versions of tk don't support it.
        """
        #print "findAll(searchStr=%r, tag=%r, lineTag=%r, removeTags=%r, elide=%r, noCase=%r, regExp=%r, startInd=%r)" % \
        #   (searchStr, tag, lineTag, removeTags, elide, noCase, regExp, startInd)
        nFound = 0
        if not (tag or lineTag):
            raise ValueError("tag and lineTag cannot both be None")

        if removeTags:
            if tag:
                self.text.tag_remove(tag, "1.0", "end")
            if lineTag:
                self.text.tag_remove(lineTag, "1.0", "end")
        
        if not searchStr:
            #print "no search string"
            return nFound
        
        searchStartInd = startInd
        self.findCountVar.set(-1)
        while True:
            foundStartInd = self.text.search(
                searchStr,
                searchStartInd,
                stopindex = "end",
                backwards = False,
                elide = elide,
                nocase = noCase,
                regexp = regExp,
                count = self.findCountVar,
            )
            if not foundStartInd:
                return nFound
            foundCount = self.findCountVar.get()
            if foundCount < 1:
                if foundCount == 0:
                    return nFound
                raise RuntimeError("Found string but count not set; try calling from \"after\"")
            
            nFound += 1
            foundEndInd = self.text.index("%s + %s chars" % (foundStartInd, foundCount))
            #print "foundStartInd=%r; foundEndInd=%r" % (foundStartInd, foundEndInd)

            if lineTag:
                lineStartInd = self.text.index("%s linestart" % (foundStartInd,))
                lineEndInd = self.text.index("%s lineend" % (foundEndInd,))
                self.text.tag_add(lineTag, lineStartInd, lineEndInd)
            if tag:
                self.text.tag_add(tag, foundStartInd, foundEndInd)
            searchStartInd = foundEndInd
            #print "searchStartind=%r" % (searchStartInd,)
        return nFound
    
    def setEnable(self, doEnable):
        """Set enabled state.
        """
        self.text.setEnable(doEnable)

    def showAllText(self):
        """Shows all text, undoing the effect of showTags"""
        for tag in self.text.tag_names():
            if tag == _AllTextTag:
                self.text.tag_configure(tag, elide=False)
            else:
                self.text.tag_configure(_AllTextTag, elide="")
    
    def showTagsOr(self, tags):
        """Only show text that is tagged with one or more of the specified tags.
        """
        #print "showTagsOr(%r)" % (tags,)
        tags = set(tags)
        for tag in self.text.tag_names():
            if tag == _AllTextTag:
                self.text.tag_configure(tag, elide=True)
            elif tag in tags:
                self.text.tag_configure(tag, elide=False)
            else:
                self.text.tag_configure(tag, elide="")
    
    def showTagsAnd(self, tags):
        """Only show text that is tagged with all of the specified tags.
        """
        #print "showTagsAnd(%r)" % (tags,)
        tags = set(tags)
        for tag in self.text.tag_names():
            if tag == _AllTextTag:
                self.text.tag_configure(_AllTextTag, elide=False)
            elif tag in tags:
                self.text.tag_configure(tag, elide="")
            else:
                self.text.tag_configure(tag, elide=True)

    def _updSevTagColor(self, sevTag, color, colorPref):
        """Apply the current color appropriate for the current severity.
        
        Called automatically. Do NOT call manually.
        """
        #print "_updSevTagColor(sevTag=%r, color=%r, colorPref=%r)" % (sevTag, color, colorPref)
        self.text.tag_configure(sevTag, foreground=color)


if __name__ == '__main__':
    import random
    import sys
    import PythonTk
    root = PythonTk.PythonTk()
    
    testFrame = LogWdg (
        master=root,
        maxLines=50,
    )
    testFrame.grid(row=0, column=0, sticky="nsew")

    severityList = RO.Constants.SevNameDict.keys()
    
    entry = Tkinter.Entry(root)
    entry.grid(row=1, column=0, sticky="nsew")
    
    def addMsg(msgStr):
        """Add a message with random severity"""
        testFrame.addMsg(msgStr, severity=random.choice(severityList))
        
    def addTolog(evt=None):
        try:
            msgStr = entry.get()
            entry.delete(0,"end")
            
            addMsg(msgStr)
        except StandardError, e:
            sys.stderr.write ("Could not extract or send: %s\n" % (astr))
            sys.stderr.write ("Error: %s\n" % (e))

    entry.bind('<KeyPress-Return>', addTolog)

    # supply some fake data
    for ii in range(10):
        addMsg("sample entry %s" % ii)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    root.mainloop()
