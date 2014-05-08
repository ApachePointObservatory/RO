#!/usr/bin/env python
"""A variant of Tkinter.OptionMenu that adds many features.

Extra features include: help, default handling, the ability to change menu items
and the ability to configure the menu.

OptionMenu is essentially an RO.Wdg.Entry widget (though I don't promise
that *all* methods are implemented).

Note: I had to go mucking with internals, so some of this code is based on
Tkinter's implementation of OptionMenu.

Warnings:
- Do not change the width of the menubutton after creating the OptionMenu; that will conflict
  with workarounds for Tcl/Tk bugs.
- If "" is a valid option then be sure to set noneDisplay to something other than "".
  Otherwise getString will return the default value when the "" is selected.
- As of Tk 8.4.19, MacOS X has poor visual support for background color (isCurrent)
  and no support for foreground color (state) for OptionMenu and for MenuButtons in general.

History:
2002-11-15 ROwen
2002-11-25 ROwen    Added helpURL support.
2003-03-10 ROwen    Overhauled to add support for changing the menu on the fly;
                    added callFunc argument.
2003-03-12 ROwen    Added defIfDisabled
2003-03-14 ROwen    Added addCallback
2003-03-19 ROwen    Added doCheck input to setDefault
2003-03-31 ROwen    Changed 0 to False.
2003-04-03 ROwen    Added preliminary implementation of ConfigMenu;
                    modified so default defValue is the first item.
2003-04-14 ROwen    Added defMenu input.
2003-04-15 ROwen    Modified to use RO.Wdg.CtxMenu 2003-04-15.
2003-04-17 ROwen    Modified to not set defValue = items[0];
                    removed hack that set "" means restore default.
2003-04-24 ROwen    Modified to call callback functions
                    when setDefault called.
2003-06-13 ROwen    Added support for multiple helpText items;
                    bug fix: callFunc sometimes received an extra arg "caller".
2003-07-09 ROwen    Modified to call back with self instead of value;
                    modified to use RO.AddCallback; added getEnable.
2003-08-05 ROwen    Modified so setDefault sets the current value if there is none;
                    bug fix: getString returned None if no value and no default;
                    now returns "" in that case.
2003-10-23 ROwen    Added label, abbrevOK and ignoreCase arguments;
                    removed defIfDisabled since it wasn't being used and added clutter;
                    removed ConfigMenu class since it didn't do much, wasn't being used
                    and I didn't want to port the changes in ConfigMenu.
2003-11-07 ROwen    Modified to not create a StringVar unless it'll be used.
2003-11-18 ROwen    Modified to use SeqUtil instead of MathUtil.
2003-12-09 ROwen    Added argument item to getIndex.
                    This required a different way of handling getIndex
                    because if the item is the string representation
                    of an integer, then tk's menu index returns that integer.
2003-12-17 ROwen    Bug fix: a value of None was being shown as "None"
                    instead of a separator.
2004-03-05 ROwen    Added support for unicode entries.
2004-07-21 ROwen    Modified for updated RO.AddCallback.
2004-08-11 ROwen    Define __all__ to restrict import.
2004-09-01 ROwen    Added checkDef argument to setItems; default is False (new behavior).
2004-09-14 ROwen    Removed unused *args from _doCallback to make pychecker happy.
                    Improved the test code.
2004-11-29 ROwen    Reordered a few methods into alphabetical order.
2005-01-05 ROwen    Added autoIsCurrent, isCurrent and severity support.
                    Modified expandValue method arguments and return value.
                    Modified setDefault: the default for doCheck is now True.
2005-06-16 ROwen    Removed an unused variable (caught by pychecker).
2006-03-23 ROwen    Added isDefault method.
2006-05-24 ROwen    Bug fix: isDefault was broken.
2006-05-26 ROwen    Added trackDefault argument.
                    Bug fix: added isCurrent argument to set.
                    Bug fix: setItems properly preserves non-item-specific help.
2006-10-20 ROwen    Added index method to avoid a tk misfeature.
2007-07-02 ROwen    One can now set the value to None; formerly set(None) was ignored.
                    Added noneDisplay argument: the string to display when the value is None.
                    As a result a defValue of None is legitimate (e.g. restoreDefault will restore it);
                    however, None is slightly special for backwards compatibility in that
                    if the user supplies a var and defValue=None then the var
                    restoreDefault will restore a default value of None (formerly it had no effect)
2007-09-05 ROwen    Added showDefault argument to setDefault.
                    If you supply a var and defValue is None, the value of the var is displayed;
                    this improves compatibility with the pre-2007-07-02 version and Tkinter.OptionMenu.
                    When calling setItems, the current value is now retained if it matches
                    ignoring case and ignoreCase is True (i.e. if it can be used in a call to set).
2007-09-10 ROwen    Added checkCurrent to setItems method. Modified __init__ to use it
                    so that the initial value of the var is shown, even if not in the list.
                    Bug fix: defValue not shown as initial value.
2009-07-23 ROwen    Save the label argument as an attribute.
2011-08-17 ROwen    Modified asValue to return default only if value = noneDisplay and noneDisplay
                    is not a valid value (the latter condition is new).
                    Modified getString to return the default value only if the current value is invalid;
                    formerly it would return the default if the current value was noneDisplay,
                    which caused surprising behavior if noneDisplay was a valid value.
                    Added method isValid.
2012-10-25 ROwen    If width is nonzero on aqua, increase it to work around Tk bug #3580194.
2012-11-16 ROwen    If width is 0 on aqua, set it manually based on content to work around Tk bug #3587262.
2012-11-29 ROwen    Fix demo and add demonstration of fixed width.
2012-11-30 ROwen    Bug fix: width patch was not applied if width changed after the widget was created.
                    Now it is applied by overridden method configure.
2012-11-30 ROwen    Does no width correction if bitmap is shown.
2014-02-04 ROwen    Improve label handling: the widget width was affected by the current value,
                    rather than the width of the label, and label="" was treated as None.
2014-02-10 ROwen    Added forceValid argument to set.
"""
__all__ = ['OptionMenu']

import Tkinter
import RO.AddCallback
import RO.Alg
import RO.SeqUtil
from IsCurrentMixin import AutoIsCurrentMixin, IsCurrentActiveMixin
from SeverityMixin import SeverityActiveMixin
from Menubutton import Menubutton

class _DoItem:
    def __init__(self, var, value):
        self.var = var
        self.value = value
    def __call__(self):
        self.var.set(self.value)

class OptionMenu(Menubutton, RO.AddCallback.TkVarMixin,
    AutoIsCurrentMixin, IsCurrentActiveMixin, SeverityActiveMixin):
    """A Tkinter OptionMenu that adds many features.
    
    Inputs:
    - items     a list of items (strings) for the menu;
                if an item = None then a separator is inserted
    - var       a Tkinter.StringVar (or any object that has set and get methods);
                this is updated when a Menu item is selected or changed.
                If defValue == None then var is used for the initialy displayed value
                (without checking it); otherwise var is set to defValue.
    - defValue  the default value; if specified, must match something in "items"
                (to skip checking, specify defValue = None initially, then call setDefault).
    - noneDisplay  what to display if value is None
    - helpText  text for hot help; may be one string (applied to all items)
                or a list of help strings, one per item. At present
                help is only displayed for the currently chosen item;
                eventually I hope help can be shown for each item in turn
                as one scrolls through the menu.
    - helpURL   URL for longer help; many only be a single string (so far)
    - callFunc  callback function (not called when added);
                the callback receives one argument: this object
    - defMenu   name of "restore default" contextual menu item, or None for none
    - label     label for menu; if None then the label is automatically set to the selected value.
                Use "" to always display an empty menu.
    - abbrevOK  controls the behavior of set and setDefault;
                if True then unique abbreviations are allowed
    - ignoreCase controls the behavior of set and setDefault;
                if True then case is ignored
    - autoIsCurrent controls automatic isCurrent mode
                - if True (auto mode), then the control is current only if all these are so:
                  - set or setIsCurrent is called with isCurrent true
                  - setDefValue is called with isCurrent true
                  - current value == default value
                - if False (manual mode), then isCurrent state is set by the most recent call
                  to setIsCurrent, set or setDefault
    - trackDefault controls whether setDefault can modify the current value:
                - if True and isDefault() true then setDefault also changes the current value
                - if False then setDefault never changes the current value
                - if None then trackDefault = autoIsCurrent (because these normally go together)
    - isCurrent: is the value current?
    - severity: one of: RO.Constants.sevNormal (the default), sevWarning or sevError
    - postCommand: callback function to call when the menu is posted;
                this can be used to change the items before the menu is shown.
    - all remaining keyword arguments are used to configure the Menu.
                text and textvariable are ignored.
    """
    def __init__(self,
        master,
        items,
        var=None,
        defValue=None,
        noneDisplay='',
        helpText=None,
        helpURL=None,
        callFunc=None,
        defMenu = None,
        label = None,
        abbrevOK = False,
        ignoreCase = False,
        autoIsCurrent = False,
        trackDefault = None,
        isCurrent = True,
        postCommand = None,
        severity = RO.Constants.sevNormal,
    **kargs):
        showDefault = not (var and defValue == None)
        if var == None:
            var = Tkinter.StringVar()
        self._tempValue = None
        self._items = []
        self.defValue = None
        self.noneDisplay = noneDisplay or ''
        self.ignoreCase = ignoreCase
        self._helpTextDict = {}
        self._fixedHelpText = None
        self.helpText = None
        self.defMenu = defMenu
        self._matchItem = RO.Alg.MatchList(abbrevOK = abbrevOK, ignoreCase = ignoreCase)
        if trackDefault == None:
            trackDefault = bool(autoIsCurrent)
        self.trackDefault = trackDefault
        
        # handle keyword arguments for the Menubutton
        # start with defaults, update with user-specified values, if any
        # then set text or textvariable
        wdgKArgs = {
            "borderwidth": 2,
            "indicatoron": True,
            "relief": "raised",
            "anchor": "c",
            "highlightthickness": 2,
        }
        wdgKArgs.update(kargs)
        for item in ("text", "textvariable"):
            wdgKArgs.pop(item, None)
        if label is not None:
            wdgKArgs["text"] = label
        else:
            wdgKArgs["textvariable"] = var
        self.label = label
        Menubutton.__init__(self, master = master, helpURL = helpURL, **wdgKArgs)
        self._menu = Tkinter.Menu(self, tearoff = False, postcommand = postCommand)
        self["menu"] = self._menu

        RO.AddCallback.TkVarMixin.__init__(self, var)

        # do after adding callback support, but before setting default (which triggers a callback)
        AutoIsCurrentMixin.__init__(self, autoIsCurrent)
        IsCurrentActiveMixin.__init__(self)
        SeverityActiveMixin.__init__(self, severity)

        self.setItems(items, helpText=helpText, checkCurrent = False, checkDefault = False)
        self.setDefault(defValue, isCurrent = isCurrent, doCheck = True, showDefault = showDefault)
        
        # add callback function after setting default
        # to avoid having the callback called right away
        if callFunc:
            self.addCallback(callFunc, callNow=False)
    
    def asString(self, val):
        """Return display string associated with specified value:
        self.noneDisplay if val == None, val otherwise.
        """
        if val != None:
            return val
        else:
            return self.noneDisplay
    
    def asValue(self, str):
        """Return value associated with display string:
        None if str = self.noneDisplay and str is not a valid value, str otherwise.
        
        Note: this is the inverse transform of asString only if noneDisplay is not a valid value.
        """
        if str == self.noneDisplay and str not in self._items:
            return None
        else:
            return str

    def clear(self):
        """Clear the display
        """
        self._var.set("")

    def ctxConfigMenu(self, menu):
        def addMenuItem(menu, descr, value):
            if descr and value != None:
                menuText = "%s (%s)" % (descr, value)
                def setValue():
                    self._tempValue = None
                    self.set(value)
                menu.add_command(label = menuText, command = setValue)

        addMenuItem(menu, self.defMenu, self.getDefault())
        return True

    def destroy(self):
        """Destroy this widget and the associated menu.
        From Tkinter's OptionMenu"""
        Menubutton.destroy(self)
        self._menu = None
    
    def expandValue(self, value):
        """Expand a value, unabbreviating and case correcting,
        as appropriate.
        
        Returns:
        - value: the expanded value, or the original value if None or invalid.
            Expansion of abbreviations and correction of case
            are controlled by the ignoreCase and abbrevOK flags
            supplied when creating this menu.
        - isOK  if False, the value was not valid and was not expanded.
            Note that None is always valid, but never expanded.
        """
        if value == None:
            return None, True

        try:
            return self._matchItem.getUniqueMatch(value), True
        except ValueError:
            return value, False
    
    def getDefault(self):
        """Returns the default value.
        """
        return self.defValue

    def getIndex(self, item=None):
        """Returns the index of the specified item,
        or the currently selected item if item=None.
        
        Originally used self._menu.index,
        but that gives the wrong answer if the item
        is the string representation of an integer.

        Returns None if the specified item is not present
        or if item=None and no item is selected.
        """
        if item == None:
            item = self._var.get()
        else:
            item = str(item)

        try:
            return self._items.index(item)
        except ValueError:
            return None
    
    def getMenu(self):
        """Returns the Menu object from the OptionMenu;
        handy if you want to modify it in some way but use sparingly
        as you can easily manipulate it to foul up this widget
        """
        return self._menu
    
    def getString(self):
        """Returns the current value of the field, or the default if the current value is not valid.
        
        If you want the displayed value, regardless of validity, use getVar().get()
        """
        if not self.isValid():
            return self.defValue or ""
        return self._var.get()
    
    def getVar(self):
        """Returns the variable that is set to the currently selected item
        """
        return self._var
    
    def index(self, val=None):
        """Return the index of an item.
        
        Inputs:
        - val: the item for which an index is desired;
                None for the currently selected item.
        
        Raise ValueError if no match. This can happen even if value is None
        because the displayed value can be forced equal to a value
        not in the list of allowed values.
        
        Implemented to work around tktoolkit-Bugs-1581435:
        "menu index wrong if label is an integer".
        """
        if val == None:
            val = self._var.get()
        return self._items.index(val)
    
    def insert_separator(self, indx, **kargs):
        """Inserts a separator at the appropriate location.
        Note: the interal self._list is not modified,
        so if you choose to update the list of items later,
        your new list should not include the separators
        that you inserted.
        """
        self._menu.insert_separator(indx, **kargs)
    
    def isDefault(self):
        """Return True if current value matches the default value.
        
        Note that it returns false if the current value is not valid.
        """
        return self._var.get() == self.asString(self.defValue)
    
    def isValid(self):
        """Return True if the currently displayed value is one of the items set by setItems
        """
        return self._var.get() in self._items \
            or (self._tempValue is not None and self._var.get() == self._tempValue)
    
    def restoreDefault(self):
        """Restore the default value.
        """
        #print "restoreDefault(); currValue=%r, defValue=%r" % (self._var.get(), self.defValue,)
        self._var.set(self.asString(self.defValue))

    def set(self, newValue, isCurrent=True, doCheck=True, forceValid=False, *args, **kargs):
        """Changes the currently selected value.

        Inputs:
        - newValue: new value to set
        - isCurrent: is the new value current?
        - doCheck: test if the new value is one of the allowed items? Ignored if forceValid is true
        - forceValid: the new value is forced to be valid. The value is cleared
            when the user selects a menu item or set is called again.
        *args, **kargs: ignored
        """
        self._tempValue = None
        newValue, isOK = self.expandValue(newValue)
        if not isOK:
            if forceValid:
                self._tempValue = str(newValue)
            elif doCheck:
                raise ValueError("Value %r invalid" % newValue)
    
        self.setIsCurrent(isCurrent)
        self._var.set(self.asString(newValue))

    def setDefault(self, newDefValue, isCurrent=None, doCheck=True, showDefault=None, *args, **kargs):
        """Changes the default value. If the current value is None, also sets the current value.

        Inputs:
        - newDefValue: the new default value
        - isCurrent: if not None, set the _isCurrent flag accordingly.
            Typically this is only useful in autoIsCurrent mode.
        - doCheck: check that the new default value is in the menu
            (ignored if newDefValue is None)
        - showDefault: one of:
          - True: show the new default
          - None: show the new default if self.trackDefault is True and the current value is the default.
          - False: do not show the new default

        Error conditions:
        - Raises ValueError and leaves the default unchanged
          if doCheck is True and if the new default value is neither in the list of values
          nor is None.
        """
        #print "setDefault(newDeffValue=%r, isCurrent=%r, doCheck=%r)" % (newDefValue, isCurrent, doCheck)
        newDefValue, isOK = self.expandValue(newDefValue)
        if not isOK and doCheck:
            raise ValueError("Default value %r invalid" % newDefValue)
        if showDefault == None:
            showDefault = self.trackDefault and self.isDefault()
        self.defValue = newDefValue
        if isCurrent != None:
            self.setIsCurrent(isCurrent)

        if showDefault:
            self.restoreDefault()
        else:
            self._doCallbacks()
    
    def setItems(self, items, isCurrent=None, helpText=None, checkCurrent=True, checkDef=False, **kargs):
        """Replaces the current set of items (but only if the new
        list is different than the old one).
        
        Inputs:
        - see init for most of them
        - isCurrent is ignored; it's purely for compatibility with key variable callbacks
        - checkCurrent  if True, if the current value is only retained if it is in the list of new items
          (and if not, the default is restored); if False, the current value is always retained
        - checkDef  if True, set default to None if it is not in the new list of items
        - if helpText is None then the old helpText is left alone if it was a single string
          (rather than a set of strings) and is nulled otherwise
        
        Warnings:
        - If the default is not present in the new list,
        then the default is silently nulled.
        """
        #print "setItems(items=%s, isCurrent=%s, helpText=%s, checkDef=%s)" % (items, isCurrent, helpText, checkDef)
        # make sure items is a list (convert if necessary)
        items = list(items)

        # update help info
        self._helpTextDict = {}
        if helpText == None:
            # if existing help text is fixed, keep using it
            # otherwise there is no help (cannot reuse item-specific help)
            self.helpText = self._fixedHelpText
        elif RO.SeqUtil.isSequence(helpText):
            # new item-specific help
            nItems = len(items)
            self._fixedHelpText = None
            if len(helpText) != nItems:
                raise ValueError, "helpText list has %d entries but %d wanted" % \
                    (len(helpText), nItems)
            for ii in range(nItems):
                self._helpTextDict[items[ii]] = helpText[ii]
        else:
            # new fixed help
            self.helpText = self._fixedHelpText = helpText
        
        # if no change (ignoring the difference between a list and a tuple)
        # then do nothing
        if items == self._items:
            return

        # update _matchItem
        self._matchItem.setList(items)
                
        # if the default value is not present, null the default value
        # don't bother with abbrev expansion; defValue should already be expanded
        if checkDef and self.defValue not in items:
            self.defValue = None
        
        # rebuild the menu
        self._items = items
        self._addItems()
        self._menu.delete(0, "end")
        self._addItems()
        
        if checkCurrent:
            currValue = self._var.get()
            try:
                self.set(currValue, isCurrent=self.getIsCurrent(), doCheck=True)
            except ValueError:
                self.restoreDefault()
        
        if self._helpTextDict:
            self.helpText = self._helpTextDict.get(self._var.get())

    def _addItems(self):
        """Adds the list of items to the menu;
        must only be called when the menu is empty
        and self._items has been set
        """
        for item in self._items:
            if item == None:
                self._menu.add_separator()
            else:
                self._menu.add_command(
                    label=item,
                    command=_DoItem(self._var, item),
                )

    def _doCallbacks(self):
        self._basicDoCallbacks(self)
        if self._helpTextDict:
            self.helpText = self._helpTextDict.get(self._var.get())


if __name__ == "__main__":
    import Label
    import PythonTk
    import StatusBar
    root = PythonTk.PythonTk()
    
    def callFunc(wdg):
        label.set(wdg.getString())

    items = ("Earlier", "Now", "Later", None, "Never")
    helpTexts = ("Help for Earlier", "Help for Now", "help for Later", "", "Help for Never")
    menu1 = OptionMenu(root,
        items = items,
        defValue = "Now",
        callFunc = callFunc,
        defMenu = "Default",
        helpText = helpTexts,
        autoIsCurrent = True,
    )
    menu1.grid(row=0, column=0, sticky="w")

    items = ("MmmmmNnnnn A", "Really long menu item", "abcdef", "C")
    menu2 = OptionMenu(root,
        items = items,
        defValue = "MmmmmNnnnn A",
        callFunc = callFunc,
        defMenu = "Default",
        helpText = "width=0",
    )
    menu2.grid(row=0, column=1, sticky="w")

    menu3 = OptionMenu(root,
        items = items,
        defValue = "MmmmmNnnnn A",
        callFunc = callFunc,
        defMenu = "Default",
        helpText = "width=12 via configure",
    )
    menu3.configure(width=12)
    menu3.grid(row=1, column=1, sticky="w")

    menu4 = OptionMenu(root,
        items = items,
        defValue = "MmmmmNnnnn A",
        callFunc = callFunc,
        defMenu = "Default",
        indicatoron = False,
        helpText = "indicatoron=False",
    )
    menu4.grid(row=0, column=2, sticky="w")

    menu5 = OptionMenu(root,
        items = items,
        defValue = "MmmmmNnnnn A",
        callFunc = callFunc,
        defMenu = "Default",
        indicatoron = False,
        helpText = "width=12 via ['width'], indicatoron=False",
    )
    menu5["width"] = 12
    menu5.grid(row=1, column=2, sticky="w")

    label = Label.Label(root, width=20, anchor="w", helpText="most recently selected value")
    label.grid(row=2, column=0, columnspan=4, sticky="w")
    
    statusBar = StatusBar.StatusBar(root, width=20)
    statusBar.grid(row=3, column=0, columnspan=4, sticky="ew")

    root.mainloop()
