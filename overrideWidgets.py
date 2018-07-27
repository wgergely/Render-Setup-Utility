import functools

from PySide2 import QtWidgets

from RenderSetupUtility.config import SHADER_OVERRIDE_OPTIONS, ARNOLD_PROPERTIES
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin


class OverrideWidget(QtWidgets.QWidget, MayaQWidgetBaseMixin):
    PROPERTIES = None
    LABEL = None

    def __init__(self, parent=None):
        super(OverrideWidget, self).__init__(parent=parent)
        self.switchBox = None
        self._createUI()

    def _createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)

        label = QtWidgets.QLabel(self.__class__.LABEL)
        self.switchBox = QtWidgets.QCheckBox()
        self.switchBox.clicked.connect(self.switchBoxClicked)

        row.layout().addWidget(label, 1)
        row.layout().addWidget(self.switchBox, 0)
        self.layout().addWidget(row)

        self._iterateDict()

    def _iterateDict(self):
        for d in self.__class__.PROPERTIES:
            row = QtWidgets.QWidget()
            QtWidgets.QHBoxLayout(row)
            row.layout().setContentsMargins(0, 0, 0, 0)

            label = QtWidgets.QLabel(d['nice'])
            box = QtWidgets.QCheckBox()

            stateChanged = functools.partial(self.checkBoxClicked, data=d)
            box.stateChanged.connect(stateChanged)

            row.layout().addWidget(label, 1)
            row.layout().addWidget(box, 0)
            self.layout().addWidget(row)

    def checkBoxClicked(self, state, data=None):
        raise NotImplementedError('Method is abstract and has to be overriden.')

    def switchBoxClicked(self):
        raise NotImplementedError('Method is abstract and has to be overriden.')


class PropertyOverrideWidget(OverrideWidget):
    """Widget for the proerties overrides."""

    PROPERTIES = ARNOLD_PROPERTIES
    LABEL = 'Apply property overrides'

    def __init__(self, parent=None):
        super(PropertyOverrideWidget, self).__init__(parent=parent)

    def checkBoxClicked(self, state, data=None):
        print state, data

    def switchBoxClicked(self):
        print 'switchBoxClicked'


class ShaderOverrideWidget(OverrideWidget):
    """Widget for the proerties overrides."""

    PROPERTIES = SHADER_OVERRIDE_OPTIONS
    LABEL = 'Apply shader overrides'

    def __init__(self, parent=None):
        super(ShaderOverrideWidget, self).__init__(parent=parent)
        self.comboBox = None

    def _iterateDict(self):
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)

        label = QtWidgets.QLabel('Select:')
        self.comboBox = QtWidgets.QComboBox()
        row.layout().addWidget(label, 1)
        row.layout().addWidget(self.comboBox, 0)
        self.layout().addWidget(row)

        for d in self.__class__.PROPERTIES:
            self.comboBox.addItem(
                d['nice'],
                userData=d
            )
        currentIndexChanged = functools.partial(self.currentIndexChanged, userData=d)
        self.comboBox.currentIndexChanged.connect(currentIndexChanged)

    def currentIndexChanged(self, idx, userData=None):
        print idx, userData

    def switchBoxClicked(self):
        print 'switchBoxClicked'
