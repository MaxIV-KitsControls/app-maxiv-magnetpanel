# Imports
try:
    from collections import defaultdict
except ImportError:
    from defaultdict import defaultdict
import sys
import PyTango
# Taurus imports
from taurus.qt import QtGui
from taurus.qt.qtgui.panel import TaurusWidget
# MagnetPanel imports
from magnetpanel.utils.widgets import TaurusLazyQTabWidget
from magnetpanel.widget.panels import MagnetCircuitPanel, MagnetListPanel
from magnetpanel.widget.panels import CyclePanel, FieldPanel, PowerSupplyPanel
from magnetpanel.widget.panels import BinpPowerSupplyPanel, SwitchBoardPanel

PERIOD_ARG = "--taurus-polling-period="


def set_polling_period(period):
    """Set the polling period if not defined in sys.argv."""
    for arg in sys.argv:
        if arg.startswith(PERIOD_ARG):
            break
    else:
        sys.argv.append(PERIOD_ARG + str(period))


def make_binpps_panel(widget):
    """ Switch PowerSupplyPanel to BinpPowerSupplyPanel """
    widget.ps_widget = BinpPowerSupplyPanel()
    # remoce previous PS panel
    widget.tabs.removeTab(1)
    # set New one
    widget.ps_tab = widget.tabs.insertTab(1, widget.ps_widget, "Power supply")
    widget.tabs.setCurrentIndex(widget.ps_tab)


class MagnetPanel(TaurusWidget):
    """This is the main panel that collects all the specific widgets above
    into tabs."""

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        # layout
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)
        # tabs
        tabs = self.tabs = TaurusLazyQTabWidget()
        hbox.addWidget(tabs)
        # circuit panel
        self.circuit_widget = MagnetCircuitPanel()
        self.circuit_tab = tabs.addTab(self.circuit_widget, "Circuit")
        # ps panel
        self.ps_widget = PowerSupplyPanel()
        self.ps_tab = tabs.addTab(self.ps_widget, "Power supply")
        # magnet panel
        self.magnets_widget = MagnetListPanel()
        self.magnets_tab = tabs.addTab(self.magnets_widget, "Magnets")
        # cycle panel
        self.cycle_widget = CyclePanel()
        self.cycle_tab = tabs.addTab(self.cycle_widget, "Cycle")
        # field panel
        self.field_widget = FieldPanel()
        self.field_tab = tabs.addTab(self.field_widget, "Field")
        # make the PS tab default for now...
        tabs.setCurrentIndex(self.ps_tab)
        # resize
        self.resize(700, 450)

    def setModel(self, model):
        TaurusWidget.setModel(self, model)
        db = PyTango.Database()
        # get device class
        devclass = db.get_class_for_device(str(model))
        # Devices models from magnet device
        if devclass == "Magnet":
            # get circuit device
            circuit = str(db.get_device_property(
                model, "CircuitProxies")["CircuitProxies"][0])
            self.setWindowTitle("Magnet circuit panel: %s" % circuit)
            # get PS device
            ps = str(db.get_device_property(
                circuit, "PowerSupplyProxy")["PowerSupplyProxy"][0])
            # check PS class
            if db.get_class_for_device(ps) == "PulsePowerSupply":
                # change ps panel to bimp ps panel (for kicker and pinger)
                make_binpps_panel(self)
            # set model
            self.tabs.setModel([circuit, ps, circuit, circuit, circuit])
        # Devices models from circuit device
        elif devclass in ("MagnetCircuit", "TrimCircuit"):
            ps = str(db.get_device_property(
                model, "PowerSupplyProxy")["PowerSupplyProxy"][0])
            if db.get_class_for_device(ps) == "PulsePowerSupply":
                make_binpps_panel(self)
            self.tabs.setModel([model, ps, model, model, model])
        else:
            self.circuit_widget.setModel(None)
            self.cycle_widget.setModel(None)
            self.field_widget.setModel(None)
            self.ps_widget.setModel(None)
            self.magnets_widget.setModel(None)


class TrimCoilCircuitPanel(TaurusWidget):
    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        # layout
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)
        # tabs
        tabs = self.tabs = TaurusLazyQTabWidget()
        hbox.addWidget(tabs)
        # magnet
        self.circuit_widget = MagnetCircuitPanel()
        self.circuit_tab = tabs.addTab(self.circuit_widget, "Circuit")
        # ps
        self.ps_widget = PowerSupplyPanel()
        self.ps_tab = tabs.addTab(self.ps_widget, "Power supply")
        # magnet
        self.magnets_widget = MagnetListPanel()
        self.magnets_tab = tabs.addTab(self.magnets_widget, "Magnets")
        # field
        self.field_widget = FieldPanel()
        self.field_tab = tabs.addTab(self.field_widget, "Field")
        # switchboard
        self.switchboard_widget = SwitchBoardPanel()
        tab = tabs.addTab(self.switchboard_widget, "Switchboard")
        self.switchboard_tab = tab
        # make the PS tab default for now...
        tabs.setCurrentIndex(self.ps_tab)
        self.resize(700, 400)

    def setModel(self, trim):
        TaurusWidget.setModel(self, trim)
        db = PyTango.Database()
        if trim:
            self.setWindowTitle("Trim coil panel: %s" % trim)
            swb = str(db.get_device_property(
                trim, "SwitchBoardProxy")["SwitchBoardProxy"][0])
            ps = str(db.get_device_property(
                trim, "PowerSupplyProxy")["PowerSupplyProxy"][0])
            # check PS class
            if db.get_class_for_device(ps) == "PulsePowerSupply":
                # change ps panel to bimp ps panel (for kicker and pinger)
                make_binpps_panel(self)
            # set model
            self.tabs.setModel([trim, ps, trim, trim, swb])
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

    set_polling_period(1000)
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
