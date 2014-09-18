#!/usr/bin/env python
from __future__ import division, print_function
"""Run a script as a droplet (an application onto which you drop file) with a log window

Deprecated. use DropletApp instead.

To build a Mac droplet using py2app, assuming the code that does the work is in mainScript.py:

- Write a trivial script that constructs/runs DropletRunner; this is the script
  that you tell setup.py about; it might be called runMainScript.py:
    import RO.Wdg.DropletRunner
    import mainScript # so py2app finds it and its dependencies
    RO.Wdg.DropletRunner.DropletRunner("mainScript.py")

- In the application PList specify the sorts of files that can be dropped, e.g.:

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

- Copy the main droplet script into the the application bundle Contents/Resources
  so DropletRunner can find it, e.g.:
    import mainScriptModule
    shutil.copy(
        "mainScript.py",
        os.path.join("dist", appName, "Contents", "Resources"),
    )

History:
2010-06-16 ROwen
2010-06-17 ROwen    Added title and initialText arguments to constructor.
2010-06-24 ROwen    Bug fix: use sys.executable to run the droplet script, thus giving the droplet script
                    access to the bundled application's python and python libraries.
2010-06-28 ROwen    Tweaked _readStdOut and _readStdErr to make it clearer they ignore their arguments.
2010-07-12 ROwen    Bug fix: DropletRunner() was an old-style class which is not compatible with some
                    versions of Python; made it a new-style class (as originally intended).
2011-02-25 ROwen    Tweaked usage documentation.
2011-08-16 ROwen    Commented out two diagnostic print statements.
2011-10-11 ROwen    Documented as deprecated.
2012-07-09 ROwen    Modified to use RO.TkUtil.Timer.
"""
__all__ = ["DropletRunner"]

import sys
import os.path
import subprocess
import Tkinter
import RO.OS
import RO.Constants
from RO.TkUtil import Timer
import LogWdg

class DropletRunner(object):
    """Run a script as a droplet (an application onto which you drop file) with a log window.
    
    Data the script writes to sys.stdout and sys.stderr is written to a log window;
    stderr output is shown in red.    

    On Mac OS X additional files may be dropped on the application icon once the first batch is processed.
    I don't know how to support this on other platforms.
    """
    def __init__(self, scriptPath, title=None, initialText=None, **keyArgs):
        """Construct and run a DropletRunner
        
        Inputs:
        - scriptPath: path to script to run when files are dropped on the application
        - title: title for log window; if None then generated from scriptPath
        - initialText: initial text to display in log window
        **keyArgs: all other keyword arguments are sent to the RO.Wdg.LogWdg constructor
        """
        self.isRunning = False
        self.scriptPath = os.path.abspath(scriptPath)
        if not os.path.isfile(scriptPath):
            raise RuntimeError("Cannot find script %r" % (self.scriptPath,))

        self.tkRoot = Tkinter.Tk()
        self._timer = Timer()
        
        if title == None:
            title = os.path.splitext(os.path.basename(scriptPath))[0]
        self.tkRoot.title(title)

        if RO.OS.PlatformName == "mac":
            self.tkRoot.createcommand('::tk::mac::OpenDocument', self._macOpenDocument)
            # the second argument is a process ID (approximately) if run as an Applet;
            # the conditional handles operation from the command line
            if len(sys.argv) > 1 and sys.argv[1].startswith("-"):
                filePathList = sys.argv[2:]
            else:
                filePathList = sys.argv[1:]
        else:
            filePathList = sys.argv[1:]

        self.logWdg = LogWdg.LogWdg(self.tkRoot, **keyArgs)
        self.logWdg.grid(row=0, column=0, sticky="nsew")
        self.tkRoot.grid_rowconfigure(0, weight=1)
        self.tkRoot.grid_columnconfigure(0, weight=1)
        
        if initialText:
            self.logWdg.addOutput(initialText)

        if filePathList:
            self.runFiles(filePathList)

        self.tkRoot.mainloop()

    def runFiles(self, filePathList):
        """Run the script with the specified files
        """
#        print "runFiles(filePathList=%s)" % (filePathList,)
        self.isRunning = True
        argList = [sys.executable, self.scriptPath] + list(filePathList)
        self.subProc = subprocess.Popen(argList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.tkRoot.tk.createfilehandler(self.subProc.stderr, Tkinter.READABLE, self._readStdErr)
        self.tkRoot.tk.createfilehandler(self.subProc.stdout, Tkinter.READABLE, self._readStdOut)
        self._poll()

    def _macOpenDocument(self, *filePathList):
        """Handle Mac OpenDocument event
        """
        self.runFiles(filePathList)

    def _poll(self):
        """Poll for subprocess completion
        """
        if self.subProc.returncode != None:
            self._cleanup()
        else:
            self._timer(0.1, self._poll)
    
    def _readStdOut(self, *dumArgs):
        """Read and log data from script's stdout
        """
        self.logWdg.addOutput(self.subProc.stdout.read())
        if self.subProc.poll() != None:
            self._cleanup()

    def _readStdErr(self, *dumArgs):
        """Read and log data from script's stderr
        """
        self.logWdg.addOutput(self.subProc.stderr.read(), severity=RO.Constants.sevError)
        if self.subProc.poll() != None:
            self._cleanup()

    def _cleanup(self):
        """Close Tk file handlers and print any final data from the subprocess
        """
        self._timer.cancel()
        if self.isRunning:
            self.isRunning = False
            self.tkRoot.tk.deletefilehandler(self.subProc.stdout)
            self.tkRoot.tk.deletefilehandler(self.subProc.stderr)
            outData, errData = self.subProc.communicate()
            if outData:
                self.logWdg.addOutput(outData)
            if errData:
                self.logWdg.addOutput(errData, severity=RO.Constants.sevError)


if __name__ == "__main__":
    DropletRunner("sampleDroplet.py")
