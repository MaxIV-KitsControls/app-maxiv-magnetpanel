from taurus.external.qt.QtCore import QSize
from taurus.external.qt.QtGui import QIcon, QPushButton, QWidget
from taurus.qt.qtgui.panel import TaurusValue


class ResettableTaurusValue(TaurusValue):

    "A TaurusValue with a reset button (if writable)"

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._initialWriteValue = None

    def _storeInitialWriteValue(self):
        "Keep the write-value from when the widget is created"
        attr = self.getModelValueObj()
        self._initialWriteValue = attr.w_value

    def resetInitialWriteValue(self):
        # model = self.getModelObj()
        # model.write(self._initialWriteValue)

        # The above is a bit dangeous... let's just update the local value
        # and require the user to press enter etc to apply the change.
        self.writeWidget().setValue(self._initialWriteValue)
        self.writeWidget().setFocus()

    def setModel(self, model):
        super(self.__class__, self).setModel(model)
        model = self.getModelObj()
        self._storeInitialWriteValue()
        if model.isReadWrite():
            self.extraWidgetClass = ValueResetButton

    def getDefaultExtraWidgetClass(self):
        # Unfortunately, the TaurusForm seems to freak out a bit if
        # we don't return a widget here, if there are other values
        # that have reset buttons. So we return an empty QWidget.
        return DummyExtraWidget


class DummyExtraWidget(QWidget):
    "Just a placeholder"
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.setFixedWidth(0)


class ValueResetButton(QPushButton):

    "A button to reset a write-value"

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        icon = QIcon.fromTheme("edit-undo")
        self.setIcon(icon)
        # TODO: figure out how to get a smaller version of the icon
        # print icon.availableSizes()
        self.setFixedSize(QSize(25, 25))

        self.clicked.connect(self._clicked)

    def _clicked(self, event):
        self.taurusValueBuddy().resetInitialWriteValue()

    def setModel(self, model):
        # This is a bit of a hack, as this is not really a
        # TaurusWidget.  But we need wait for the model to be set
        # before we can access the initial value.
        value = self.taurusValueBuddy()._initialWriteValue
        attr = self.taurusValueBuddy().getModelObj()
        fmt = attr.format if attr.format != "Not specified" else None
        unit = attr.unit if attr.unit != "No unit" else ""
        print attr, value, fmt, unit
        if fmt:
            tooltip = ('Reset to initial value: %s %s' % (fmt, unit)) % value
        else:
            tooltip = 'Reset to initial value: %s %s' % (value, unit)
        self.setToolTip(tooltip)
