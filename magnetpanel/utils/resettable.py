from taurus.external.qt import QtCore
from taurus.external.qt.QtCore import QSize
from taurus.external.qt.QtGui import QIcon, QPushButton, QWidget
from taurus.qt.qtgui.panel import TaurusValue


class ResettableTaurusValue(TaurusValue):
    """A TaurusValue with a reset button (if writable)."""

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._storedValue = None

    def storeCurrentValue(self):
        """Keep the attribute value from when the widget is created"""
        attr = self.getModelValueObj()
        self._storedValue = attr.w_value

    def resetToStoredValue(self):
        model = self.getModelObj()
        model.write(self._storedValue)
        self.writeWidget().setValue(self._storedValue)
        self.writeWidget().setFocus()

    def setModel(self, model):
        super(self.__class__, self).setModel(model)
        model = self.getModelObj()
        if model is not None:
            self.storeCurrentValue()
            if model.isReadWrite():
                self.extraWidgetClass = ValueResetButton

    def getDefaultExtraWidgetClass(self):
        # Unfortunately, the TaurusForm seems to freak out a bit if
        # we don't return a widget here, if there are other values
        # that have reset buttons. So we return an empty QWidget.
        return DummyExtraWidget


class DummyExtraWidget(QWidget):
    """Just a placeholder"""

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.setFixedWidth(0)


class ValueResetButton(QPushButton):
    """A button to store/reset a write-value"""

    # TODO: right-click to store value

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        icon = QIcon.fromTheme("edit-undo")
        self.setIcon(icon)
        # TODO: figure out how to get a smaller version of the icon
        # print icon.availableSizes()
        self.setFixedSize(QSize(25, 25))

    def mousePressEvent(self, event):
        button = event.button()
        if button == QtCore.Qt.LeftButton:
            # left button restores stored value
            self.taurusValueBuddy().resetToStoredValue()
        elif button == QtCore.Qt.RightButton:
            # right button stores the current value
            self.taurusValueBuddy().storeCurrentValue()
            self.setModel(None)

    def contextMenuEvent(self, event):
        pass  # we override to remove the context menu

    def setModel(self, model):
        # This is a bit of a hack, as this is not really a
        # TaurusWidget.  But we need wait for the model to be set
        # before we can access the initial value.
        self._update_tooltip()

    def _update_tooltip(self):
        value = self.taurusValueBuddy()._storedValue
        attr = self.taurusValueBuddy().getModelObj()
        if attr is not None:
            fmt = attr.format if attr.format != "Not specified" else None
            unit = attr.unit if attr.unit != "No unit" else ""
            if fmt:
                tooltip = f"Reset to value: <b>{fmt} {unit}</b>" % value
            else:
                tooltip = f"Reset to value: <b>{value} {unit}</b>"
            self.setToolTip(tooltip + "<p>(Right-click to store)")
        else:
            self.setToolTip("")
