#!/usr/bin/env python
"""A widget to changing values in real time as a strip chart

Warnings:
- Requires matplotlib built with TkAgg support
- This widget is experimental and the API may change.

Known issues:
- The x label is often truncated. This is due to poor auto-layout on matplotlib's part.
  I am not yet sure whether to wait for a fix to matplotlib or hack around the problem.

History:
2010-09-22: first experimental version.
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
    
    For each variable quantity to display:
    - Call addLine once to specify the quantity
    - Call addPoint for each new data point you wish to display

    For each constant line (e.g. limit) to display:
    - Call addConstantLine.
    
    All supplied times are POSIX timestamps (e.g. as supplied by time.time()).
    You may choose the kind of time displayed on the time axis (e.g. UTC or local time) using cnvTimeFunc
    and the format of that time using dateFormat.
    
    To refine the display manipulate the axis attribute (a matplotlib.Axis).
    For instance:
        # show a major tick every 10 seconds on even 10 seconds
        stripChart.axis.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,61,10)))
        
    Potentially useful attributes:
    - axis: the matplotlib Axis object associated for this chart
    - canvas: the FigureCanvas
    """
    def __init__(self,
        master,
        timeRange = 3600,
        width = 8,
        height = 2,
        grid = True,
        dateFormat = "%H:%M:%S",
        updateInterval = None,
        cnvTimeFunc = None,
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
        - grid: if True a grid is shown
        - dateFormat: format for major axis labels, using time.strftime format
        - updateInterval: now often the time axis is updated (seconds); if None a value is calculated
        - cnvTimeFunc: a function that takes a POSIX timestamp (e.g. time.time()) and returns matplotlib days;
            typically an instance of TimeConverter; defaults to TimeConverter(useUTC=False)
        """
        Tkinter.Frame.__init__(self, master)
        
        if cnvTimeFunc == None:
            cnvTimeFunc = TimeConverter(useUTC=False)
        self._cnvTimeFunc = cnvTimeFunc
        
        self._timeRange = timeRange
        if updateInterval == None:
            updateInterval = max(0.1, min(5.0, timeRange / 2000.0))
        self._updateInterval = float(updateInterval)
        self._purgeCounter = 0
        self._maxPurgeCounter = max(1, int(0.5 + (5.0 / self._updateInterval)))
        self._background = None

        figure = matplotlib.figure.Figure(figsize=(width, height), frameon=True)
        self.canvas = FigureCanvasTkAgg(figure, self)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="news")
        self.canvas.mpl_connect('draw_event', self._updateBackground)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.axis = figure.add_subplot(1, 1, 1)
        if grid:
            self.axis.grid(True)
        self.axis.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(dateFormat))
        self.axis.xaxis_date()
        self._lineDict = dict()
        self._constLineDict = dict()
        self._timeAxisTimer = None
        self._updateTimeAxis()

    def addConstantLine(self, name, y, **kargs):
        """Add a new constant to plot
        
        Inputs:
        - name: name of constant line
        - y: value of constant line
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self._constLineDict[name] = ConstLine(name, y=y, stripChartWdg = self, **kargs)

    def addLine(self, name, **kargs):
        """Add a new quantity to plot
        """
        if name in self._lineDict:
            raise RuntimeError("Line %s already exists" % (name,))
        self._lineDict[name] = Line(name, stripChartWdg = self, **kargs)
    
    def addPoint(self, name, y, t=None):
        """Add a data point to a specified line
        
        Inputs:
        - name: name of Line
        - y: y value
        - t: time as a POSIX timestamp (e.g. time.time()); if None then "now"
        """
        self._lineDict[name].addPoint(y, t)
        self._drawPoints()
    
    def setYLimits(self, minY, maxY):
        """Set y limits
        """
        self.axis.set_ylim(minY, maxY)
    
    def _drawPoints(self):
        """Redraw the lines
        
        Note: all Lines have animated=True, so they are not redrawn using self.canvas.draw
        """
        if not self._background:
            return
#        self.canvas.restore_region(self._background)
        for line in self._lineDict.itervalues():
            self.axis.draw_artist(line.line)
        self.canvas.blit(self.axis.bbox)
    
    def _updateBackground(self, event):
        """Handle draw event
        """
        self._background = self.canvas.copy_from_bbox(self.axis.bbox)
        self._drawPoints()
    
    def _updateTimeAxis(self):
        """Update the time axis; calls itself
        """
        if self._timeAxisTimer != None:
            self.after_cancel(self._timeAxisTimer)
            self._timeAxisTimer = None
        tMax = time.time() + self._updateInterval
        tMin = tMax - self._timeRange
        
        self._purgeCounter = (self._purgeCounter + 1) % self._maxPurgeCounter
        if self._purgeCounter == 0:
            for line in self._lineDict.itervalues():
                line.purgeOldData(tMin)
        
        for constLine in self._constLineDict.itervalues():
            constLine.plot(tMin, tMax)
        
        self.axis.set_xlim(self._cnvTimeFunc(tMin), self._cnvTimeFunc(tMax))
        self.canvas.draw()
        self._timeAxisTimer = self.after(int(self._updateInterval * 1000), self._updateTimeAxis)


class Line(object):
    """A line (trace) on a strip chart representing some varying quantity
    
    Attributes that might be useful:
    - name: the name of this line
    - line: the matplotlib.lines.Line2D associated with this line
    """
    def __init__(self, name, stripChartWdg, **kargs):
        """Create a line
        
        Inputs:
        - name: name of line
        - stripChartWdg: the stripChartWdg on which to display the line
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self.name = name
        self._tyData = []
        self._cnvTimeFunc = stripChartWdg._cnvTimeFunc
        self.line = matplotlib.lines.Line2D([], [], animated=True, **kargs)
        stripChartWdg.axis.add_line(self.line)
        
    def addPoint(self, y, t=None):
        """Append a new data point
        
        Warning: does not update the display (the caller must do that)
        
        Inputs:
        - y: y value
        - t: time as a POSIX timestamp (e.g. time.time()); if None then "now"
        """
        if t == None:
            t = time.time()
        self._tyData.append((self._cnvTimeFunc(t), y))
        if len(self._tyData) > 1 and t < self._tyData[-2][0]:
            self._tyData.sort()
        self._setData()
    
    def purgeOldData(self, minTime):
        """Purge data with t < minTime

        Inputs:
        - minTime: time before which to delete data (unix seconds)
        
        Warning: does not update the display (the caller must do that)
        """
        tData = zip(*self._tyData)[0]
        minTimeDays = self._cnvTimeFunc(minTime)
        numToDitch = bisect.bisect_left(tData, minTimeDays)
        if numToDitch > 0:
            self._tyData = self._tyData[numToDitch:]
            self._setData()

    def _setData(self):
        tData, yData = zip(*self._tyData)
        self.line.set_data(tData, yData)
        

    def __str__(self):
        return "%s(%r)" % (type(self).__name__, self.name)


class ConstLine(object):
    """A horizontal line on a strip chart, e.g. representing a limit

    Attributes that might be useful:
    - name: the name of this line
    - line: the matplotlib.lines.Line2D associated with this line
    """
    def __init__(self, name, y, stripChartWdg, **kargs):
        """Create a constant line
        
        Inputs:
        - name: name of line
        - y: constant value to plot
        - stripChartWdg: the stripChartWdg on which to display the line
        - **kargs: keyword arguments for matplotlib Line2D, such as color
        """
        self.name = name
        self._yData = [float(y), float(y)]
        self._cnvTimeFunc = stripChartWdg._cnvTimeFunc
        self.line = matplotlib.lines.Line2D([], [], **kargs)
        stripChartWdg.axis.add_line(self.line)
    
    def plot(self, tMin, tMax):
        """Show the constant ranging from tMin to tMax
        
        Warning: does not update the display (the caller must do that)
        
        Inputs:
        - tMin: minimum time (unix sec)
        - tMax: maximum time (unix sec)
        """
        self.line.set_data([self._cnvTimeFunc(tMin), self._cnvTimeFunc(tMax)], self._yData)

    def __str__(self):
        return "%s(%r,%s)" % (type(self).__name__, self.name, self._yData[0])


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
    stripChart = StripChartWdg(root, timeRange=60, cnvTimeFunc=TimeConverter(useUTC=True))
    stripChart.pack(expand=True, fill="both")
    stripChart.addLine("test")
    stripChart.addConstantLine("max", 0.90, color="red")
    stripChart.setYLimits(0.0, 1.0)
    # the default ticks for time spans <= 300 is not nice, so be explicit
    stripChart.axis.xaxis.set_major_locator(matplotlib.dates.SecondLocator(bysecond=range(0,61,10)))
    
    stripChart.addLine("foo", color="green")

    def addRandomValues(name, interval=100):
        val = numpy.random.rand(1)[0]
        stripChart.addPoint(name, val)
        root.after(interval, addRandomValues, name, interval)

    addRandomValues("test", interval=500)
    addRandomValues("foo", 3000)
    root.mainloop()
