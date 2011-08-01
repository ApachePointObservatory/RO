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
2011-08-01 ROwen    Added support for recursion.
                    Added arguments patterns, exclPatterns, dirPatterns, exclDirPatterns, recursionDepth and processDirs.
                    Call update_idletasks after each file is processed so messages are more likely to be logged as they arrive.
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
    def __init__(self, master, width, height, font=None, printTraceback=False,
         patterns=None, exclPatterns=None, dirPatterns=None, exclDirPatterns=None,
         recursionDepth=False, processDirs=False):
        """Construct a DropletApp
        
        Inputs:
        - master: master widget; this should almost certainly be the root window
        - width: width of log widget
        - height: height of log widget
        - font: font for log widget
        - printTraceback: print a traceback to stderr if processing a file fails?
        - patterns: one or a sequence of inclusion patterns; each file name must match at least one of these;
            if None or [] then ["*"] is used.
            Patterns are matched using fnmatch, which does unix-style matching
            (* for any char sequence, ? for one char).
        - exclPatterns: one or a sequence of exclusion patterns; each file name must not match any of these
        - dirPatterns: one or a sequence of inclusion patterns; each directory name must match at least one of these;
            if None or [] then ["*"] is used.
        - exclDirPatterns: one or a sequence of exclusion patterns; each directory name must not match any of these
        - recursionDepth: recursion level; None or an integer n:
            None means infinite recursion
            n means go down n levels from the root path, for example:
            0 means don't even look inside directories in paths
            1 means look inside directories in paths but no deeper
        - processDirs: if True then processFile is sent directories as well as files, else it receives only files.
        """
        Tkinter.Frame.__init__(self, master)
        self.printTraceback = bool(printTraceback)
        self.patterns = patterns
        self.exclPatterns = exclPatterns
        self.dirPatterns = dirPatterns
        self.exclDirPatterns = exclDirPatterns
        self.recursionDepth = recursionDepth
        self.processDirs = bool(processDirs)
        
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
        filteredPathList = RO.OS.findFiles(
            paths = filePathList,
            patterns = self.patterns,
            exclPatterns = self.exclPatterns,
            dirPatterns = self.dirPatterns,
            exclDirPatterns = self.exclDirPatterns,
            recursionDepth = self.recursionDepth,
            returnDirs = self.processDirs,
        )

        for filePath in filteredPathList:
            try:
                self.processFile(filePath)
                self.update_idletasks()
            except Exception, e:
                self.logWdg.addOutput("%s failed: %s\n" % (filePath, e), severity=RO.Constants.sevError)
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
