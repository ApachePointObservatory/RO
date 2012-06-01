#!/usr/bin/env python
"""A widget to display changing values in real time as a strip chart

Known issues:
Matplotlib's defaults present a number of challenges for making a nice strip chart display.
Here are manual workarounds for some common problems:

- Memory Leak:
    Matplotlib 1.0.0 has a memory leak in canvas.draw(), at least when using TgAgg:
    <https://sourceforge.net/tracker/?func=detail&atid=560720&aid=3124990&group_id=80706>
    Unfortunately canvas.draw is only way to update the display after altering the x/time axis.
    Thus every StripChartWdg will leak memory until the matplotlib bug is fixed;
    the best you can do is reduce the leak rate by increasing updateInterval.

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

Acknowledgements:
I am grateful to Benjamin Root, Tony S Yu and others on matplotlib-users
for advice on tying the x axes together and improving the layout.

History:
2010-09-29  ROwen
2010-11-30  Fixed a memory leak (Line._purgeOldData wasn't working correctly).
2010-12-10  Document a memory leak caused by matplotlib's canvas.draw.
2010-12-23  Backward-incompatible changes:
            - addPoint is now called on the object returned by addLine, not StripChartWdg.
                This eliminate the need to give lines unique names.
            - addPoint is silently ignored if y is None
            - addLine and addConstantLine have changed:
                - There is no "name" argument; use label if you want a name that shows up in legends.
                - The label does not have to be unique.
                - They return an object.
            Added removeLine method.
2010-12-29  Document useful arguments for addLine.
2012-05-31  Add a clear method to StripChartWdg and _Line.
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
#         print "updateInterval=", self.updateInterval

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

        # dictionary of constant line name: (matplotlib Line2D, matplotlib Subplot)
        self._constLineDict = dict()

        for subplot in self.subplotArr:
            subplot._scwLines = [] # a list of contained _Line objects;
                # different than the standard lines property in that:
                # - lines contains Line2D objects
                # - lines contains constant lines as well as data lines
            subplot._scwBackground = None # background for animation
            subplot.label_outer() # disable axis labels on all but the bottom subplot
            subplot.set_ylim(auto=True) # set auto scaling for the y axis
        
        self._timeAxisTimer = None
        self._updateTimeAxis()

    def addConstantLine(self, y, subplotInd=0, **kargs):
        """Add a new constant to plot
        
        Inputs:
        - y: value of constant line
        - subplotInd: index of subplot
        - All other keyword arguments are sent to the matplotlib Line2D constructor
          to control the appearance of the data. See addLine for more information.
        """
        subplot = self.subplotArr[subplotInd]
        line2d = subplot.axhline(y, **kargs)
        yMin, yMax = subplot.get_ylim()
        if subplot.get_autoscaley_on() and numpy.isfinite(y) and not (yMin <= y <= yMax):
            subplot.relim()
            subplot.autoscale_view(scalex=False, scaley=True)
        return line2d

    def addLine(self, subplotInd=0, **kargs):
        """Add a new quantity to plot
        
        Inputs:
        - subplotInd: index of subplot
        - All other keyword arguments are sent to the matplotlib Line2D constructor
          to control the appearance of the data. Useful arguments include:
          - label: name of line (displayed in a Legend)
          - color: color of line
          - linestyle: style of line (defaults to a solid line); "" for no line, "- -" for dashed, etc.
          - marker: marker shape, e.g. "+"
          Please do not attempt to control other sorts of line properties, such as its data.
          Arguments to avoid include: animated, data, xdata, ydata, zdata, figure.
        """
        subplot = self.subplotArr[subplotInd]
        return _Line(subplot, self._cnvTimeFunc, **kargs)
    
    def clear(self):
        """Clear data in all non-constant lines
        """
        for subplot in self.subplotArr:
            for line in subplot._scwLines:
                line.clear()
                subplot.draw_artist(line.line2d)
            self.canvas.blit(subplot.bbox)

    def getDoAutoscale(self, subplotInd=0):
        return self.subplotArr[subplotInd].get_autoscaley_on()
    
    def removeLine(self, line):
        """Remove an existing line added by addLine or addConstantLine
        
        Raise an exception if the line is not found
        """
        if isinstance(line, _Line):
            # a _Line object needs to be removed from _scwLines as well as the subplot
            line2d = line.line2d
            subplot = line.subplot
            subplot._scwLines.remove(line)
        else:
            # a constant line is just a matplotlib Line2D instance
            line2d = line
            subplot = line.axes

        subplot.lines.remove(line2d)
        if subplot.get_autoscaley_on():
            subplot.relim()
            subplot.autoscale_view(scalex=False, scaley=True)
        self.canvas.draw()

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
#         print "handleDrawEvent"
        for subplot in self.subplotArr:
            subplot._scwBackground = self.canvas.copy_from_bbox(subplot.bbox)
            for line in subplot._scwLines:
                subplot.draw_artist(line.line2d)
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
        
        for subplot in self.subplotArr:
            subplot.set_xlim(minMplDays, maxMplDays)
            if doPurge:
                for line in subplot._scwLines:
                    line._purgeOldData(minMplDays)
                if subplot.get_autoscaley_on():
                    # since data is being purged the y limits may have changed
                    subplot.relim()
                    subplot.autoscale_view(scalex=False, scaley=True)
        self.canvas.draw()
        self._timeAxisTimer = self.after(int(self.updateInterval * 1000), self._updateTimeAxis)


class _Line(object):
    """A line (trace) on a strip chart representing some varying quantity
    
    Attributes that might be useful:
    - line2d: the matplotlib.lines.Line2D associated with this line
    - subplot: the matplotlib Subplot instance displaying this line
    - cnvTimeFunc: a function that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days;
        typically an instance of TimeConverter; defaults to TimeConverter(useUTC=False)
    """
    def __init__(self, subplot, cnvTimeFunc, **kargs):
        """Create a line
        
        Inputs:
        - subplot: the matplotlib Subplot instance displaying this line
        - cnvTimeFunc: a function that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days;
            typically an instance of TimeConverter; defaults to TimeConverter(useUTC=False)
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self.subplot = subplot
        self._cnvTimeFunc = cnvTimeFunc
        # do not use the data in the Line2D because in some versions of matplotlib
        # line.get_data returns numpy arrays, which cannot be appended to
        self._tList = []
        self._yList = []
        self.line2d = matplotlib.lines.Line2D([], [], animated=True, **kargs)
        self.subplot.add_line(self.line2d)
        self.subplot._scwLines.append(self)
        
    def addPoint(self, y, t=None):
        """Append a new data point
        
        Inputs:
        - y: y value; if None the point is silently ignored
        - t: time as a POSIX timestamp (e.g. time.time()); if None then "now"
        """
        if y == None:
            return
        if t == None:
            t = time.time()
        mplDays = self._cnvTimeFunc(t)

        self._tList.append(mplDays)
        self._yList.append(y)
        if self.subplot.get_autoscaley_on() and numpy.isfinite(y):
            yMin, yMax = self.subplot.get_ylim()
            self.line2d.set_data(self._tList, self._yList)
            if not (yMin <= y <= yMax):
                self.subplot.relim()
                self.subplot.autoscale_view(scalex=False, scaley=True)
                return # a draw event was triggered
        else:
            self.line2d.set_data(self._tList, self._yList)

        # did not trigger redraw event so do it now
        if self.subplot._scwBackground:
            canvas = self.subplot.figure.canvas
            canvas.restore_region(self.subplot._scwBackground)
            for line in self.subplot._scwLines:
                self.subplot.draw_artist(line.line2d)
            canvas.blit(self.subplot.bbox)
    
    def clear(self):
        """Clear all data
        """
        self._tList = []
        self._yList = []
        self.line2d.set_data(self._tList, self._yList)

    def _purgeOldData(self, minMplDays):
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
            self.line2d.set_data(self._tList, self._yList)


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
#         updateInterval = 5,
        width = 9,
        height = 3,
    )
    stripChart.pack(expand=True, fill="both")
    countsLine = stripChart.addLine(label="Counts", subplotInd=0, color="blue")
    satConstLine = stripChart.addConstantLine(2.5, label="Saturated", subplotInd=0, color="red")
    stripChart.subplotArr[0].yaxis.set_label_text("Counts")
    # make sure the Y axis of subplot 0 always includes 0 and 2.7
#    stripChart.showY(0.0, 2.8, subplotInd=0)

    walk1Line = stripChart.addLine(label="Walk 1", subplotInd=1, color="blue")
    walk2Line = stripChart.addLine(label="Walk 2", subplotInd=1, color="green")
    stripChart.subplotArr[1].yaxis.set_label_text("Random Walk")
#    stripChart.showY(0.0, subplotInd=0)
    stripChart.subplotArr[1].legend(loc=3)

    # stop major time ticks from jumping around as time advances:
    stripChart.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,60,10)))
    
    varDict = {
        countsLine: RO.Alg.ConstrainedGaussianRandomWalk(1, 0.2, 0, 2.8),
        walk1Line:  RO.Alg.RandomWalk.GaussianRandomWalk(0, 2),
        walk2Line: RO.Alg.RandomWalk.GaussianRandomWalk(0, 2),
    }
    def addRandomValues(line, interval=100):
        var = varDict[line]
        line.addPoint(var.next())
        root.after(interval, addRandomValues, line, interval)

    addRandomValues(countsLine, interval=500)
    addRandomValues(walk1Line, 1600)
    addRandomValues(walk2Line, 1900)
    
    def deleteSatConstLine():
        stripChart.removeLine(satConstLine)
    Tkinter.Button(root, text="Delete Saturated Counts", command=deleteSatConstLine).pack()

    def deleteWalk1():
        stripChart.removeLine(walk1Line)
    Tkinter.Button(root, text="Delete Walk 1", command=deleteWalk1).pack()

    root.mainloop()
