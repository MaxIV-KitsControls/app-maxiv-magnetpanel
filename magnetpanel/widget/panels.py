try:
    from collections import defaultdict
except ImportError:
    from defaultdict import defaultdict

import sys
import PyTango

from taurus.qt import QtCore, QtGui
from taurus import Attribute

from taurus.qt.qtgui.panel import TaurusWidget
from taurus.qt.qtgui.display import TaurusLabel
from taurus.qt.qtgui.button import TaurusCommandButton
from taurus.qt.qtgui.plot import TaurusTrend
from maxwidgets.display import MAXValueBar
from magnetpanel.utils.maxfrom import MAXForm
from magnetpanel.utils.switchboard import SwitchBoardPanel
from magnetpanel.utils.widgets import (AttributeColumnsTable, DeviceRowsTable,
                     DevnameAndState, StatusArea, TaurusLazyQTabWidget)


class BinpPowerSupplyPanel(TaurusWidget):
    "Allows directly controlling the BINP power supply connected to the circuit"
    attrs = ["currentSetPoint", "Voltage"]

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)
        form_vbox = QtGui.QVBoxLayout(self)

        # devicename label
        hbox2 = QtGui.QVBoxLayout(self)
        self.device_and_state = DevnameAndState(self)
        hbox2.addWidget(self.device_and_state, stretch=2)

        # commands
        commandbox = QtGui.QHBoxLayout(self)
        self.start_button = TaurusCommandButton(command="Start")
        self.start_button.setUseParentModel(True)
        self.stop_button = TaurusCommandButton(command="Stop")
        self.stop_button.setUseParentModel(True)
        self.init_button = TaurusCommandButton(command="Init")
        self.init_button.setUseParentModel(True)
        self.on_button = TaurusCommandButton(command="On")
        self.on_button.setUseParentModel(True)
        self.off_button = TaurusCommandButton(command="Off")
        self.off_button.setUseParentModel(True)
        self.enable_trigger_button = TaurusCommandButton(command="EnableTrigger")
        self.enable_trigger_button.setUseParentModel(True)
        self.disable_trigger_button = TaurusCommandButton(command="DisableTrigger")
        self.disable_trigger_button.setUseParentModel(True)
        self.reset_button = TaurusCommandButton(command="Reset")
        self.reset_trigger_button.setUseParentModel(True)
        commandbox.addWidget(self.start_button)
        commandbox.addWidget(self.stop_button)
        commandbox.addWidget(self.init_button)
        commandbox.addWidget(self.on_button)
        commandbox.addWidget(self.off_button)
        commandbox.addWidget(self.enable_trigger_button)
        commandbox.addWidget(self.disable_trigger_button)
        commandbox.addWidget(self.reset_button)
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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        self.status_area.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])
            attrname = "%s/%s" % (device, "Current")
            self.valuebar.setModel(attrname)
            # self.state_button.setModel(device)
            attr = Attribute(attrname)
            self.current_label.setText("%s [%s]" % (attr.label, attr.unit))
        else:
            self.form.setModel(None)
            self.valuebar.setModel(None)

class PowerSupplyPanel(TaurusWidget):
    "Allows directly controlling the power supply connected to the circuit"
    attrs = ["Current", "Voltage", "Resistance"]

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)
        form_vbox = QtGui.QVBoxLayout(self)

        # devicename label
        hbox2 = QtGui.QVBoxLayout(self)
        self.device_and_state = DevnameAndState(self)
        hbox2.addWidget(self.device_and_state, stretch=2)

        # commands
        commandbox = QtGui.QHBoxLayout(self)
        self.start_button = TaurusCommandButton(command="On")
        self.start_button.setUseParentModel(True)
        self.stop_button = TaurusCommandButton(command="Off")
        self.stop_button.setUseParentModel(True)
        self.init_button = TaurusCommandButton(command="Init")
        self.init_button.setUseParentModel(True)
        commandbox.addWidget(self.start_button)
        commandbox.addWidget(self.stop_button)
        commandbox.addWidget(self.init_button)
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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        self.status_area.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])
            attrname = "%s/%s" % (device, "Current")
            self.valuebar.setModel(attrname)
            # self.state_button.setModel(device)
            attr = Attribute(attrname)
            self.current_label.setText("%s [%s]" % (attr.label, attr.unit))
        else:
            self.form.setModel(None)
            self.valuebar.setModel(None)


class MagnetCircuitPanel(TaurusWidget):
    "Displays the important attributes of the circuit device"

    attrs = ["energy", "MainFieldComponent", "PowerSupplyReadValue", "PowerSupplySetPoint",
             "fixNormFieldOnEnergyChange"]

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):

        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        form_vbox = QtGui.QVBoxLayout(self)

        hbox2 = QtGui.QVBoxLayout(self)
        self.device_and_state = DevnameAndState(self)
        hbox2.addWidget(self.device_and_state)
        self.magnet_type_label = QtGui.QLabel("Magnet type:")
        hbox2.addWidget(self.magnet_type_label)
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
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        self.device_and_state.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])
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
    "Panel for controlling the cycling functionality"

    trend_trigger = QtCore.pyqtSignal(bool)

    attrs = ["CyclingTimePlateau", "CyclingIterations", "CyclingSteps",
             "CyclingRampTime", "NominalSetPoint"]
    scale_factor = 1.1

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def scaleSize(self):
        size = self.form.scrollArea.widget().frameSize()
        return QtCore.QSize(size.width(), size.height() * self.scale_factor)

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        grid = QtGui.QGridLayout()
        self.form = MAXForm(withButtons=False)

        grid.addWidget(self.form, 0, 0, 2, 1)
        # rescale taurus form methode
        self.form.scrollArea.sizeHint = self.scaleSize
        self.status_label = StatusArea()
        grid.addWidget(self.status_label, 0, 1, 1, 1)

        commandbox = QtGui.QVBoxLayout(self)
        self.start_button = TaurusCommandButton(command="StartCycle")
        self.start_button.setUseParentModel(True)
        self.stop_button = TaurusCommandButton(command="StopCycle")
        self.stop_button.setUseParentModel(True)
        commandbox.addWidget(self.start_button)
        commandbox.addWidget(self.stop_button)
        grid.addLayout(commandbox, 1, 1, 1, 1)

        vbox.addLayout(grid)

        self.trend = TaurusTrend()
        vbox.addWidget(self.trend, stretch=1)
        self.trend_trigger.connect(self.set_trend_paused)

        self.cyclingState = None

    def setModel(self, device):
        print self.__class__.__name__, "setModel", device
        TaurusWidget.setModel(self, device)
        # self.state_button.setModel(device)
        if device:
            self.form.setModel(["%s/%s" % (device, attribute)
                                for attribute in self.attrs])

            self.status_label.setModel("%s/cyclingStatus" % device)

            ps = str(PyTango.Database().get_device_property(
                device, "PowerSupplyProxy")["PowerSupplyProxy"][0])

            self.trend.setPaused()
            self.trend.setModel(["%s/Current" % ps])
            self.trend.setForcedReadingPeriod(0.2)
            self.trend.showLegend(True)

            # let's pause the trend when not cycling
            self.cyclingState = self.getModelObj().getAttribute("cyclingState")
            self.cyclingState.addListener(self.handle_cycling_state)
        else:
            if self.cyclingState:
                self.cyclingState.removeListener(self.handle_cycling_state)
            self.trend.setModel(None)
            self.status_label.setModel(None)

    def handle_cycling_state(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            self.trend_trigger.emit(evt_value.value)

    def set_trend_paused(self, value):
        self.trend.setForcedReadingPeriod(0.2 if value else -1)
        self.trend.setPaused(not value)


class FieldPanel(TaurusWidget):
    """Shows the field components for one of the magnets in the circuit in
    a table. The user can select which magnet using a dropdown."""

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        hbox = QtGui.QHBoxLayout(self)
        label = QtGui.QLabel("Magnetic field components", parent=self)
        label.setAlignment(QtCore.Qt.AlignCenter)
        hbox.addWidget(label)

        # the dropdown to select which magnet's fields to show
        self.magnet_combobox = QtGui.QComboBox(parent=self)
        self.magnet_combobox.currentIndexChanged.connect(self._magnet_selected)
        hbox.addWidget(self.magnet_combobox)
        vbox.addLayout(hbox)

        # the actual field table for the chosen magnet
        self.table = AttributeColumnsTable(parent=self)
        vbox.addWidget(self.table)

    @QtCore.pyqtSlot(str)
    def _magnet_selected(self, i):
        magnet = self.magnet_combobox.itemText(i)
        if magnet:
            magnet_models = ["%s/fieldA" % magnet,
                             "%s/fieldB" % magnet,
                             "%s/fieldAnormalised" % magnet,
                             "%s/fieldBnormalised" % magnet]
            self.table.setModel(magnet_models)

    def setModel(self, circuit, magnet=None):
        TaurusWidget.setModel(self, circuit)
        if circuit is None:
            self.magnet_combobox.clear()
            self.table.setModel(None)
        else:
            db = PyTango.Database()
            magnets = db.get_device_property(circuit, "MagnetProxies")["MagnetProxies"]
            self.magnet_combobox.addItems(magnets)


class MagnetListPanel(TaurusWidget):
    "Shows all magnets in the circuit, with state and interlocks, in a table"

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)

        label = QtGui.QLabel("All magnets in the circuit")
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
