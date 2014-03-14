#!/usr/bin/env python
"""Widget to manage named presets of an input container list

History:
2014-02-03 ROwen
2014-02-07 ROwen    Renamed config to preset
2014-03-13 ROwen    Bug fix: was not recording default values. The fix required an update to InputCont.
2014-03-14 ROwen    Added helpText and helpURL arguments.
"""
import functools
import Tkinter
import Entry
import Label
import InputDialog
import OptionMenu
import CtxMenu

class InputContPresetsWdg(Tkinter.Menubutton):
    """Widget to manage named presets for an input container list

    Manages a list of named presets, with two categories:
    - user presets, which the user can modify and are auto-persisted and reloaded
    - standard presets, which cannot be modified by the user
    """
    def __init__(self,
        master,
        sysName,
        userPresetsDict,
        inputCont,
        stdPresets=None,
        helpText=None,
        helpURL=None,
    **kwargs):
        """Construct a PresetWdg

        Inputs:
        - master: master widget
        - sysName: name of this system in userPresetsDict
        - userPresetsDict: a dict of user-specified presets for various systems; use an RO.Alg.SavedDict
            if you want the user presets to be auto-loaded at startup and auto-saved when changed.
            Only userPresetsDict[sysName] applies to this system (inputCont).
            The format of the value userPresetsDict[sysName] is the same as the format of stdPresets.
        - stdPresets: standard presets for this system. None, or a dict whose entries are:
            preset name: preset as a dict of values in the form required by inputCont.setValueDict()
        - inputCont: input container list being configured (an RO.InputCont.ContList)
        - helpText: a string that describes the widget
        - helpURL: URL for on-line help
        - **kwargs: additional config arguments for Tkinter.Menubutton. 

        If user presets and standard presets both exist then user presets are listed first,
        followed by a separator and then the standard presets.
        Within each group (user and standard), presets are listed alphabetically.
        """
        self._sysName = sysName
        self._userPresetsDict = userPresetsDict
        self._stdPresets = stdPresets or dict()
        self._inputCont = inputCont
        self.helpText = helpText

        wdgKArgs = {
            "borderwidth": 2,
            "indicatoron": True,
            "relief": "raised",
            "anchor": "c",
            "highlightthickness": 2,
        }
        wdgKArgs.update(kwargs)
        Tkinter.Menubutton.__init__(self, master, **wdgKArgs)
        CtxMenu.addCtxMenu(wdg = self, helpURL = helpURL)

        self._menu = Tkinter.Menu(self, tearoff=False)

        editMenu = Tkinter.Menu(
            self._menu,
            tearoff = False,
        )
        editMenu.add_command(
            label = "Save...",
            command = self._doSave,
        )
        editMenu.add_command(
            label = "Rename...",
            command = self._doRename,
        )
        editMenu.add_command(
            label = "Delete...",
            command = self._doDelete,
        )

        self._menu.add_cascade(
            label = "Edit",
            menu = editMenu,
        )
        self["menu"] = self._menu

        self._begNameIndex = 1

        self._updateNames()

    def setStdPresets(self, stdPresets):
        """Set standard presets, replacing existing standard presets, if any

        Inputs:
        - stdPresets: standard presets for this system. None, or a dict whose entries are:
            preset name: preset as a dict of values in the form required by inputCont.setValueDict()
        """
        self._stdPresets = stdPresets or dict()
        self._updateNames()

    def _updateNames(self):
        """Update names in option menu
        """
        self._menu.delete(self._begNameIndex, "end")
        userPresetNames = self._getUserPresetNames()
        for presetName in userPresetNames:
            self._menu.add_command(
                label = presetName,
                command = functools.partial(self._applyUserPreset, presetName),
            )

        stdPresetsNames = self._getStdPresetNames()
        if bool(userPresetNames) and bool(stdPresetsNames):
            self._menu.add_separator()
        for presetName in stdPresetsNames:
            self._menu.add_command(
                label = presetName,
                command = functools.partial(self._applyDefaultPreset, presetName),
            )

    def _getStdPresetNames(self):
        """Get a sorted list of default preset names
        """
        return sorted(self._stdPresets.iterkeys())

    def _getUserPresetNames(self):
        """Get a sorted list of current preset names
        """
        preset = self._userPresetsDict.get(self._sysName, dict())
        return sorted(preset.iterkeys())

    def _applyUserPreset(self, presetName):
        """User selected a preset; apply it
        """
        preset = self._userPresetsDict[self._sysName]
        inputContPreset = preset[presetName]
        self._inputCont.setValueDict(inputContPreset)

    def _applyDefaultPreset(self, presetName):
        inputContPreset = self._stdPresets[presetName]
        self._inputCont.setValueDict(inputContPreset)

    def _doSave(self):
        """Save current preset
        """
        dialogBox = SaveDialog(master=self, currNameList=self._getUserPresetNames())
        newName = dialogBox.result
        if not newName:
            return
        inputContPreset = self._inputCont.getValueDict(omitDef=False)
        preset = self._userPresetsDict.get(self._sysName, dict())
        preset[newName] = inputContPreset
        self._userPresetsDict[self._sysName] = preset
        self._updateNames()

    def _doRename(self):
        """Rename an item
        """
        dialogBox = RenameDialog(master=self, currNameList=self._getUserPresetNames())
        oldNewNames = dialogBox.result
        if not oldNewNames:
            return
        oldName, newName = oldNewNames
        preset = self._userPresetsDict.get(self._sysName, dict())
        inputContPreset = preset[oldName]
        del preset[oldName]
        preset[newName] = inputContPreset
        self._userPresetsDict[self._sysName] = preset
        self._updateNames()

    def _doDelete(self):
        """Delete an item
        """
        dialogBox = DeleteDialog(master=self, currNameList=self._getUserPresetNames())
        nameToDelete = dialogBox.result
        if not nameToDelete:
            return
        preset = self._userPresetsDict.get(self._sysName, dict())
        del preset[nameToDelete]
        self._userPresetsDict[self._sysName] = preset
        self._updateNames()


class SaveDialog(InputDialog.ModalDialogBase):
    """Dialog box to save the current preset; result is name for saved preset
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Save")

    def body(self, master):
        Label.StrLabel(master=master, text="Save This Preset As:").grid(row=0, column=0, columnspan=5)
        # Tkinter.Label(master, text="Name:").grid(row=1, column=0)
        self.nameEntry = Entry.StrEntry(master)
        self.currNameWdg = OptionMenu.OptionMenu(
            master = master,
            items = self._currNameList,
            label = "",
            callFunc = self._doOptionMenu,
        )

        self.nameEntry.grid(row=1, column=1)
        self.currNameWdg.grid(row=1, column=2)
        return self.nameEntry # return the item that gets initial focus

    def setResult(self):
        self.result = self.nameEntry.get()

    def _doOptionMenu(self, wdg=None):
        name = self.currNameWdg.getString()
        if name:
            self.nameEntry.set(name)


class RenameDialog(InputDialog.ModalDialogBase):
    """Dialog box to rename a preset; result is a tuple: (old name, new name) or None

    Returns None if oldName == newName or one of them is empty
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Save")

    def body(self, master):
        Label.StrLabel(master=master, text="Rename Preset:").grid(row=0, column=0, columnspan=5)
        # Tkinter.Label(master, text="Name:").grid(row=1, column=0)
        self.oldNameWdg = OptionMenu.OptionMenu(
            master = master,
            items = self._currNameList,
        )
        self.newNameWdg = Entry.StrEntry(master)

        self.oldNameWdg.grid(row=1, column=1)
        self.newNameWdg.grid(row=1, column=2)
        return self.newNameWdg # return the item that gets initial focus

    def setResult(self):
        oldName = self.oldNameWdg.getString()
        newName = self.newNameWdg.get()
        if oldName and newName and oldName != newName:
            result = (oldName, newName)
        else:
            result = None
        self.result = result


class DeleteDialog(InputDialog.ModalDialogBase):
    """Dialog box to delete one named preset; result is name to delete
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Delete")

    def body(self, master):
        Label.StrLabel(master=master, text="Delete Preseturation:").grid(row=0, column=0, columnspan=5)
        self.currNameWdg = OptionMenu.OptionMenu(
            master = master,
            items = self._currNameList,
        )

        self.currNameWdg.grid(row=1, column=1)

    def setResult(self):
        self.result = self.currNameWdg.getString()


class RestoreDefaultsDialog(InputDialog.ModalDialogBase):
    """Dialog box to confirm restoring defaults; result is True if restore wanted
    """
    def body(self, master):
        Label.StrLabel(master=master, text="Restore Default Presets?").grid(row=0, column=0)

    def setResult(self):
        self.result = True


if __name__ == '__main__':
    from RO.Alg import SavedDict
    import RO.InputCont
    import Gridder
    import InputContFrame

    root = Tkinter.Tk()
    root.geometry("200x200")
    userPresetsDict = SavedDict("testPreset.json")

    class TestFrame(InputContFrame.InputContFrame):
        def __init__(self, master):
            InputContFrame.InputContFrame.__init__(self, master, stateTracker=None)

            gr = Gridder.Gridder(master=self)

            self.wdg1 = Entry.StrEntry(self)
            gr.gridWdg("Widget 1", self.wdg1)
            
            self.wdg2 = Entry.StrEntry(self)
            gr.gridWdg("Widget 2", self.wdg2)

            stdPresets = dict(
                default1 = {
                    "Widget 1": "value 1",
                    "Widget 2": 1.1,
                },
                default2 = {
                    "Widget 1": "value 2",
                    "Widget 2": 2.2,
                },
            )

            self._inputCont = RO.InputCont.ContList (
                conts = [
                    RO.InputCont.WdgCont (
                        name = 'Widget 1',
                        wdgs = self.wdg1,
                    ),
                    RO.InputCont.WdgCont (
                        name = 'Widget 2',
                        wdgs = self.wdg2,
                    ),
                ],
            )

            self.configWdg = InputContPresetsWdg(
                master = self,
                sysName = "test",
                userPresetsDict = userPresetsDict,
                stdPresets = stdPresets,
                inputCont = self._inputCont,
                text = "Presets",
            )
            gr.gridWdg("Presets", self.configWdg)

            gr.allGridded()

    testFrame = TestFrame(master=root)
    testFrame.grid(row=0, column=0)

    root.mainloop()
