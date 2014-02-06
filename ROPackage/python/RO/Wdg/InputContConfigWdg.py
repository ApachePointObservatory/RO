#!/usr/bin/env python
"""Widget to manage named configurations of an input container list

History:
2014-02-03 ROwen
"""
import functools
import Tkinter
import Entry
import Label
import InputDialog
import OptionMenu

class InputContConfigWdg(Tkinter.Menubutton):
    """Widget to manage named configurations of an input container list

    Manages a list of named configs, with two categories:
    - user configs, which can be modified
    - default configs, which cannot be modified
    """
    def __init__(self, master, sysName, userConfigsDict, inputCont, defaultConfigs=None, **kwargs):
        """Construct a ConfigWdg

        Inputs:
        - master: master widget
        - sysName: name of this system in userConfigsDict
        - userConfigsDict: a dict of user-specified configs for various systems;
            only userConfigsDict[sysName] applies to this system (ConfigWdg).
            The format of userConfigsDict[sysName] is the same as the format of defaultConfigs.
        - defaultConfigs: default configs for this system. A dict whose entries are:
            config name: config as a dict of values in the form required by inputCont.setValueDict()
        - inputCont: input container list being configured (an RO.InputCont.ContList)
        """
        self._sysName = sysName
        self._userConfigsDict = userConfigsDict
        self._defaultConfigs = defaultConfigs or dict()
        self._inputCont = inputCont

        wdgKArgs = {
            "borderwidth": 2,
            "indicatoron": True,
            "relief": "raised",
            "anchor": "c",
            "highlightthickness": 2,
        }
        wdgKArgs.update(kwargs)
        Tkinter.Menubutton.__init__(self, master, **wdgKArgs)

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

    def _updateNames(self):
        """Update names in option menu
        """
        self._menu.delete(self._begNameIndex, "end")
        userConfigNames = self._getUserConfigNames()
        for configName in userConfigNames:
            self._menu.add_command(
                label = configName,
                command = functools.partial(self._applyUserConfig, configName),
            )

        defaultConfigsNames = self._getDefaultConfigNames()
        if bool(userConfigNames) and bool(defaultConfigsNames):
            self._menu.add_separator()
        for configName in defaultConfigsNames:
            self._menu.add_command(
                label = configName,
                command = functools.partial(self._applyDefaultConfig, configName),
            )

    def _getDefaultConfigNames(self):
        """Get a sorted list of default configuration names
        """
        return sorted(self._defaultConfigs.iterkeys())

    def _getUserConfigNames(self):
        """Get a sorted list of current configuration names
        """
        config = self._userConfigsDict.get(self._sysName, dict())
        return sorted(config.iterkeys())

    def _applyUserConfig(self, configName):
        """User selected a config; apply it
        """
        config = self._userConfigsDict[self._sysName]
        inputContConfig = config[configName]
        self._inputCont.setValueDict(inputContConfig)

    def _applyDefaultConfig(self, configName):
        inputContConfig = self._defaultConfigs[configName]
        self._inputCont.setValueDict(inputContConfig)

    def _doSave(self):
        """Save current configuration
        """
        dialogBox = SaveDialog(master=self, currNameList=self._getUserConfigNames())
        newName = dialogBox.result
        if not newName:
            return
        inputContConfig = self._inputCont.getValueDict()
        config = self._userConfigsDict.get(self._sysName, dict())
        config[newName] = inputContConfig
        self._userConfigsDict[self._sysName] = config
        self._updateNames()

    def _doRename(self):
        """Rename an item
        """
        dialogBox = RenameDialog(master=self, currNameList=self._getUserConfigNames())
        oldNewNames = dialogBox.result
        if not oldNewNames:
            return
        oldName, newName = oldNewNames
        config = self._userConfigsDict.get(self._sysName, dict())
        inputContConfig = config[oldName]
        del config[oldName]
        config[newName] = inputContConfig
        self._userConfigsDict[self._sysName] = config
        self._updateNames()

    def _doDelete(self):
        """Delete an item
        """
        dialogBox = DeleteDialog(master=self, currNameList=self._getUserConfigNames())
        nameToDelete = dialogBox.result
        if not nameToDelete:
            return
        config = self._userConfigsDict.get(self._sysName, dict())
        del config[nameToDelete]
        self._userConfigsDict[self._sysName] = config
        self._updateNames()


class SaveDialog(InputDialog.ModalDialogBase):
    """Dialog box to save the current configuration; result is name for saved config
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Save")

    def body(self, master):
        Label.StrLabel(master=master, text="Save This Config As:").grid(row=0, column=0, columnspan=5)
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
    """Dialog box to rename a configuration; result is a tuple: (old name, new name) or None

    Returns None if oldName == newName or one of them is empty
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Save")

    def body(self, master):
        Label.StrLabel(master=master, text="Rename Config:").grid(row=0, column=0, columnspan=5)
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
    """Dialog box to delete one named config; result is name to delete
    """
    def __init__(self, master, currNameList):
        self._currNameList = currNameList
        InputDialog.ModalDialogBase.__init__(self, master=master, title="Delete")

    def body(self, master):
        Label.StrLabel(master=master, text="Delete Configuration:").grid(row=0, column=0, columnspan=5)
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
        Label.StrLabel(master=master, text="Restore Default Configs?").grid(row=0, column=0)

    def setResult(self):
        self.result = True


if __name__ == '__main__':
    from RO.Alg import SavedDict
    import RO.InputCont
    import Gridder
    import InputContFrame

    root = Tkinter.Tk()
    root.geometry("200x200")
    userConfigsDict = SavedDict("testConfig.json")

    class TestFrame(InputContFrame.InputContFrame):
        def __init__(self, master):
            InputContFrame.InputContFrame.__init__(self, master, stateTracker=None)

            gr = Gridder.Gridder(master=self)

            self.wdg1 = Entry.StrEntry(self)
            gr.gridWdg("Widget 1", self.wdg1)
            
            self.wdg2 = Entry.StrEntry(self)
            gr.gridWdg("Widget 2", self.wdg2)

            defaultConfigs = dict(
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

            self.configWdg = InputContConfigWdg(
                master = self,
                sysName = "test",
                userConfigsDict = userConfigsDict,
                defaultConfigs = defaultConfigs,
                inputCont = self._inputCont,
                text = "Configs",
            )
            gr.gridWdg("Configs", self.configWdg)

            gr.allGridded()

    testFrame = TestFrame(master=root)
    testFrame.grid(row=0, column=0)

    root.mainloop()
