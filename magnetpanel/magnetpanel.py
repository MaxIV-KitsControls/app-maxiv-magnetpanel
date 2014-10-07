from functools import partial
import time
from math import isnan

import PyTango
from taurus.qt import QtCore, QtGui
from taurus import Attribute

from taurus.qt.qtgui.input import TaurusValueLineEdit
#from maxwidgets.input import MAXLineEdit

from taurus.qt.qtgui.panel import TaurusWidget, TaurusForm
from taurus.qt.qtgui.display import TaurusLabel, TaurusLed, TaurusLabel
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.plot import TaurusTrend
#from maxwidgets.display import MAXValueBar
from maxvaluebar import MAXValueBar
#from maxwidgets.panel import MAXForm
from maxform import MAXForm

from numpy import ndarray


class AttributeColumn(object):

    def __init__(self,parent,column):
        self.parent = parent
        self.column = column

    def event_received(self, *args):
        self.parent.onEvent(self.column, *args)


class AttributeColumnsTable(TaurusWidget):

    """Display several spectrum attributes belonging to the same
    device as columns in a table."""

    trigger = QtCore.pyqtSignal(int, ndarray)

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.table = QtGui.QTableWidget()

        hbox.addWidget(self.table)

        self.trigger.connect(self.updateColumn)

    def setModel(self, attrs):
        try:
            TaurusWidget.setModel(self, attrs[0].rsplit("/", 1)[0])
            self.attributes = [Attribute(a) for a in attrs]

            self.table.setColumnCount(len(attrs))
            fmt = "%s [%s]"
            labels = []
            for a in self.attributes:
                config = a.getConfig()
                label = fmt % (config.getLabel(), config.getUnit())
                labels.append(label)

            self.table.setHorizontalHeaderLabels(labels)
            header = self.table.horizontalHeader()
            header.setResizeMode(QtGui.QHeaderView.Stretch)

            # Check if there are any columns at all
            row_lengths = [len(a.read().value) for a in self.attributes
                           if a.read().quality == PyTango.AttrQuality.ATTR_VALID]
            if not any(row_lengths):
                return None
            self.table.setRowCount(max(row_lengths))

            self._columns = []

            for i, att in enumerate(self.attributes):
                # JFF: this is a workaround for a behavior in Taurus. Just
                # adding a new listener to each attribute does not work, the
                # previous ones get removed for some reason.
                col = AttributeColumn(self, i)
                self._columns.append(col)  # keep reference to prevent GC
                att.addListener(col.event_received)
        except PyTango.DevFailed:
            pass

    def onEvent(self, column, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                    PyTango.EventType.PERIODIC_EVENT]:
            self.trigger.emit(column, evt_value.value)

    def updateColumn(self, column, values):
        for row, value in enumerate(values):
            if not isnan(value):
                item = QtGui.QTableWidgetItem(str(value))
                item.setFlags( QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled )
            else:
                item = QtGui.QTableWidgetItem("N/A")
                item.setFlags( QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled )
                item.setBackgroundColor(QtGui.QColor(200, 200, 200))
            self.table.setItem(row, column, item)


class DevnameAndState(TaurusWidget):

    """A widget that displays the name and state of a device"""

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        grid = QtGui.QGridLayout(self)
        self.setLayout(grid)

        grid.addWidget(QtGui.QLabel("Device:"), 0, 0)
        self.devicename_label = QtGui.QLabel("<devicename>")
        grid.addWidget(self.devicename_label, 0, 1)

        grid.addWidget(QtGui.QLabel("State:"), 1, 0)
        hbox = QtGui.QHBoxLayout(self)
        #self.state_led = TaurusLed()
        #hbox.addWidget(self.state_led)
        self.state_label = TaurusLabel()
        # policy = QtGui.QSizePolicy()
        # policy.setHorizontalPolicy(QtGui.QSizePolicy.Fixed)
        # self.state_label.setSizePolicy(policy)

        hbox.addWidget(self.state_label)
        #hbox.insertStretch(2, 1)

        grid.addLayout(hbox, 1, 1, alignment=QtCore.Qt.AlignLeft)
        grid.setColumnStretch(1, 1)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        self.devicename_label.setText("<b>%s</b>" % device)
        #self.state_led.setModel("%s/State" % device)
        self.state_label.setModel("%s/State" % device)


#class DevnameAndStatePl


class StatusArea(TaurusWidget):

    """A (scrolling) text area that displays device status, or any other
    string attribute."""

    statusTrigger = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, down_command=None, up_command=None, state=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QVBoxLayout(self)
        self.setLayout(hbox)

        self.status_label = QtGui.QLabel("(No status has been read.)")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(QtCore.Qt.AlignTop)
        status_scroll_area = QtGui.QScrollArea()
        status_scroll_area.setMaximumSize(QtCore.QSize(100000, 100))
        status_scroll_area.setWidgetResizable(True)
        status_scroll_area.setWidget(self.status_label)
        hbox.addWidget(status_scroll_area)

        self.statusTrigger.connect(self.updateStatus)

    def setModel(self, model):
        split_model = model.split("/")
        if len(split_model) < 4:
            status = Attribute("%s/Status" % model)
        else:
            status = Attribute(model)
        status.addListener(self.onStatusChange)

    def onStatusChange(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            self.statusTrigger.emit(evt_value.value)

    def updateStatus(self, status):
        self.status_label.setText(status)


class ToggleButton(TaurusWidget):

    """A button that has two states, pressed and unpressed. When pressing
    it, the 'down' command is run, and when unpressing it the 'up' command
    is run. The 'pressedness' of the button is connected to a given
    Tango state, e.g. ON."""

    state_trigger = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, down_command=None, up_command=None, state=None):
        TaurusWidget.__init__(self, parent)
        self._down_command = down_command
        self._up_command = up_command
        self._state = state
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.button = QtGui.QPushButton()
        #self.button.setText()
        self.button.setCheckable(True)
        hbox.addWidget(self.button)

        self.button.clicked.connect(self.onClick)
        self.state_trigger.connect(self.change_state)

    def setModel(self, model):
        TaurusWidget.setModel(self, model)
        m = self.getModelObj()
        self.down_command = getattr(m, self._down_command)
        self.up_command = getattr(m, self._up_command)

        self.state = m.getAttribute("State")
        self.state.addListener(self.handle_state_event)

    def onClick(self):
        print "state is", self.state.read()
        pressed = self.state.read().value == self._state
        print "pressed", pressed
        if pressed:
            print "running up_commnad", self._up_command
            self.up_command()
        else:
            print "running down_command", self._down_command
            self.down_command()

    def change_state(self, new_state):
        print "change_state", new_state
        self.button.setChecked(new_state)
        self.button.setText((self._down_command, self._up_command)[new_state])

    def handle_state_event(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            print "state", self._state
            self.state_trigger.emit(evt_value.value == self._state)


class PowerSupply(TaurusWidget):

    attrs = ["Current", "Voltage", "Impedance"]

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        form_vbox = QtGui.QVBoxLayout(self)
        # devicename label

        hbox2 = QtGui.QHBoxLayout(self)
        self.device_and_state = DevnameAndState(self)
        hbox2.addWidget(self.device_and_state, stretch=2)

        # commands
        commandbox = QtGui.QHBoxLayout(self)
        self.start_button = TaurusCommandButton(command="On")
        self.start_button.setUseParentModel(True)
        self.stop_button = TaurusCommandButton(command="Off")
        self.stop_button.setUseParentModel(True)
        commandbox.addWidget(self.start_button)
        commandbox.addWidget(self.stop_button)
        # self.state_button = ToggleButton(down_command="Start",
        #                                  up_command="Stop",
        #                                  state=PyTango.DevState.ON)
        #commandbox.addWidget(self.state_button)
        hbox2.addLayout(commandbox, stretch=1)

        form_vbox.addLayout(hbox2)
        # attributes
        self.form = MAXForm(withButtons=False)

        form_vbox.addLayout(commandbox)
        form_vbox.addWidget(self.form, stretch=1)

        self.status_area = StatusArea()
        form_vbox.addWidget(self.status_area)

        hbox.addLayout(form_vbox)

        # value bar
        self.valuebar = MAXValueBar(self)
        slider_vbox = QtGui.QVBoxLayout(self)
        slider_vbox.setContentsMargins(10, 10, 10, 10)
        hbox.addLayout(slider_vbox)
        self.current_label = TaurusLabel()
        self.current_label.setAlignment(QtCore.Qt.AlignCenter)
        slider_vbox.addWidget(self.valuebar, 1)
        slider_vbox.addWidget(self.current_label)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        self.form.setModel(["%s/%s" % (device, attribute)
                            for attribute in self.attrs])
        #self.form.setFontSize(25)

        attrname = "%s/%s" % (device, "Current")
        self.valuebar.setModel(attrname)
        #self.state_button.setModel(device)
        attr = Attribute(attrname)
        self.current_label.setText("%s [%s]" % (attr.label, attr.unit))

        self.status_area.setModel(device)


class MagnetCircuit(TaurusWidget):

    attrs = ["energy", "variableComponent", "currentActual", "currentCalculated",
             "fixNormFieldOnEnergyChange"]

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        form_vbox = QtGui.QVBoxLayout(self)

        hbox2 = QtGui.QHBoxLayout(self)
        self.device_and_state = DevnameAndState(self)
        hbox2.addWidget(self.device_and_state)

        form_vbox.addLayout(hbox2)

        # attributes
        self.form = MAXForm(withButtons=False)

        form_vbox.addWidget(self.form, stretch=1)

        self.status_area = StatusArea(self)
        form_vbox.addWidget(self.status_area)

        hbox.addLayout(form_vbox)


        # value bar
        self.valuebar = MAXValueBar(self)
        slider_vbox = QtGui.QVBoxLayout(self)
        slider_vbox.setContentsMargins(10, 10, 10, 10)
        hbox.addLayout(slider_vbox)
        self.current_label = TaurusLabel()
        self.current_label.setAlignment(QtCore.Qt.AlignCenter)
        slider_vbox.addWidget(self.valuebar, 1)
        slider_vbox.addWidget(self.current_label)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        self.form.setModel(["%s/%s" % (device, attribute)
                            for attribute in self.attrs])
        #self.form[0].readWidgetClass = "TaurusValueLabel"  # why?
        #self.form.setFontSize(25)

        attrname = "%s/%s" % (device, "variableComponent")
        self.valuebar.setModel(attrname)
        attr = Attribute(attrname)
        self.current_label.setText("%s [%s]" % (attr.label, attr.unit))

        self.status_area.setModel(device)


class CyclePanel(TaurusWidget):

    trend_trigger = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        hbox = QtGui.QHBoxLayout(self)

        self.status_label = StatusArea()
        hbox.addWidget(self.status_label, stretch=1)
        # policy = QtGui.QSizePolicy()
        # policy.setVerticalPolicy(QtGui.QSizePolicy.Fixed)
        # self.status_label.setSizePolicy(policy)

        commandbox = QtGui.QHBoxLayout(self)
        # self.state_button = ToggleButton(down_command="StartCycle",
        #                                  up_command="StopCycle",
        #                                  state=PyTango.DevState.RUNNING)
        # commandbox.addWidget(self.state_button)
        self.start_button = TaurusCommandButton(command="StartCycle")
        self.start_button.setUseParentModel(True)
        self.stop_button = TaurusCommandButton(command="StopCycle")
        self.stop_button.setUseParentModel(True)
        commandbox.addWidget(self.start_button)
        commandbox.addWidget(self.stop_button)

        hbox.addLayout(commandbox, stretch=1)

        vbox.addLayout(hbox)

        self.trend = TaurusTrend()
        vbox.addWidget(self.trend, stretch=1)
        self.trend_trigger.connect(self.set_trend_paused)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        #self.state_button.setModel(device)
        self.status_label.setModel("%s/cyclingStatus" % device)

        ps = str(PyTango.Database().get_device_property(
            device, "PowerSupplyProxy")["PowerSupplyProxy"][0])

        self.trend.setPaused()
        self.trend.setModel(["%s/Current" % ps])
        #self.trend.setForcedReadingPeriod(1.0)
        self.trend.showLegend(True)

        # let's pause the trend when not cycling
        self.cyclingState = self.getModelObj().getAttribute("cyclingState")
        self.cyclingState.addListener(self.handle_cycling_state)

        # Note: the trend is acting a bit strange; it seems like it's
        # polling the value at the "forced reading period" even if
        # it's paused. Setting a low period makes the synoptic
        # sluggish, presumably because of frequent taurus reads. This
        # happens whether the trend is paused or not.

    def handle_cycling_state(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            print "cycle state", evt_value.value
            self.trend_trigger.emit(evt_value.value)

    def set_trend_paused(self, value):
        print "set_trend_paused", not value
        self.trend.setPaused(not value)


class FieldPanel(TaurusWidget):

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        label = QtGui.QLabel("Average field components, un-normalised and normalised")
        label.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(label)

        self.table = AttributeColumnsTable()
        vbox.addWidget(self.table)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        self.table.setModel(["%s/fieldA" % device,
                             "%s/fieldB" % device,
                             "%s/fieldAnormalised" % device,
                             "%s/fieldBnormalised" % device])


class MagnetPanel(TaurusWidget):

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        tabs = QtGui.QTabWidget()
        hbox.addWidget(tabs)

        self.circuit_widget = MagnetCircuit()
        self.circuit_tab = tabs.addTab(self.circuit_widget, "Overview")

        self.ps_widget = PowerSupply()
        self.ps_tab = tabs.addTab(self.ps_widget, "Power supply")

        self.cycle_widget = CyclePanel()
        self.cycle_tab = tabs.addTab(self.cycle_widget, "Cycle")

        self.field_widget = FieldPanel()
        self.field_tab = tabs.addTab(self.field_widget, "Field")

        # make the PS tab default for now...
        tabs.setCurrentIndex(self.ps_tab)

        self.resize(600, 400)

    def setModel(self, magnet):

        self.setWindowTitle(magnet)

        TaurusWidget.setModel(self, magnet)
        db = PyTango.Database()

	print db.get_device_property(magnet, "CircuitProxies")
        circuit = str(db.get_device_property(
            magnet, "CircuitProxies")["CircuitProxies"][0])
        self.circuit_widget.setModel(circuit)

        ps = str(db.get_device_property(
            circuit, "PowerSupplyProxy")["PowerSupplyProxy"][0])
        self.ps_widget.setModel(ps)

        self.cycle_widget.setModel(circuit)

        self.field_widget.setModel(circuit)


def main():
    from taurus.qt.qtgui.application import TaurusApplication
    import sys

    app = TaurusApplication(sys.argv)
    args = app.get_command_line_args()

    #w = PowerSupply()
    w = MagnetPanel()

    if len(args) > 0:
        w.setModel(args[0])
    app.setCursorFlashTime(0)

    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
