import taurus
from taurus.qt.qtgui.input import TaurusValueLineEdit
from taurus.qt import QtCore, Qt
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

    def __init__(self, parent=None, designMode=False):
        TaurusValueLineEdit.__init__(self, parent, designMode)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)

    def _stepBy(self, steps):
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
            self.writeValue()

    def focusInEvent(self, event):
        self._focus = True
        TaurusValueLineEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self._focus = False
        self.resetPendingOperations()  # discard unwritten changes (safer?)
        TaurusValueLineEdit.focusOutEvent(self, event)

    def _updateWriteValue(self, value):
        cursor_position = self.cursorPosition()
        self.setValue(value)
        self.setCursorPosition(cursor_position)

    def handleEvent(self, evt_src, evt_type, evt_value):
        TaurusValueLineEdit.handleEvent(self, evt_src, evt_type, evt_value)
        if evt_type in (PyTango.EventType.PERIODIC_EVENT,
                        PyTango.EventType.CHANGE_EVENT):
                        # taurus.core.taurusbasetypes.TaurusEventType.Periodic,
                        # taurus.core.taurusbasetypes.TaurusEventType.Change):
            if not self._focus:
                self._updateWriteValue(evt_value.w_value)
        elif evt_type in (PyTango.EventType.ATTR_CONF_EVENT,
                          PyTango.EventType.QUALITY_EVENT):
                #taurus.core.taurusbasetypes.TaurusEventType.Config:
            # update the wheel delta to correspond to the LSD
            digits = self._decimalDigits(evt_value.format)
            if digits:
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
        TaurusValueLineEdit._stepBy(self, numSteps*self._wheel_delta)
        if self._autoApply:
            self.writeValue()

    @classmethod
    def getQtDesignerPluginInfo(cls):
        ret = TaurusValueLineEdit.getQtDesignerPluginInfo()
        ret['group']  = 'MAX-lab Taurus Widgets'
        ret['module'] = 'maxwidgets.input'
        return ret
