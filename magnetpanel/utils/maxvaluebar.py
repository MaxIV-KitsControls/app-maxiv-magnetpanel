from contextlib import contextmanager

from taurus.external.qt import Qt, QtCore, QtGui, QtWidgets
from taurus.external.qt.QtCore import QPointF as Point, QRectF as Rect
from taurus.qt.qtgui.container import TaurusWidget
from taurus import Configuration
import tango

__all__ = ["MAXValueBar"]

__docformat__ = "restructuredtext"

TICK_FORMAT = "%.1f"


class ValueBarWidget(QtWidgets.QWidget):

    def __init__(self):
        super(ValueBarWidget, self).__init__()

        self.initUI()

    def initUI(self):
        self.setMinimumSize(100, 150)

        self.value = 0
        self.write_value = None

        self.min_value = -100
        self.max_value = 100

        self.warn_high = None
        self.warn_low = None

        self.alarm_low = None
        self.alarm_high = None

        self.pad = 10

    def setValue(self, value, write_value=None):
        self.value = value
        self.write_value = write_value
        self.repaint()

    def setWriteValue(self, value):
        self.write_value = value

    def setRange(self, min_value, max_value):
        self.setMinimum(min_value)
        self.setMaximum(max_value)

    def setMinimum(self, value):
        self.min_value = value
        self.repaint()

    def setMaximum(self, value):
        self.max_value = value
        self.repaint()

    def setWarningLow(self, value):
        self.warn_low = value
        self.repaint()

    def setWarningHigh(self, value):
        self.warn_high = value
        self.repaint()

    def setAlarmLow(self, value):
        self.alarm_low = value
        self.repaint()

    def setAlarmHigh(self, value):
        self.alarm_high = value
        self.repaint()

    def _get_ticks(self):
        return [self.min_value, self.max_value]

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.draw_widget(qp)
        qp.end()

    def _draw_scale(self, w, h, fh, fw, qp):
        ticks = self._get_ticks()
        if all(t is not None for t in ticks):
            n = len(ticks) - 1
            qp.setPen(QtGui.QColor(0, 0, 0))
            qp.drawLine(Point(w, self.pad), Point(w, h + self.pad))
            for i, tick in enumerate(ticks):
                qp.drawLine(Point(w, h - i * h / n + self.pad),
                            Point(w + 5, h - i * h / n + self.pad))
                qp.drawText(Point(w + self.pad, h - i * h / n + self.pad + fw / 2),
                            TICK_FORMAT % tick)

    @contextmanager
    def _scale(self, qp):
        size = self.size()
        h = size.height() - 2 * self.pad

        qp.translate(0, self.pad)
        qp.scale(1, -h / (self.max_value - self.min_value))
        qp.translate(0, -self.max_value)
        yield
        qp.resetTransform()

    def draw_widget(self, qp):

        # TODO: clean up and complete the error handling; e.g. no limits,
        # non-valid qualities, etc.

        font = QtGui.QFont("Serif", 7, QtGui.QFont.Light)
        qp.setFont(font)

        metrics = qp.fontMetrics()
        ticks = self._get_ticks()
        fw = [metrics.width(TICK_FORMAT % s) for s in ticks
              if s is not None]
        if not fw:
            return  # no ticks, should draw something anyway..?

        fw = max(fw) if len(fw) > 0 else 0
        fh = metrics.height()
        size = self.size()
        w = size.width() - (self.pad + fw)
        h = size.height() - 2 * self.pad

        # draw things in the value scale
        with self._scale(qp):

            # frame
            qp.setPen(QtCore.Qt.transparent)
            qp.setBrush(QtGui.QColor(255, 255, 255))
            qp.drawRect(Rect(0, self.min_value, w, self.max_value - self.min_value))

            # warning
            if self.warn_high is not None:
                qp.setBrush(QtGui.QColor(255, 200, 150))
                qp.drawRect(Rect(0, self.warn_high, w, self.max_value - self.warn_high))

            if self.warn_low is not None:
                qp.setBrush(QtGui.QColor(255, 200, 150))
                qp.drawRect(Rect(0, self.min_value, w, abs(self.min_value - self.warn_low)))

            # alarm
            if self.alarm_high is not None:
                qp.setBrush(QtGui.QColor(255, 170, 170))
                qp.drawRect(Rect(0, self.alarm_high, w, self.max_value - self.alarm_high))

            if self.alarm_low is not None:
                qp.setBrush(QtGui.QColor(255, 170, 170))
                qp.drawRect(Rect(0, self.min_value, w, abs(self.min_value - self.alarm_low)))

            # value bar
            qp.setPen(QtGui.QColor(0, 200, 0))
            qp.setBrush(QtGui.QColor(0, 200, 0))
            qp.drawRect(Rect(10, 0, w - 2 * self.pad, self.value))

            # write value line
            qp.setPen(QtGui.QColor(255, 0, 0))
            if self.write_value:
                qp.drawLine(Point(0, self.write_value), Point(w, self.write_value))

            # zero line
            qp.setPen(QtGui.QColor(0, 0, 0))
            if self.min_value <= 0 <= self.max_value:
                qp.drawLine(0, 0, w + 5, 0)

        self._draw_scale(w, h, fw, fh, qp)


def float_or_none(value):
    return float(value) if (value and value != "Not specified") else None


class MAXValueBar(TaurusWidget):
    value_trigger = QtCore.pyqtSignal(float, float)
    conf_trigger = QtCore.pyqtSignal()

    _delta = 1

    def __init__(self, parent=None, designMode=False):
        TaurusWidget.__init__(self, parent, designMode=designMode)
        self._setup_ui()

        self._throttle_timer = QtCore.QTimer()
        self._throttle_timer.setInterval(200)
        self._throttle_timer.setSingleShot(True)
        # self.connect(self._throttle_timer, QtCore.SIGNAL("timeout()"), self._writeValue)
        self._throttle_timer.timeout.connect(self._writeValue)

        self._value = None

        self._acc_value = 0  # accumulate fast wheel events
        self._last_wheel = 0  # time of last wheel event

    @classmethod
    def getQtDesignerPluginInfo(cls):
        ret = TaurusWidget.getQtDesignerPluginInfo()
        ret["module"] = "maxvaluebar"
        ret["group"] = "MAX-lab Taurus Widgets"
        ret["container"] = ":/designer/frame.png"
        ret["container"] = False
        return ret

    def _setup_ui(self):
        vbox = QtGui.QHBoxLayout(self)
        self.valuebar = ValueBarWidget()
        vbox.addWidget(self.valuebar)
        self.setLayout(vbox)
        self.value_trigger.connect(self.valuebar.setValue)
        self.conf_trigger.connect(self.updateConfig)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)

    def setModel(self, model):
        TaurusWidget.setModel(self, model)
        self.updateConfig()
        conf = Configuration(f"{self.model}?configuration")
        conf.addListener(lambda *args: self.conf_trigger.emit())

    def _decimalDigits(self, fmt):
        """returns the number of decimal digits from a format string
        (or None if they are not defined)"""
        try:
            if fmt[-1].lower() in ["f", "g"] and "." in fmt:
                return int(fmt[:-1].split(".")[-1])
            else:
                return None
        except:
            return None

    def updateConfig(self):
        conf = Configuration(f"{self.model}?configuration")
        # Note: could be inefficient with lots of redraws?
        self.valuebar.setMaximum(float_or_none(conf.max_value))
        self.valuebar.setMinimum(float_or_none(conf.min_value))
        self.valuebar.setWarningHigh(float_or_none(conf.max_warning))
        self.valuebar.setWarningLow(float_or_none(conf.min_warning))
        self.valuebar.setAlarmHigh(float_or_none(conf.max_alarm))
        self.valuebar.setAlarmLow(float_or_none(conf.min_alarm))

        digits = self._decimalDigits(conf.format)
        if digits:
            self._delta = pow(10, -digits)

    @QtCore.pyqtSlot()
    def _writeValue(self):
        if self._value:
            self.getModelObj().write(self._value)

    def throttledWrite(self, value):
        """Instead of writing to Tango every time the value changes, we start a
        timer. Writes during the timer will be accumulated and when the timer
        runs out, the last value is written.
        """
        self._value = value
        if not self._throttle_timer.isActive():
            self._throttle_timer.start()

    def handleEvent(self, evt_src, evt_type, evt_value):
        if evt_type in (tango.EventType.PERIODIC_EVENT,
                        tango.EventType.CHANGE_EVENT):
            if evt_value.quality == tango.AttrQuality.ATTR_VALID:
                self.value_trigger.emit(evt_value.value, evt_value.w_value)
        elif evt_type in (tango.EventType.ATTR_CONF_EVENT,
                          tango.EventType.QUALITY_EVENT):
            # Note: why don't I get "ATTR_CONF" events when the attribute
            # config changes? Seems like I get QUALITY events instead..?
            self.conf_trigger.emit()

    def wheelEvent(self, evt):

        model = self.getModelObj()

        evt.accept()
        numDegrees = evt.delta() / 8
        numSteps = numDegrees / 15
        modifiers = evt.modifiers()
        if modifiers & Qt.Qt.ControlModifier:
            numSteps *= 10
        elif (modifiers & Qt.Qt.AltModifier) and model.isFloat():
            numSteps *= .1

        # We change the value by 1 in the least significant digit according
        # to the configured format.
        value = self.valuebar.write_value + numSteps * self._delta
        self.valuebar.setWriteValue(value)
        self.throttledWrite(value)


def main():
    import sys
    from taurus.qt.qtgui.application import TaurusApplication

    app = TaurusApplication(sys.argv)
    w = MAXValueBar()
    w.setModel(sys.argv[1])
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
