try:
    from collections import defaultdict
except ImportError:
    from defaultdict import defaultdict
from math import isnan

import PyTango
from taurus.qt import QtCore, QtGui
from taurus import Attribute

from taurus.qt.qtgui.panel import TaurusWidget, TaurusForm
from taurus.qt.qtgui.display import TaurusLabel, TaurusLed, TaurusLabel
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.plot import TaurusTrend
from maxwidgets.display import MAXValueBar
#from maxvaluebar import MAXValueBar
#from maxwidgets.panel import MAXForm
from maxform import MAXForm


# TODO: investigate setDisconnectOnHide()? Does not seem to work as I hoped...

STATE_COLORS = {
    PyTango.DevState.ON: (0, 255, 0),
    PyTango.DevState.OFF: (255, 255, 255),
    PyTango.DevState.CLOSE: (255, 255, 255),
    PyTango.DevState.OPEN: (0, 255, 0),
    PyTango.DevState.INSERT: (255, 255, 255),
    PyTango.DevState.EXTRACT: (0, 255, 0),
    PyTango.DevState.MOVING: (128, 160, 255),
    PyTango.DevState.STANDBY: (255, 255, 0),
    PyTango.DevState.FAULT: (255, 0, 0),
    PyTango.DevState.INIT: (204, 204, 122),
    PyTango.DevState.RUNNING: (128, 160, 255),
    PyTango.DevState.ALARM:  (255, 140, 0),
    PyTango.DevState.DISABLE: (255, 0, 255),
    PyTango.DevState.UNKNOWN: (128, 128, 128),
    None: (128, 128, 128)
}


class AttributeColumn(object):

    def __init__(self, parent, column):
        self.parent = parent
        self.column = column

    def event_received(self, *args):
        self.parent.onEvent(self.column, *args)


class TableItem(object):

    def __init__(self, parent, row, column):
        self.parent = parent
        self.row = row
        self.column = column

    def event_received(self, *args):
        self.parent.onEvent(self.row, self.column, *args)


class AttributeColumnsTable(TaurusWidget):

    """Display several 1D spectrum attributes belonging to the same
    device as columns in a table."""

    trigger = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.table = QtGui.QTableWidget()

        hbox.addWidget(self.table)

        self.trigger.connect(self.updateColumn)
        self.attributes = []
        self._columns = []

    def setModel(self, attrs):
        if not attrs:
            for att, col in zip(self.attributes, self._columns):
                att.removeListener(col.event_received)
        else:
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

                self._values = {}
                self._config = {}
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
            self._values[column] = evt_value
            self.trigger.emit(column)
        if isinstance(evt_value, PyTango.DeviceAttributeConfig):
            self._config[column] = evt_value

    def updateColumn(self, column):
        data = self._values[column]
        for row, value in enumerate(data.value):
            if not isnan(value):
                cfg = self._config.get(column)
                if cfg and cfg.format != "Not specified":
                    item = QtGui.QTableWidgetItem(cfg.format % value)
                else:
                    item = QtGui.QTableWidgetItem(str(value))
                item.setFlags(QtCore.Qt.ItemIsSelectable |
                              QtCore.Qt.ItemIsEnabled)
            else:
                item = QtGui.QTableWidgetItem("NaN")
                item.setFlags(QtCore.Qt.ItemIsSelectable |
                              QtCore.Qt.ItemIsEnabled)
                item.setBackgroundColor(QtGui.QColor(220, 220, 220))
            item.setTextAlignment(QtCore.Qt.AlignRight |
                                  QtCore.Qt.AlignVCenter)
            self.table.setItem(row, column, item)


class DeviceRowsTable(TaurusWidget):

    """A widget that displays a table where each row displays a device,
    and the values of selected attributes."""

    trigger = QtCore.pyqtSignal(int, int)


    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.table = QtGui.QTableWidget()

        hbox.addWidget(self.table)

        self.trigger.connect(self.update_item)
        self._items = {}

    def setModel(self, devices, attributes=[]):
        if not devices:
            for dev, attrs in self.attributes.items():
                for att in attrs:
                    att.removeListener(self._items[dev][att.name].event_received)
        else:
            try:
                #TaurusWidget.setModel(self, attrs[0].rsplit("/", 1)[0])
                attrnames = [a[0] if isinstance(a, tuple) else a for a in attributes]
                self.attributes = dict((dev, [Attribute("%s/%s" % (dev, a))
                                              for a in attrnames]) for dev in devices)

                self.table.setColumnCount(len(attributes) + 1)
                colnames = [a[1] if isinstance(a, tuple) else a for a in attributes]
                labels = ["Device"] + colnames
                self.table.setHorizontalHeaderLabels(labels)
                header = self.table.horizontalHeader()
                header.setResizeMode(QtGui.QHeaderView.Stretch)

                # Check if there are any columns at all
                self.table.setRowCount(len(devices))

                self._values = defaultdict(dict)
                self._config = defaultdict(dict)

                for r, (dev, attrs) in enumerate(self.attributes.items()):
                    item = QtGui.QTableWidgetItem(dev)
                    self.table.setItem(r, 0, item)
                    self._items[dev] = {}
                    for c, att in enumerate(attrs):
                        # JFF: this is a workaround for a behavior in Taurus. Just
                        # adding a new listener to each attribute does not work, the
                        # previous ones get removed for some reason.
                        titem = TableItem(self, r, c+1)
                        self._items[dev][att.name] = titem  # keep xreference to prevent GC
                        att.addListener(titem.event_received)

            except PyTango.DevFailed:
                pass

    def onEvent(self, row, column, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            self._values[row][column] = evt_value
            self.trigger.emit(row, column)
        if hasattr(evt_value, "format"):
            self._config[row][column] = evt_value

    def update_item(self, row, column):
        try:
            value = self._values[row][column]
            cfg = self._config[row].get(column)
            if cfg and cfg.format != "Not specified":
                item = QtGui.QTableWidgetItem(cfg.format % value.value)
            else:
                item = QtGui.QTableWidgetItem(str(value.value))
            item.setFlags( QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled )
            if value.type is PyTango.CmdArgType.DevState:
                if value.value in STATE_COLORS:
                    item.setBackgroundColor(QtGui.QColor(*STATE_COLORS[value.value]))
            self.table.setItem(row, column, item)
        except KeyError:
            pass


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
        policy = QtGui.QSizePolicy()
        policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        self.state_label.setSizePolicy(policy)

        hbox.addWidget(self.state_label)
        #hbox.insertStretch(2, 1)

        grid.addLayout(hbox, 1, 1, alignment=QtCore.Qt.AlignLeft)
        grid.setColumnStretch(1, 1)

    def setModel(self, device):
        TaurusWidget.setModel(self, device)
        self.devicename_label.setText("<b>%s</b>" % device)
        #self.state_led.setModel("%s/State" % device)
        if device:
            self.state_label.setModel("%s/State" % device)
        else:
            self.state_label.setModel(None)


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
        self.status = None

        self.statusTrigger.connect(self.updateStatus)

    def setModel(self, model):
        if model:
            split_model = model.split("/")
            if len(split_model) < 4:
                self.status = Attribute("%s/Status" % model)
            else:
                self.status = Attribute(model)
            self.status.addListener(self.onStatusChange)
        else:
            self.status.removeListener(self.onStatusChange)

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
        if model:
            m = self.getModelObj()
            self.down_command = getattr(m, self._down_command)
            self.up_command = getattr(m, self._up_command)

            self.state = m.getAttribute("State")
            self.state.addListener(self.handle_state_event)
        else:
            if self.state:
                self.state.removeListener(self.handle_state_event)

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


class PowerSupplyPanel(TaurusWidget):

    attrs = ["Current", "Voltage"]  #, "Resistance"]

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
        # self.form.setDisconnectOnHide(True)

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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        self.status_area.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])
            #self.form.setFontSize(25)

            attrname = "%s/%s" % (device, "Current")
            self.valuebar.setModel(attrname)
            #self.state_button.setModel(device)
            attr = Attribute(attrname)
            self.current_label.setText("%s [%s]" % (attr.label, attr.unit))
        else:
            self.form.setModel(None)
            self.valuebar.setModel(None)


class MagnetCircuitPanel(TaurusWidget):

    attrs = ["energy", "MainFieldComponent", "currentActual", "currentSet",
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
        self.magnet_type_label = QtGui.QLabel("Magnet type:")
        #self.magnet_type_label.setAlignment(QtCore.Qt.AlignTop)
        hbox2.addWidget(self.magnet_type_label)
        form_vbox.addLayout(hbox2)

        # attributes
        self.form = MAXForm(withButtons=False)
        # self.form.setDisconnectOnHide(True)

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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])
            #self.form[0].readWidgetClass = "TaurusValueLabel"  # why?
            #self.form.setFontSize(25)
            db = PyTango.Database()
            magnet = db.get_device_property(device, "MagnetProxies")["MagnetProxies"][0]
            magnet_type = PyTango.Database().get_device_property(magnet, "Type")["Type"][0]
            self.magnet_type_label.setText("Magnet type: <b>%s</b>" % magnet_type)
            attrname = "%s/%s" % (device, "MainFieldComponent")
            self.valuebar.setModel(attrname)
            attr = Attribute(attrname)
            self.current_label.setText("%s [%s]" % (attr.label, attr.unit))

            self.status_area.setModel(device)
        else:
            self.form.setModel(None)
            self.valuebar.setModel(None)
            self.status_area.setModel(None)


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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        #self.state_button.setModel(device)
        if device:
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
        else:
            if self.cyclingState:
                self.cyclingState.removeListener(self.handle_cycling_state)
            self.trend.setModel(None)
            self.status_label.setModel(None)

        # Note: the trend is acting a bit strange; it seems like it's
        # polling the value at the "forced reading period" even if
        # it's paused. Setting a low period makes the synoptic
        # sluggish, presumably because of frequent taurus reads. This
        # happens whether the trend is paused or not.

    def handle_cycling_state(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
             self.trend_trigger.emit(evt_value.value)

    def set_trend_paused(self, value):
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

        # self.magnet_tabs = TaurusLazyQTabWidget(self)
        self.magnet_tabs = QtGui.QTabWidget(self)
        vbox.addWidget(self.magnet_tabs)

        self.magnet_field_tables = {}

    def setModel(self, circuit):
        TaurusWidget.setModel(self, circuit)
        for i, (magnet, table) in enumerate(self.magnet_field_tables.items()):
            table.setModel(None)
            self.magnet_tabs.removeTab(i)
        self.magnet_field_tables = {}
        if circuit:
            db = PyTango.Database()
            magnets = db.get_device_property(circuit, "MagnetProxies")["MagnetProxies"]
            models = []
            for magnet in magnets:
                table = AttributeColumnsTable()
                magnet_models = ["%s/fieldA" % magnet,
                                 "%s/fieldB" % magnet,
                                 "%s/fieldAnormalised" % magnet,
                                 "%s/fieldBnormalised" % magnet]
                models.append(magnet_models)
                table.setModel(magnet_models)
                self.magnet_tabs.addTab(table, magnet)
                self.magnet_field_tables[magnet] = table

            self.magnet_tabs.setModel(models)
        else:
            self.magnet_tabs.setModel(None)


class MagnetListPanel(TaurusWidget):

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        label = QtGui.QLabel("All magnets in the circuit.")
        label.setAlignment(QtCore.Qt.AlignCenter)
        vbox.addWidget(label)

        self.table = DeviceRowsTable()
        vbox.addWidget(self.table)

    def setModel(self, circuit):
        print "MagnetListPanel setModel", circuit
        TaurusWidget.setModel(self, circuit)
        db = PyTango.Database()
        if circuit:
            magnets = db.get_device_property(circuit, "MagnetProxies")["MagnetProxies"]
            self.table.setModel(magnets, ["State", "TemperatureInterlock"])
        else:
            self.table.setModel(None)


class TaurusLazyQTabWidget(QtGui.QTabWidget):

    """A tabbed container for multiple Taurus widgets, which "lazily" sets
    the models for each tab when it's first selected.
    """

    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.models = []
        self.currentChanged.connect(self._tab_changed)
        self.current_tab = None

    def setModel(self, models):
        # In order for this to work, each tab must contain just one Taurus
        # widget and the models argument must contain the models for these
        # in the correct order.
        if not models:
            models = []
        self.models = models
        index = self.currentIndex()
        tab = self.widget(index)
        tab.setModel(self.models[index])

    def _tab_changed(self, tab_index):
        "_tab_changed", tab_index
        if self.models:
            tab = self.widget(tab_index)
            if self.current_tab:
                self.current_tab.setModel(None)
            model = self.models[tab_index]
            if not tab.getModel():
                tab.setModel(model)
            self.current_tab = tab


class MagnetPanel(TaurusWidget):

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        tabs = self.tabs = TaurusLazyQTabWidget()
        hbox.addWidget(tabs)

        self.circuit_widget = MagnetCircuitPanel()
        self.circuit_tab = tabs.addTab(self.circuit_widget, "Circuit")

        self.ps_widget = PowerSupplyPanel()
        self.ps_tab = tabs.addTab(self.ps_widget, "Power supply")

        self.magnets_widget = MagnetListPanel()
        self.magnets_tab = tabs.addTab(self.magnets_widget, "Magnets")

        self.cycle_widget = CyclePanel()
        self.cycle_tab = tabs.addTab(self.cycle_widget, "Cycle")

        self.field_widget = FieldPanel()
        self.field_tab = tabs.addTab(self.field_widget, "Field")

        # make the PS tab default for now...
        tabs.setCurrentIndex(self.ps_tab)

        self.resize(700, 400)

    def setModel(self, magnet):
        print "MagnetPanel setModel", magnet
        #TaurusWidget.setModel(self, magnet)
        db = PyTango.Database()
        print "hello"
        if magnet:
            print db.get_device_property(magnet, "CircuitProxies")
            circuit = str(db.get_device_property(
                magnet, "CircuitProxies")["CircuitProxies"][0])
            #self.circuit_widget.setModel(circuit)
            self.setWindowTitle(circuit)
            print "hello again"
            ps = str(db.get_device_property(
                circuit, "PowerSupplyProxy")["PowerSupplyProxy"][0])
            # self.ps_widget.setModel(ps)

            # self.magnets_widget.setModel(circuit)

            # self.cycle_widget.setModel(circuit)

            # self.field_widget.setModel(circuit)
            self.tabs.setModel([circuit, ps, circuit, circuit, circuit])
        else:
            self.circuit_widget.setModel(None)
            self.cycle_widget.setModel(None)
            self.field_widget.setModel(None)
            self.ps_widget.setModel(None)
            self.magnets_widget.setModel(None)
        print "********* magnet DONE"


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
