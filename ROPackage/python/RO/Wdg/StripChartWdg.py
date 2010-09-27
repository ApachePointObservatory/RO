#!/usr/bin/env python
"""A widget to changing values in real time as a strip chart

Warnings:
- Requires matplotlib built with TkAgg support
- This widget is somewhat experimental and the API may change.

Useful resource settings:
# set background color of axes region to white
matplotlib.rc("figure", facecolor="white") 
matplotlib.rc("legend", fontsize="medium") 

Known issues:
- The x label is truncated if the window is short. This is due to poor auto-layout on matplotlib's part.
  I am not yet sure whether to wait for a fix to matplotlib or hack around the problem.
- User may wish to choose flat step style with lines drawn to the right edge,
  instead of connect-the-dot style with no line after the last seen datapoint
- Spacing between subplots is rather large (but given the way matplotlib labels ticks
  I'm not sure it could be compressed much more without conflicts between Y axis labels).

History:
2010-09-27  ROwen
"""
import bisect
import datetime
import time
import numpy
import Tkinter
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import RO.SeqUtil

# to set background color of axes region:
# matplotlib.rc('figure', facecolor='w') 

__all__ = ["StripChartWdg"]

_UseAnimation = True

class StripChartWdg(Tkinter.Frame):
    """A widget to changing values in real time as a strip chart
    
    For each variable quantity to display:
    - Call addLine once to specify the quantity
    - Call addPoint for each new data point you wish to display

    For each constant line (e.g. limit) to display:
    - Call addConstantLine.
    
    All supplied times are POSIX timestamps (e.g. as supplied by time.time()).
    You may choose the kind of time displayed on the time axis (e.g. UTC or local time) using cnvTimeFunc
    and the format of that time using dateFormat.
    
    To refine the display manipulate the axes attribute (a matplotlib.Axes).
    For instance (useful if your time range is < 300 seconds or so):
    # show a major tick every 10 seconds on even 10 seconds
    stripChart.axes.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,61,10)))
        
    Potentially useful attributes:
    - axes: the last subplot (all subplots share the same x axis, so to manipulate
        properties of the x axis you only have manipulate them for axes)
    - subplotArr: list of subplots, from top to bottom; each is a matplotlib Subplot object,
        which is basically an Axes object but specialized to live in a rectangular grid
    - canvas: the FigureCanvas
    """
    def __init__(self,
        master,
        timeRange = 3600,
        width = 8,
        height = 2,
        numSubplots = 1,
        showGrid = True,
        dateFormat = "%H:%M:%S",
        updateInterval = None,
        cnvTimeFunc = None,
        doAutoscale = True,
    ):
        """Construct a StripChartWdg with the specified time range
        
        Eventually we should support multiple axes and multiple values/axis
        but let's start simple with one axis.
        
        Inputs:
        - master: Tk parent widget
        - timeRange: range of time displayed (seconds)
        - minY: minimum Y value
        - maxY: maximum Y value
        - width: width of graph in inches
        - height: height of graph in inches
        - numSubplots: the number of subplots
        - showGrid: if True a grid is shown
        - dateFormat: format for major axis labels, using time.strftime format
        - updateInterval: now often the time axis is updated (seconds); if None a value is calculated
        - cnvTimeFunc: a function that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days;
            typically an instance of TimeConverter; defaults to TimeConverter(useUTC=False)
        - doAutoscale: if True then autoscale the y axis of the associated subplot,
            else you should call setYLimit for the subplot.
            May be a single value (which is applied to all subplots) or a sequence of numSubplot values.
        """
        Tkinter.Frame.__init__(self, master)
        
        self._timeRange = timeRange
        if updateInterval == None:
            updateInterval = max(0.1, min(5.0, timeRange / 2000.0))
        self.updateInterval = float(updateInterval)
        self._purgeCounter = 0
        self._maxPurgeCounter = max(1, int(0.5 + (5.0 / self.updateInterval)))
        self._background = None

        if cnvTimeFunc == None:
            cnvTimeFunc = TimeConverter(useUTC=False)
        self._cnvTimeFunc = cnvTimeFunc
        self._doAutoscaleArr = RO.SeqUtil.oneOrNAsList(doAutoscale, numSubplots, "doAutoscale")

        figure = matplotlib.figure.Figure(figsize=(width, height), frameon=True)
        self.canvas = FigureCanvasTkAgg(figure, self)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="news")
        if _UseAnimation:
            self.canvas.mpl_connect('draw_event', self._handleDrawEvent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        bottomSubplot = figure.add_subplot(numSubplots, 1, numSubplots)
        self.subplotArr = [figure.add_subplot(numSubplots, 1, n+1, sharex=bottomSubplot) \
            for n in range(numSubplots-1)] + [bottomSubplot]
        self.axes = self.subplotArr[-1]
        if showGrid:
            for subplot in self.subplotArr:
                subplot.grid(True)

# alternate means of hiding x labels on all subplots but the last
# however calling subplot.label_outer() is easier and seems to work fine
#         for subplot in self.subplotArr[0:-1]:
#             for ticklabel in subplot.get_xticklabels():
#                 ticklabel.set_visible(False)

        self.axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(dateFormat))
        self.axes.xaxis_date()

        for subplot in self.subplotArr:
            subplot.label_outer() # disable axis labels on all but the bottom subplot
#            subplot.yaxis.get_major_locator().set_params(prune = "upper")
#        figure.subplots_adjust(hspace=0.1)
        
        self._lineDict = dict()
        self._constLineDict = dict()
        self._timeAxisTimer = None
        self._updateTimeAxis()

    def addConstantLine(self, label, y, subplotInd=0, includeInLegend=False, **kargs):
        """Add a new constant to plot
        
        Inputs:
        - label: label for constant line
        - y: value of constant line
        - includeInLegend: if True then the line is labelled; otherwise it is not
        - subplotInd: index of subplot
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        subplot = self.subplotArr[subplotInd]
        self._constLineDict[label] = subplot.axhline(y, **kargs)
        if includeInLegend:
            self._constLineDict[label].set_label(label)
        yMin, yMax = self.axes.get_ylim()
        if self._doAutoscaleArr[subplotInd] and numpy.isfinite(y) and not (yMin <= y <= yMax):
            self.axes.relim()
            self.axes.autoscale_view(scalex=False, scaley=True)

    def addLine(self, label, subplotInd=0, **kargs):
        """Add a new quantity to plot
        
        Inputs:
        - label: label for line
        - subplotInd: index of subplot
        all other keyword arguments are sent to the _Line constructor
        """
        if label in self._lineDict:
            raise RuntimeError("Line %s already exists" % (label,))
        axes = self.subplotArr[subplotInd]
        doAutoscale = self._doAutoscaleArr[subplotInd]
        self._lineDict[label] = _Line(label, axes=axes, doAutoscale=doAutoscale, **kargs)
    
    def addPoint(self, label, y, t=None):
        """Add a data point to a specified line
        
        Inputs:
        - label: label of Line
        - y: y value
        - t: time as a POSIX timestamp (e.g. time.time()); if None then "now"
        """
        if t == None:
            t = time.time()
        mplDays = self._cnvTimeFunc(t)
        self._lineDict[label].addPoint(y, mplDays)
        if _UseAnimation:
            self._drawPoints()
    
    def setYLimits(self, subplotInd, minY, maxY):
        """Set y limits for the specified subplot
        """
        self.subplotArr[subplotInd].set_ylim(minY, maxY)
    
    def _drawPoints(self):
        """Redraw the lines
        
        Only used if _UseAnimation True, since then adding points to lines does not update the display.
        """
        if not self._background:
            return
#        self.canvas.restore_region(self._background)
        for line in self._lineDict.itervalues():
            line.axes.draw_artist(line.line)
        self.canvas.blit(self.axes.bbox)
    
    def _handleDrawEvent(self, event):
        """Handle draw event
        """
        self._background = self.canvas.copy_from_bbox(self.axes.bbox)
        self._drawPoints()
    
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
        
        for subplotInd, subplot in enumerate(self.subplotArr):
            subplot.set_xlim(minMplDays, maxMplDays)
            if self._doAutoscaleArr[subplotInd] and doPurge:
                # since data is being purged the y limits may have changed
                subplot.relim()
                subplot.autoscale_view(scalex=False, scaley=True)
        self.canvas.draw()
        self._timeAxisTimer = self.after(int(self.updateInterval * 1000), self._updateTimeAxis)


class _Line(object):
    """A line (trace) on a strip chart representing some varying quantity
    
    Attributes that might be useful:
    - label: the label of this line
    - axes: the matplotlib Axes or Subplot instance displaying this line
    - line: the matplotlib.lines.Line2D associated with this line
    """
    def __init__(self, label, axes, doAutoscale, **kargs):
        """Create a line
        
        Inputs:
        - label: label of line
        - axes: the matplotlib Axes or Subplot instance displaying this line
        - doAutoscale: if True then autoscale the y axis
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self.label = label
        self.axes = axes
        self.line = matplotlib.lines.Line2D([], [], animated=_UseAnimation, label=label, **kargs)
        self.axes.add_line(self.line)
        self._doAutoscale = doAutoscale
        
    def addPoint(self, y, mplDays):
        """Append a new data point
        
        Inputs:
        - y: y value
        - mplDays: time as matplotlib days
        """
        tList, yList = self.line.get_data(True)
        tList.append(mplDays)
        yList.append(y)
        yMin, yMax = self.axes.get_ylim()
        self.line.set_data(tList, yList)
        if self._doAutoscale and numpy.isfinite(y) and not (yMin <= y <= yMax):
            self.axes.relim()
            self.axes.autoscale_view(scalex=False, scaley=True)
    
    def purgeOldData(self, minMplDays):
        """Purge data with t < minMplDays

        Inputs:
        - minMplDays: time before which to delete data (matpotlib days)
        
        Warning: does not update the display (the caller must do that)
        """
        tList, yList = self.line.get_data(True)
        if not tList:
            return
        numToDitch = bisect.bisect_left(tList, minMplDays)
        if numToDitch > 0:
            self.line.set_data(tListp[numToDitch:], yList[numToDitch:])

    def __str__(self):
        return "%s(%r)" % (type(self).__name__, self.label)


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
    root = Tkinter.Tk()
    stripChart = StripChartWdg(
        master = root,
        timeRange = 60,
        numSubplots = 2,
        doAutoscale = True,
        cnvTimeFunc = TimeConverter(useUTC=True),
    )
    stripChart.pack(expand=True, fill="both")
    stripChart.addLine("test", subplotInd=0)
    stripChart.subplotArr[0].yaxis.set_label_text("Test (ADU)")
    stripChart.addConstantLine("max", 20.90, color="red", includeInLegend=False)
    stripChart.subplotArr[0].legend(loc=3)
#    stripChart.setYLimits(0, 0.0, 1.0)
    # the default ticks for time spans <= 300 is not nice, so be explicit
    stripChart.axes.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,61,10)))
    
    stripChart.addLine("foo", subplotInd=1, color="green")

    def addRandomValues(label, interval=100):
        val = numpy.random.rand(1)[0] * 3
        stripChart.addPoint(label, val)
        root.after(interval, addRandomValues, label, interval)

    addRandomValues("test", interval=500)
    addRandomValues("foo", 3000)
    root.mainloop()
