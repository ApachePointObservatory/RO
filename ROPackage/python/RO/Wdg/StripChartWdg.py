#!/usr/bin/env python
"""A widget to changing values in real time as a strip chart

Known issues:
Matplotlib's defaults present a number of challenges for making a nice strip chart display.
Here are manual workarounds for some common problems:

- Jumping Ticks:
    By default the major time ticks and grid jump to new values as time advances. I haven't found an
    automatic way to keep them steady, but you can do it manually by following these examples:
    # show a major tick every 10 seconds on even 10 seconds
    stripChart.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0, 60, 10)))
    # show a major tick every 5 seconds on even 5 minutes
    stripChart.xaxis.set_major_locator(matplotlib.dates.MinuteLocator(byminute=range(0, 60, 5)))

- Reducing The Spacing Between Subplots:
    Adjacent subplots are rather widely spaced. You can manually shrink the spacing but then
    the major Y labels will overlap. Here is a technique that includes "pruning" the top major tick label
    from each subplot and then shrinking the subplot horizontal spacing:
        for subplot in stripChartWdg.subplotArr:
            subplot.yaxis.get_major_locator().set_params(prune = "upper")
        stripChartWdg.figure.subplots_adjust(hspace=0.1)
- Truncated X Axis Labels:
    The x label is truncated if the window is short, due to poor auto-layout on matplotlib's part.
    Also the top and sides may have too large a margin. Tony S Yu provided code that should solve the
    issue automatically, but I have not yet incorporated it. You can try the following manual tweak:
    (values are fraction of total window height or width, so they must be in the range 0-1):
      stripChartWdg.figure.subplots_adjust(bottom=0.15) # top=..., left=..., right=...
    Unfortunately, values that look good at one window size may not be suitable at another.

- Undesirable colors and font sizes:
    If you are unhappy with the default choices of font size and background color
    you can edit the .matplotlibrc file or make settings programmatically.
    Some useful programmatic settings:

    # by default the background color of the outside of the plot is gray; set using figure.facecolor:
    matplotlib.rc("figure", facecolor="white") 
    # by default legends have large text; set using legend.fontsize:
    matplotlib.rc("legend", fontsize="medium") 

Requirements:
- Requires matplotlib built with TkAgg support
- This widget is somewhat experimental and the API may change.

Acknowledgements:
I am grateful to Benjamin Root, Tony S Yu and others on matplotlib-users
for advice on tying the x axes together and improving the layout.

History:
2010-09-29  ROwen
2010-11-30  Fixed a memory leak (Line.purgeOldData wasn't working correctly).
"""
import bisect
import datetime
import time
import numpy
import Tkinter
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

__all__ = ["StripChartWdg"]

class StripChartWdg(Tkinter.Frame):
    """A widget to changing values in real time as a strip chart
    
    Usage Hints:
    - For each variable quantity to display:
      - Call addLine once to specify the quantity
      - Call addPoint for each new data point you wish to display

    - For each constant line (e.g. limit) to display call addConstantLine
    
    - To make sure a plot includes one or two y values (e.g. 0 or a range of values) call showY

    - To manually scale a Y axis call setYLimits (by default all y axes are autoscaled).
    
    - All supplied times are POSIX timestamps (e.g. as supplied by time.time()).
        You may choose the kind of time displayed on the time axis (e.g. UTC or local time) using cnvTimeFunc
        and the format of that time using dateFormat.
    
    Known Issues:
    matplotlib's defaults present a number of challenges for making a nice strip chart display.
    Some issues and manual solutions are discussed in the main file's document string.
        
    Potentially Useful Attributes:
    - canvas: the matplotlib FigureCanvas
    - figure: the matplotlib Figure
    - subplotArr: list of subplots, from top to bottom; each is a matplotlib Subplot object,
        which is basically an Axes object but specialized to live in a rectangular grid
    - xaxis: the x axis shared by all subplots
    """
    def __init__(self,
        master,
        timeRange = 3600,
        numSubplots = 1,
        width = 8,
        height = 2,
        showGrid = True,
        dateFormat = "%H:%M:%S",
        updateInterval = None,
        cnvTimeFunc = None,
    ):
        """Construct a StripChartWdg with the specified time range
        
        Inputs:
        - master: Tk parent widget
        - timeRange: range of time displayed (seconds)
        - width: width of graph in inches
        - height: height of graph in inches
        - numSubplots: the number of subplots
        - showGrid: if True a grid is shown
        - dateFormat: format for major axis labels, using time.strftime format
        - updateInterval: now often the time axis is updated (seconds); if None a value is calculated
        - cnvTimeFunc: a function that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days;
            typically an instance of TimeConverter; defaults to TimeConverter(useUTC=False)
        """
        Tkinter.Frame.__init__(self, master)
        
        self._timeRange = timeRange
        if updateInterval == None:
            updateInterval = max(0.1, min(5.0, timeRange / 2000.0))
        self.updateInterval = float(updateInterval)

        if cnvTimeFunc == None:
            cnvTimeFunc = TimeConverter(useUTC=False)
        self._cnvTimeFunc = cnvTimeFunc

        # how many time axis updates occur before purging old data
        self._maxPurgeCounter = max(1, int(0.5 + (5.0 / self.updateInterval)))
        self._purgeCounter = 0

        self.figure = matplotlib.figure.Figure(figsize=(width, height), frameon=True)
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="news")
        self.canvas.mpl_connect('draw_event', self._handleDrawEvent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        bottomSubplot = self.figure.add_subplot(numSubplots, 1, numSubplots)
        self.subplotArr = [self.figure.add_subplot(numSubplots, 1, n+1, sharex=bottomSubplot) \
            for n in range(numSubplots-1)] + [bottomSubplot]
        if showGrid:
            for subplot in self.subplotArr:
                subplot.grid(True)

        self.xaxis = bottomSubplot.xaxis
        bottomSubplot.xaxis_date()
        self.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(dateFormat))

        # dictionary of line name: _Line object
        self._lineDict = dict()
        # dictionary of constant line name: matplotlib Line2D
        self._constLine2DDict = dict()
        # dictionary of matplotlib Subplot: _SubplotInfo
        self._subplotInfoDict = dict()

        for subplot in self.subplotArr:
            subplot.label_outer() # disable axis labels on all but the bottom subplot
            subplot.set_ylim(auto=True) # set auto scaling for the y axis
            self._subplotInfoDict[subplot] = _SubplotInfo()
        
        self._timeAxisTimer = None
        self._updateTimeAxis()

    def addConstantLine(self, name, y, subplotInd=0, doLabel=False, **kargs):
        """Add a new constant to plot
        
        Inputs:
        - name: name for constant line
        - y: value of constant line
        - doLabel: if True then the Line's label is set to name.
            Set True if you want the line to show up in the legend using name.
            Set False if you want no label (the line will not show in the legend)
            or if you prefer to specify a legend that is different than name
        - subplotInd: index of subplot
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        if name in self._constLine2DDict:
            raise RuntimeError("Constant Line %s already exists" % (name,))
        subplot = self.subplotArr[subplotInd]
        if doLabel:
            kargs["label"] = name
        self._constLine2DDict[name] = subplot.axhline(y, **kargs)
        yMin, yMax = subplot.get_ylim()
        if subplot.get_autoscaley_on() and numpy.isfinite(y) and not (yMin <= y <= yMax):
            subplot.relim()
            subplot.autoscale_view(scalex=False, scaley=True)

    def addLine(self, name, subplotInd=0, doLabel=True, **kargs):
        """Add a new quantity to plot
        
        Inputs:
        - name: name for line
        - subplotInd: index of subplot
        - doLabel: if True then the Line's label is set to name.
            Set True if you want the line to show up in the legend using name.
            Set False if you want no label (the line will not show in the legend)
            or if you prefer to specify a legend that is different than name
        all other keyword arguments are sent to the _Line constructor
        """
        if name in self._lineDict:
            raise RuntimeError("Line %s already exists" % (name,))
        subplot = self.subplotArr[subplotInd]
        if doLabel:
            kargs["label"] = name
        line = _Line(subplot, **kargs)
        self._lineDict[name] = line

        self._subplotInfoDict[subplot].animatedLineList.append(line)

    def addPoint(self, name, y, t=None):
        """Add a data point to a specified line
        
        Inputs:
        - name: name of Line
        - y: y value
        - t: time as a POSIX timestamp (e.g. time.time()); if None then "now"
        """
        if t == None:
            t = time.time()
        mplDays = self._cnvTimeFunc(t)
        line = self._lineDict[name]

        didRescale = line.addPoint(y, mplDays)

        if not didRescale:
            # did not rescale, so no draw event triggered, so update just this subplot's display
            subplotInfo = self._subplotInfoDict[line.subplot]
            if subplotInfo.background:
                self.canvas.restore_region(subplotInfo.background)
                for line in subplotInfo.animatedLineList:
                    line.subplot.draw_artist(line.line)
                self.canvas.blit(line.subplot.bbox)

    def getDoAutoscale(self, subplotInd=0):
        return self.subplotArr[subplotInd].get_autoscaley_on()

    def setDoAutoscale(self, doAutoscale, subplotInd=0):
        """Turn autoscaling on or off for the specified subplot
        
        You can also turn off autoscaling by calling setYLimits.
        """
        doAutoscale = bool(doAutoscale)
        subplot = self.subplotArr[subplotInd]
        subplot.set_ylim(auto=doAutoscale)
        if doAutoscale:
            subplot.relim()
            subplot.autoscale_view(scalex=False, scaley=True)
    
    def setYLimits(self, minY, maxY, subplotInd=0):
        """Set y limits for the specified subplot and disable autoscaling.
        
        Note: if you want to autoscale with a minimum range, use showY.
        """
        self.subplotArr[subplotInd].set_ylim(minY, maxY, auto=False)
    
    def showY(self, y0, y1=None, subplotInd=0):
        """Specify one or two values to always show in the y range.
        
        Inputs:
        - subplotInd: index of subplot
        - y0: first y value to show
        - y1: second y value to show; None to omit

        Warning: setYLimits overrides this method (but the values are remembered in case you turn
        autoscaling back on).
        """
        subplot = self.subplotArr[subplotInd]
        yMin, yMax = subplot.get_ylim()
        
        if y1 != None:
            yList = [y0, y1]
        else:
            yList = [y0]
        doRescale = False
        for y in yList:
            subplot.axhline(y, linestyle=" ")
            if subplot.get_autoscaley_on() and numpy.isfinite(y) and not (yMin <= y <= yMax):
                doRescale = True
        if doRescale:
            subplot.relim()
            subplot.autoscale_view(scalex=False, scaley=True)

    def _handleDrawEvent(self, event):
        """Handle draw event
        """
        for subplot, subplotInfo in self._subplotInfoDict.iteritems():
            subplotInfo.background = self.canvas.copy_from_bbox(subplot.bbox)
            for line in subplotInfo.animatedLineList:
                subplot.draw_artist(line.line)
            self.canvas.blit(subplot.bbox)
    
    def _updateTimeAxis(self):
        """Update the time axis; calls itself
        """
        if self._timeAxisTimer != None:
            self.after_cancel(self._timeAxisTimer)
            self._timeAxisTimer = None
        tMax = time.time() + self.updateInterval
        tMin = tMax - self._timeRange
        minMplDays = self._cnvTimeFunc(tMin)
        maxMplDays = self._cnvTimeFunc(tMax)
        
        self._purgeCounter = (self._purgeCounter + 1) % self._maxPurgeCounter
        doPurge = self._purgeCounter == 0
        if doPurge:
            for line in self._lineDict.itervalues():
                line.purgeOldData(minMplDays)
        
        for subplot in self.subplotArr:
            subplot.set_xlim(minMplDays, maxMplDays)
            if subplot.get_autoscaley_on() and doPurge:
                # since data is being purged the y limits may have changed
                subplot.relim()
                subplot.autoscale_view(scalex=False, scaley=True)
        self.canvas.draw()
        self._timeAxisTimer = self.after(int(self.updateInterval * 1000), self._updateTimeAxis)

class _SubplotInfo(object):
    """Information needed to animate a Subplot
    """
    def __init__(self):
        self.background = None
        self.animatedLineList = []

class _Line(object):
    """A line (trace) on a strip chart representing some varying quantity
    
    Attributes that might be useful:
    - line: the matplotlib.lines.Line2D associated with this line
    - subplot: the matplotlib Subplot instance displaying this line
    - subplotInd: the index of the subplot
    """
    def __init__(self, subplot, **kargs):
        """Create a line
        
        Inputs:
        - subplot: the matplotlib Subplot instance displaying this line
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self.subplot = subplot
        # do not use the data in the Line2D because in some versions of matplotlib
        # line.get_data returns numpy arrays, whihc cannot be appended to
        self._tList = []
        self._yList = []
        self.line = matplotlib.lines.Line2D([], [], animated=True, **kargs)
        self.subplot.add_line(self.line)
        
    def addPoint(self, y, mplDays):
        """Append a new data point
        
        Inputs:
        - y: y value
        - mplDays: time as matplotlib days
        
        Return:
        - True if view should be relimited, False otherwise
        """
        self._tList.append(mplDays)
        self._yList.append(y)
        if self.subplot.get_autoscaley_on() and numpy.isfinite(y):
            yMin, yMax = self.subplot.get_ylim()
            self.line.set_data(self._tList, self._yList)
            if not (yMin <= y <= yMax):
                self.subplot.relim()
                self.subplot.autoscale_view(scalex=False, scaley=True)
                return True
        else:
            self.line.set_data(self._tList, self._yList)
        return False

    def purgeOldData(self, minMplDays):
        """Purge data with t < minMplDays

        Inputs:
        - minMplDays: time before which to delete data (matpotlib days)
        
        Warning: does not update the display (the caller must do that)
        """
        if not self._tList:
            return
        numToDitch = bisect.bisect_left(self._tList, minMplDays) - 1 # -1 avoids a gap at the left
        if numToDitch > 0:
            self._tList = self._tList[numToDitch:]
            self._yList = self._yList[numToDitch:]
            self.line.set_data(self._tList, self._yList)


class TimeConverter(object):
    """A functor that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days
    """
    _DaysPerSecond = 1.0 / (24.0 * 60.0 * 60.0)
    def __init__(self, useUTC, offset=0.0):
        """Create a TimeConverter
        
        Inputs:
        - useUTC: use UTC instead of the local time zone?
        - offset: time offset: returned time - supplied time (sec)
        """
        self._offset = float(offset)

        unixSec = time.time()
        if useUTC:
            d = datetime.datetime.utcfromtimestamp(unixSec)
        else:
            d = datetime.datetime.fromtimestamp(unixSec)
        matplotlibDays = matplotlib.dates.date2num(d)
        self.mplSecMinusUnixSec = (matplotlibDays / self._DaysPerSecond) - unixSec
            
    def __call__(self, unixSec):
        """Given a a POSIX timestamp (e.g. from time.time()) return matplotlib days
        """
        return (unixSec + self._offset + self.mplSecMinusUnixSec) * self._DaysPerSecond


if __name__ == "__main__":   
    import RO.Alg
    root = Tkinter.Tk()
    stripChart = StripChartWdg(
        master = root,
        timeRange = 60,
        numSubplots = 2,
#        updateInterval = 5,
        width = 9,
        height = 3,
    )
    stripChart.pack(expand=True, fill="both")
    stripChart.addLine("Counts", subplotInd=0, color="blue")
    stripChart.addConstantLine("Saturated", 2.5, subplotInd=0, color="red", doLabel=True)
    stripChart.subplotArr[0].yaxis.set_label_text("Counts")
    # make sure the Y axis of subplot 0 always includes 0 and 2.7
    stripChart.showY(0.0, 2.8, subplotInd=0)

    stripChart.addLine("Walk 1", subplotInd=1, color="blue")
    stripChart.addLine("Walk 2", subplotInd=1, color="green")
    stripChart.subplotArr[1].yaxis.set_label_text("Random Walk")
    stripChart.showY(0.0, subplotInd=0)
    stripChart.subplotArr[1].legend(loc=3)

    # stop major time ticks from jumping around as time advances:
    stripChart.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,60,10)))
    
    varDict = {
        "Counts": RO.Alg.ConstrainedGaussianRandomWalk(1, 0.2, 0, 2.8),
        "Walk 1":  RO.Alg.RandomWalk.GaussianRandomWalk(0, 2),
        "Walk 2": RO.Alg.RandomWalk.GaussianRandomWalk(0, 2),
    }
    def addRandomValues(name, interval=100):
        var = varDict[name]
        stripChart.addPoint(name, var.next())
        root.after(interval, addRandomValues, name, interval)

    addRandomValues("Counts", interval=500)
    addRandomValues("Walk 1", 1600)
    addRandomValues("Walk 2", 1900)
    root.mainloop()
