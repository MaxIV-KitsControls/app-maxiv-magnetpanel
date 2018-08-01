import taurus
from taurus.external.qt import Qt, QtCore, QtGui
from taurus.qt.qtgui.input import TaurusValueLineEdit
from taurus.qt.qtgui.container import TaurusWidget

import PyTango


class MAXLineEdit (TaurusValueLineEdit):

    """A TaurusValueLineEdit tweaked to fit MAXIV purposes. Changes:

    - The current digit (left of the cursor) can be in- or decremented
    by pressing the up/down arrow keys. If autoApply is activated, the
    value will be written on each such keypress.

    - The mouse wheel can be used to freely change the value. The
    change will occur in the least significant digit, configured by
    the Tango attribute format. autoApply works like above.

    - The widget will update the write value even if it is changed
    from somewhere else. The exception is if the widget is currently
    focused (the assumption being that the user is editing it.)

    """

    _focus = False
    _wheel_delta = 1
    w_value_trigger = QtCore.pyqtSignal()

    def __init__(self, parent=None, designMode=False):
        TaurusValueLineEdit.__init__(self, parent, designMode)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)
        self._throttle_timer = QtCore.QTimer()
        self._throttle_timer.setInterval(200)
        self._throttle_timer.setSingleShot(True)
        self.connect(self._throttle_timer, QtCore.SIGNAL("timeout()"), self._writeValue)
        self.w_value_trigger.connect(self._updateWriteValue)

    def _stepBy(self, steps):

        """try to figure out which digit the cursor is at, and step by one in
        that digit."""

        text = str(self.text())
        cursor = len(text) - self.cursorPosition()

        if '.' not in self.text():
            decimal = 0
        else:
            decimal = len(text) - text.find('.') - 1

        if cursor == decimal:
            return
        if cursor == len(text):
            return

        exp = cursor - decimal
        if cursor > decimal:
            exp -= 1

        delta = 10**exp

        TaurusValueLineEdit._stepBy(self, steps*delta)
        self.setCursorPosition(len(self.text()) - cursor)
        if self._autoApply:
            self.writeValue()  # this seems a but risky...

    def focusInEvent(self, event):
        self._focus = True
        TaurusValueLineEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self._focus = False
        self.resetPendingOperations()  # discard unwritten changes (safer?)
        TaurusValueLineEdit.focusOutEvent(self, event)

    def _updateWriteValue(self):
        cursor_position = self.cursorPosition()
        self.setValue(self._w_value)
        self.setCursorPosition(cursor_position)

    def handleEvent(self, evt_src, evt_type, evt_value):
        TaurusValueLineEdit.handleEvent(self, evt_src, evt_type, evt_value)
        if evt_type in (PyTango.EventType.PERIODIC_EVENT,
                        PyTango.EventType.CHANGE_EVENT):
                        # taurus.core.taurusbasetypes.TaurusEventType.Periodic,
                        # taurus.core.taurusbasetypes.TaurusEventType.Change):
            if not self._focus:
                self._w_value = evt_value.w_value
                self.w_value_trigger.emit()
        elif evt_type in (PyTango.EventType.ATTR_CONF_EVENT,
                          PyTango.EventType.QUALITY_EVENT):
            # update the wheel delta to correspond to the LSD
            digits = self._decimalDigits(evt_value.format)
            if digits is not None:
                self._wheel_delta = pow(10, -digits)

    def _decimalDigits(self, fmt):
        '''returns the number of decimal digits from a format string
        (or None if they are not defined)'''
        try:
            if fmt[-1].lower() in ['f', 'g'] and '.' in fmt:
                return int(fmt[:-1].split('.')[-1])
            else:
                return None
        except:
            return None

    @QtCore.pyqtSlot()
    def _writeValue(self):
        self.writeValue()

    def throttledWrite(self, delta):
        """Intead of writing to Tango every time the value changes, we start a
        timer. Writes during the timer will be accumulated and when the timer
        runs out, the last value is written.
        """
        TaurusValueLineEdit._stepBy(self, delta)
        if not self._throttle_timer.isActive():
            self._throttle_timer.start()

    def wheelEvent(self, evt):
        if not self.getEnableWheelEvent() or Qt.QLineEdit.isReadOnly(self):
            return Qt.QLineEdit.wheelEvent(self, evt)
        model = self.getModelObj()
        if model is None or not model.isNumeric():
            return Qt.QLineEdit.wheelEvent(self, evt)

        evt.accept()
        numDegrees = evt.delta() / 8
        numSteps = numDegrees / 15
        modifiers = evt.modifiers()
        if modifiers & Qt.Qt.ControlModifier:
            numSteps *= 10
        elif (modifiers & Qt.Qt.AltModifier) and model.isFloat():
            numSteps *= .1

        # change the value by 1 in the least significant digit according
        # to the configured format.
        self.throttledWrite(numSteps*self._wheel_delta)

    @classmethod
    def getQtDesignerPluginInfo(cls):
        ret = TaurusValueLineEdit.getQtDesignerPluginInfo()
        ret['group'] = 'MAX-lab Taurus Widgets'
        ret['module'] = 'maxwidgets.input'
        return ret

    def resetInitialValue(self):
        pass


class ResettableMAXLineEdit(TaurusWidget):

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        vbox = QtGui.QVBox(layout=self)
        self.lineedit = MAXLineEdit(parent=vbox)

    def __getattr__(self, attr):
        return getattr(self.lineedit, attr)
