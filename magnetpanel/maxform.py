from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.input import TaurusValueLineEdit
#from maxwidgets.input import MAXLineEdit
from maxlineedit import MAXLineEdit


class MAXForm(TaurusForm):
    """
    A TaurusForm adapted for MAX-IV needs. It is user-modifiable by default,
    which is useful when the form is part of a TaurusGUI. The form will use
    custom TaurusValue widgets for som commonly used device classes.
    """

    widgetMap = {'GammaSPCe': ('maxwidgets.panel.GammaSPCeTV', (), {})}

    def __init__(self, *args, **kwargs):
        if 'withButtons' not in kwargs:
            kwargs['withButtons'] = False

        TaurusForm.__init__(self, *args, **kwargs)
        self.setModifiableByUser(True)
        self.setCustomWidgetMap(self.widgetMap)

    def setModel(self, model):

        TaurusForm.setModel(self, model)

        # a hack to replace taurus lineedit widgets with ours...
        for widget in self:
            if isinstance(widget.writeWidget(), TaurusValueLineEdit):
                widget.writeWidgetClass = MAXLineEdit
                widget.writeWidget().setAutoApply(True)
                widget.writeWidget().setForcedApply(True)
                widget.writeWidget().setEnableWheelEvent(True)

    def setFontSize(self, size):
        self.setStyleSheet('QLabel,QLineEdit {font-size: %dpt;}' % size)

        # for widget in self:
        #     print "setFontSize", size, widget
        #     if widget.writeWidget():
        #         font = widget.writeWidget().font()
        #         font.setPointSize(size)
        #         widget.writeWidget().setFont(font)

        #     if widget.readWidget():
        #         widget.readWidget()\
        #.setStyleSheet('QLabel {font-size: %dpt;}' % size)


def main():
    import sys
    from taurus.core.util import argparse
    from taurus.qt.qtgui.application import TaurusApplication

    parser = argparse.get_taurus_parser()
    parser.set_usage("%prog [options] [model1 [model2 ...]]")

    app = TaurusApplication(cmd_line_parser=parser)

    args = app.get_command_line_args()
    if not args:
        parser.print_usage()
        sys.exit(1)

    form = MAXForm()
    form.setModel(args)
    form.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
