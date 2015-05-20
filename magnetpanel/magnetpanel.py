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
from switchboard import SwitchBoardPanel
from widgets import (AttributeColumnsTable, DeviceRowsTable,
                     DevnameAndState, StatusArea, TaurusLazyQTabWidget)


# TODO: investigate setDisconnectOnHide()? Does not seem to work as I hoped...


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

    "Displays the important attributes of the circuit device"

    attrs = ["energy", "MainFieldComponent", "currentActual", "currentSet",
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

    "Panel for controlling the cycling functionality"

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

        commandbox = QtGui.QVBoxLayout(self)
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

        self.cyclingState = None

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


class MagnetPanel(TaurusWidget):

    """This is the main panel that collects all the specific widgets above
    into tabs."""

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

        self.resize(700, 450)

    def setModel(self, magnet):
        print "MagnetPanel setModel", magnet
        TaurusWidget.setModel(self, magnet)
        db = PyTango.Database()
        if magnet:
            circuit = str(db.get_device_property(
                magnet, "CircuitProxies")["CircuitProxies"][0])
            #self.circuit_widget.setModel(circuit)
            self.setWindowTitle("Magnet circuit panel: %s" % circuit)
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


class TrimCoilCircuitPanel(TaurusWidget):

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

        self.field_widget = FieldPanel()
        self.field_tab = tabs.addTab(self.field_widget, "Field")

        self.switchboard_widget = SwitchBoardPanel()
        self.switchboard_tab = tabs.addTab(self.switchboard_widget, "Switchboard")

        # make the PS tab default for now...
        tabs.setCurrentIndex(self.ps_tab)

        self.resize(700, 400)

    def setModel(self, trimcircuit):
        TaurusWidget.setModel(self, trimcircuit)
        db = PyTango.Database()
        if trimcircuit:
            self.setWindowTitle("Trim coil panel: %s" % trimcircuit)
            swb = str(db.get_device_property(
                trimcircuit, "SwitchBoardProxy")["SwitchBoardProxy"][0])
            ps = str(db.get_device_property(
                trimcircuit, "PowerSupplyProxy")["PowerSupplyProxy"][0])
            self.tabs.setModel([trimcircuit, ps, trimcircuit, trimcircuit, swb])
        else:
            self.setWindowTitle("N/A")
            self.circuit_widget.setModel(None)
            # self.cycle_widget.setModel(None)
            self.field_widget.setModel(None)
            self.ps_widget.setModel(None)
            self.magnets_widget.setModel(None)
            self.switchboard_widget.setModel(None)


def magnet_main():
    from taurus.qt.qtgui.application import TaurusApplication
    import sys

    app = TaurusApplication(sys.argv)
    args = app.get_command_line_args()

    w = MagnetPanel()
    # w = TrimCoilCircuitPanel()

    if len(args) > 0:
        w.setModel(args[0])
    app.setCursorFlashTime(0)

    w.show()
    sys.exit(app.exec_())

def trimcoil_main():
    from taurus.qt.qtgui.application import TaurusApplication
    import sys

    app = TaurusApplication(sys.argv)
    args = app.get_command_line_args()

    w = TrimCoilCircuitPanel()

    if len(args) > 0:
        w.setModel(args[0])
    app.setCursorFlashTime(0)

    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    magnet_main()
