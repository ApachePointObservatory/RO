#!/usr/bin/env python
"""Run an application as a droplet (an application onto which you drop file) with a log window.

To build a Mac droplet using py2app, in the PList specify the sorts of files that can be dropped, e.g.:

    plist = dict(
    ...
        CFBundleDocumentTypes       = [
            dict(
                CFBundleTypeName = "TEXT",
                LSItemContentTypes = [
                    "public.plain-text",
                    "public.text",
                    "public.data",
                ],
                CFBundleTypeRole = "Viewer",
            ),
        ],
    )

    Notes:
    - There are keywords that allow you to specify allowed file suffixes
      but they are deprecated in Mac OS X 10.5 so I don't show them:
    - CFBundleTypeRole is required; another common value is "Editor".

History:
2011-02-25 ROwen
"""
import os.path
import sys
import traceback
import Tkinter
import RO.OS
import RO.Constants
import LogWdg

__all__ = ["DropletApp"]

class DropletApp(Tkinter.Frame):
    """Run an application as a droplet (an application onto which you drop files)
    
    You must subclass this class and override processFile.
    
    Your typical code will look like the example at the end.
    """
    def __init__(self, master, width, height, font=None, printTraceback=False):
        """Construct a DropletApp
        
        Inputs:
        - master: master widget; this should almost certainly be the root window
        - width: width of log widget
        - height: height of log widget
        - font: font for log widget
        - printTraceback: print a traceback to stderr if processing a file fails?
        """
        Tkinter.Frame.__init__(self, master)
        self.printTraceback = bool(printTraceback)
        
        self.logWdg = RO.Wdg.LogWdg(
            master = self,
            width = width,
            height = height,
        )
        self.logWdg.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        if font:
            self.logWdg.text["font"] = font

        if RO.OS.PlatformName == "mac":
            self.tk.createcommand('::tk::mac::OpenDocument', self._macOpenDocument)
    
    def processFile(self, filePath):
        """Override this method.
        """
        raise RuntimeError("Subclass must override")
    
    def processFileList(self, filePathList):
        """Process a list of files
        
        Includes basic error handling: if an error is raised,
        prints a message to the log window and goes on to the next file.
        """
        for filePath in filePathList:
            try:
                fileName = os.path.basename(filePath)
                self.processFile(filePath)
            except Exception, e:
                self.logWdg.addOutput("%s failed: %s\n" % (fileName, e), severity=RO.Constants.sevError)
                if self.printTraceback:
                    traceback.print_exc(file=sys.stderr)

    def _macOpenDocument(self, *filePathList):
        """Handle Mac OpenDocument event
        """
        self.processFileList(filePathList)


if __name__ == "__main__":
    filePathList = sys.argv[1:]
    # strip first argument if it starts with "-", as happens when run as a Mac application
    if filePathList and filePathList[0].startswith("-"):
        filePathList = filePathList[1:]

    root = Tkinter.Tk()
    
    class TestApp(DropletApp):
        def __init__(self, master):
            DropletApp.__init__(self, master=master, width=135, height=20)
            
            self.logWdg.addOutput("Test Droplet\n")

    
        def processFile(self, filePath):
            self.logWdg.addOutput("Processing %s\n" % (filePath))
    
    app = TestApp(root)
    app.pack(side="left", expand=True, fill="both")

    root.mainloop()
