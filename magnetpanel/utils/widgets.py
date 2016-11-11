try:
    from collections import defaultdict
except ImportError:
    from defaultdict import defaultdict
from math import isnan

from taurus.qt import QtCore, QtGui
from taurus.qt.qtgui.panel import TaurusWidget, TaurusForm
from taurus.qt.qtgui.display import TaurusLabel
from taurus import Attribute
import PyTango


class AttributeColumn(object):

    def __init__(self, parent, column):
        self.parent = parent
        self.column = column

    def event_received(self, *args):
        self.parent.onEvent(self.column, *args)


class TableItem(QtGui.QTableWidgetItem):

    def __init__(self, trigger):
	self.trigger = trigger
        self.value = None
        self.config = None
        self.source = None
        QtGui.QTableWidgetItem.__init__(self)

    @property
    def writable_boolean(self):
        return (self.value is not None and
                self.value.type == PyTango.CmdArgType.DevBoolean and
                self.value.w_value is not None)

    def event_received(self, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                        PyTango.EventType.PERIODIC_EVENT]:
            self.value = evt_value
            self.source = evt_src
            self.trigger.emit(self.row(), self.column())
        if hasattr(evt_value, "format"):
            self.config = evt_value

class AttributeColumnsTable(TaurusWidget):

    """Display several 1D spectrum attributes belonging to the same
    device as columns in a table."""

    trigger = QtCore.pyqtSignal((int, int))

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.table = QtGui.QTableWidget()
        self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        hbox.addWidget(self.table)

        self.trigger.connect(self.updateColumn)
        self.attributes = []
        self._columns = []
        self._values = {}
        self._config = {}

    def setModel(self, attrs):
        if not attrs:
            for att, col in zip(self.attributes, self._columns):
                att and att.removeListener(col.event_received)
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

    def keyPressEvent(self, e):
        "Copy selected cells to the clipboard on Ctrl+C"
        if (e.modifiers() & QtCore.Qt.ControlModifier):
            selected = self.table.selectedRanges()
            if e.key() == QtCore.Qt.Key_C:
                s = ""
                for r in xrange(selected[0].topRow(), selected[0].bottomRow() + 1):
                    for c in xrange(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        try:
                            s += str(self.table.item(r, c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n"  # eliminate last '\t'
                clipboard = QtGui.QApplication.clipboard()
                clipboard.setText(s)

    def onEvent(self, column, evt_src, evt_type, evt_value):
        if evt_type in [PyTango.EventType.CHANGE_EVENT,
                    PyTango.EventType.PERIODIC_EVENT]:
            self._values[column] = evt_value
            self.trigger.emit(column)
        if isinstance(evt_value, PyTango.DeviceAttributeConfig):
            self._config[column] = evt_value

    def updateColumn(self, column):
        if not self._values:
            return  # when does this happen?
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

    trigger = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        TaurusWidget.__init__(self, parent)
        self._setup_ui()

    def _setup_ui(self):
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        self.table = QtGui.QTableWidget(parent=self)

        hbox.addWidget(self.table)

        self.trigger.connect(self.update_item)
        self.table.itemClicked.connect(self.on_item_clicked)

        self._items = {}
        self.attributes = {}

    def keyPressEvent(self, e):
        "Copy selected cells to the clipboard on Ctrl+C"
        if (e.modifiers() & QtCore.Qt.ControlModifier):
            selected = self.table.selectedRanges()
            if e.key() == QtCore.Qt.Key_C:
                s = ""
                for r in xrange(selected[0].topRow(), selected[0].bottomRow() + 1):
                    for c in xrange(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        try:
                            s += str(self.table.item(r, c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n"  # eliminate last '\t'
                clipboard = QtGui.QApplication.clipboard()
                clipboard.setText(s)

    def setModel(self, devices, attributes=[]):
        if not devices:
            for dev, attrs in self.attributes.items():
                for att in attrs:
                    att and att.removeListener(
                        self._items[dev][att.name].event_received)
        else:
            try:
                #TaurusWidget.setModel(self, attrs[0].rsplit("/", 1)[0])
                attrnames = [a[0] if isinstance(a, tuple) else a
                             for a in attributes]
                self.attributes = dict((dev, [Attribute("%s/%s" % (dev, a))
                                              for a in attrnames])
                                       for dev in devices)

                self.table.setColumnCount(len(attributes) + 1)
                colnames = [a[1] if isinstance(a, tuple) else a
                            for a in attributes]
                labels = ["Device"] + colnames
                self.table.setHorizontalHeaderLabels(labels)
                header = self.table.horizontalHeader()
                header.setResizeMode(QtGui.QHeaderView.Stretch)

                # Check if there are any columns at all
                self.table.setRowCount(len(devices))

                for r, (dev, attrs) in enumerate(self.attributes.items()):
                    item = QtGui.QTableWidgetItem(dev)
                    item.setFlags(QtCore.Qt.ItemIsSelectable |
                                  QtCore.Qt.ItemIsEnabled)
                    self.table.setItem(r, 0, item)
                    for c, att in enumerate(attrs, 1):
                        # JFF: this is a workaround for a behavior in Taurus. Just
                        # adding a new listener to each attribute does not work, the
                        # previous ones get removed for some reason.
                        item = TableItem(self.trigger)
                        self.table.setItem(r, c, item)
                        att.addListener(item.event_received)

            except PyTango.DevFailed:
                pass

    def update_item(self, row, column):
        item = self.table.item(row, column)
        value, config = item.value, item.config

        # Set text
        if config and config.format != "Not specified":
            item.setText(config.format % value.value)
        else:
            item.setText(str(value.value))

	# Set flags and state
        if item.writable_boolean:
            item.setFlags(QtCore.Qt.ItemIsSelectable
                          | QtCore.Qt.ItemIsEnabled
                          | QtCore.Qt.ItemIsUserCheckable)
            state = QtCore.Qt.Checked if value.w_value else QtCore.Qt.Unchecked
            item.setCheckState(state)
	else:
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        # Set background color
        if value.type == PyTango.CmdArgType.DevState:
            if value.value in self.STATE_COLORS:
                item.setBackgroundColor(QtGui.QColor(*self.STATE_COLORS[value.value]))


    def on_item_clicked(self, item):
        # Not a writable item
        if not isinstance(item, TableItem) or not item.writable_boolean:
	    return
        button_state = (item.checkState() == QtCore.Qt.Checked)
        value_state = item.value.w_value
        if button_state != value_state:
            item.source.write(button_state)


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
        self.devicename_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        grid.addWidget(self.devicename_label, 0, 1)

        grid.addWidget(QtGui.QLabel("State:"), 1, 0)
        hbox = QtGui.QHBoxLayout(self)
        #self.state_led = TaurusLed()
        #hbox.addWidget(self.state_led)
        self.state_label = TaurusLabel()
        policy = QtGui.QSizePolicy()
        self.state_label.setBgRole("state")
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
        self.status_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
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
            self.status and self.status.removeListener(self.onStatusChange)

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


class TaurusLazyQTabWidget(QtGui.QTabWidget):

    """A tabbed container for multiple Taurus widgets, which "lazily" sets
    the models for each tab when it's first selected.
    """

    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.models = []
        self.currentChanged.connect(self._tab_changed)
        #self.current_tab = None

    def setModel(self, models):
        # In order for this to work, each tab must contain just one Taurus
        # widget and the models argument must contain the models for these
        # in the same order as the tabs.
        index = self.currentIndex()
        tab = self.widget(index)
        if not models:
            self.models = []
            tab.setModel(None)
        else:
            self.models = models
            tab.setModel(self.models[index])

    def _tab_changed(self, tab_index):
        """Callback for when the user swiches tabs. Sets the model on the new
        tab and unsets it on the old."""
        if self.models:
            tab = self.widget(tab_index)
            if tab:
                # if self.current_tab and self.current_tab.getModel():
                #     self.current_tab.setModel(None)
                model = self.models[tab_index]
                if not tab.getModel():
                    tab.setModel(model)
                #self.current_tab = tab


if __name__ == "__main__":
    import sys
    from taurus.qt.qtgui.application import TaurusApplication
    app = TaurusApplication(sys.argv)
    #w = StatusArea()
    w = DevnameAndState()
    w.setModel(sys.argv[1])
    w.show()
    sys.exit(app.exec_())
