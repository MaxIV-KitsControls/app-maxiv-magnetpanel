from collections import defaultdict

from taurus.external.qt import QtCore
from taurus.qt.qtgui.container import TaurusWidget
from taurus.qt.qtgui.util import UILoadable

from magnetpanel.resource import rc_switchboard

# silence pep8 unused import warning
assert rc_switchboard

SEXTUPOLE_MODES = {
    "SEXTUPOLE":         ":/sextupole/sextupole.svg",
    "NORMAL_QUADRUPOLE": ":/sextupole/quadrupole.svg",
    "SKEW_QUADRUPOLE":   ":/sextupole/skew_quadrupole.svg",
    "X_CORRECTOR":       ":/sextupole/horizontal_steerer.svg",
    "Y_CORRECTOR":       ":/sextupole/vertical_steerer.svg"
}

OCTUPOLE_MODES = {
    "NORMAL_QUADRUPOLE": ":/octupole/quadrupole.svg",
    "SKEW_QUADRUPOLE":   ":/octupole/skew_quadrupole.svg",
    "X_CORRECTOR":       ":/octupole/horizontal_steerer.svg",
    "Y_CORRECTOR":       ":/octupole/vertical_steerer.svg",
}

BOARD_MODES = {
    "SEXTUPOLE": defaultdict(lambda: ":/sextupole/all_off.svg", SEXTUPOLE_MODES),
    "OCTUPOLE":  defaultdict(lambda: ":/octupole/all_off.svg", OCTUPOLE_MODES)
}


@UILoadable()
class SwitchBoardPanel(TaurusWidget):
    modeChanged = QtCore.pyqtSignal()
    typeChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(TaurusWidget, self).__init__(parent)

        self.loadUi()

        self.statusLabel.setUseParentModel(True)
        self.statusLabel.setModel("/Status")

        self.modeCB.setUseParentModel(True)
        self.modeCB.setModel("/Mode")

        self.type_attribute = None
        self.mode_attribute = None
        self.type_value = None
        self.mode_value = None

        self.modelChanged.connect(self.onModelChanged)
        self.modeChanged.connect(self.onModeChanged)
        self.typeChanged.connect(self.onTypeChanged)

    def eventReceived(self, evt_src, evt_type, evt_value):
        if not hasattr(evt_value, "rvalue"):
            return

        # We can"t interact with QWidgets from here
        # (calling thread is not a QThread). Emit signals instead.
        if evt_src is self.type_attribute and \
           evt_value.rvalue != self.type_value:
            self.type_value = evt_value.rvalue
            self.typeChanged.emit()

        if evt_src is self.mode_attribute and \
           evt_value.rvalue != self.mode_value:
            self.mode_value = evt_value.rvalue
            self.modeChanged.emit()

    def onModelChanged(self, model):
        if self.mode_attribute:
            self.mode_attribute.removeListener(self)
            self.mode_attribute = None
        if self.type_attribute:
            self.type_attribute.removeListener(self)
            self.type_attribute = None

        device = self.getModelObj()
        if device:
            self.mode_attribute = device.getAttribute("Mode")
            self.mode_attribute.addListener(self)
            self.type_attribute = device.getAttribute("Type")
            self.type_attribute.addListener(self)

    def onTypeChanged(self):
        # fetch list of valid mode names
        device = self.getModelObj()
        if device:
            modes = device.command_inout("getAttrStringValueList", "Mode")
        else:
            modes = []
        # update combo box
        choices = [(m, m) for m in modes]
        self.modeCB.setValueNames(choices)
        # update image
        self.onModeChanged()

    def onModeChanged(self):
        # update image
        image_map = BOARD_MODES.get(self.type_value)
        if image_map:
            svg = image_map[self.mode_value]
        else:
            svg = ":/unknown.svg"
        self.svgWidget.load(svg)


def main():
    import sys
    from taurus.core.util import argparse
    from taurus.qt.qtgui.application import TaurusApplication

    parser = argparse.get_taurus_parser()
    parser.usage = "%prog [options] <device>"

    app = TaurusApplication(cmd_line_parser=parser)
    args = app.get_command_line_args()

    if len(args) < 1:
        parser.print_usage()
        sys.exit(1)

    model = args[0]

    w = SwitchBoardPanel()
    w.setModel(model)
    w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
