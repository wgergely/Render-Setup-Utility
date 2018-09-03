# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413

"""RenderSetupUtility widget definition."""


##############################################
# from PySide2 import QtCore
# if not QtCore.QCoreApplication.instance():
from RenderSetupUtility.mayaStandaloneContext import initialize
initialize()
from RenderSetupUtility.mayaStandaloneContext import app
    # reload(QtCore)
###############################################


from PySide2 import QtCore, QtGui, QtWidgets
from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from RenderSetupUtility.overrideWidgets import ShaderOverrideWidget, PropertyOverrideWidget
from RenderSetupUtility.shadersWidget import ShadersWidget


class RenderSetupUtilityWindow(QtWidgets.QWidget, MayaQWidgetDockableMixin):
    """The main RenderSetupUtility widget."""

    _instance = None
    BUTTON_SIZE = 22
    MARGIN = 6

    @property
    def __name__(self):
        """Name of the widget."""
        return self.__class__.__name__

    def __repr__(self):
        return '<{} (singleton instance)>'.format(self.__name__)

    def __new__(cls, *awrgs, **kwargs):
        if not cls._instance:
            cls._instance = super(RenderSetupUtilityWindow, cls).__new__(
                cls, *awrgs, **kwargs)
            cls._instance.__initialized__ = False
        else:
            cls._instance.__initialized__ = True
        return cls._instance

    def __init__(self, parent=None):
        """Init method with singleton break."""
        if hasattr(self, '__initialized__'):
            if self.__initialized__:
                return
        super(RenderSetupUtilityWindow, self).__init__(parent=parent)

        self._addLayerButton = None
        self._activeLayer = None
        self._visibleLayer = None
        self._renderSetupButton = None
        self._addCollectionButton = None
        self._removeCollectionButton = None
        self._selectShapesButton = None
        self._renameShaderButton = None
        self._duplicateShaderButton = None
        self._refreshButton = None
        self._searchField = None
        self._searchGroups = None
        self._shadersWidget = None
        self._propertyOverrideWidget = None
        self._shaderOverrideWidget = None

        self._createUI()
        self._connectSignals()

    @property
    def TEXT_BUTTON_WIDTH(self):
        """Width of and icon button including the margin."""
        return self.__class__.BUTTON_SIZE * 3 + self.__class__.MARGIN

    @property
    def ICON_BUTTON_WIDTH(self):
        """Width of and icon button including the margin."""
        return self.__class__.BUTTON_SIZE + self.__class__.MARGIN

    def _createUI(self):
        """Create the layout."""

        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum
        )

        # Row1
        row1 = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row1)
        row1.layout().setContentsMargins(0, 0, 0, 0)

        self._addLayerButton = QtWidgets.QPushButton('+')
        self._addLayerButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        label = QtWidgets.QLabel('Active layer')
        self._activeLayer = QtWidgets.QComboBox()
        self._renderSetupButton = QtWidgets.QPushButton('RS')
        self._renderSetupButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        row1.layout().addWidget(self._addLayerButton, 0)
        row1.layout().addWidget(label, 0)
        row1.layout().addWidget(self._activeLayer, 1)
        row1.layout().addWidget(self._renderSetupButton, 0)

        # Row2
        row2 = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row2)
        row2.layout().setContentsMargins(0, 0, 0, 0)

        self._visibleLayer = QtWidgets.QComboBox()
        label = QtWidgets.QLabel('Visible layer')

        row2.layout().addSpacing(self.ICON_BUTTON_WIDTH)
        row2.layout().addWidget(label, 0)
        row2.layout().addWidget(self._visibleLayer, 1)
        row2.layout().addSpacing(self.ICON_BUTTON_WIDTH)

        # Row3
        row3 = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row3)
        row3.layout().setContentsMargins(0, 0, 0, 0)

        self._addCollectionButton = QtWidgets.QPushButton('Add')
        self._addCollectionButton.setFixedSize(
            self.__class__.BUTTON_SIZE * 3,
            self.__class__.BUTTON_SIZE
        )

        self._removeCollectionButton = QtWidgets.QPushButton('Remove')
        self._removeCollectionButton.setFixedSize(
            self.__class__.BUTTON_SIZE * 3,
            self.__class__.BUTTON_SIZE
        )

        self._selectShapesButton = QtWidgets.QPushButton('Select shapes')
        self._selectShapesButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        self._renameShaderButton = QtWidgets.QPushButton('Rename')
        self._renameShaderButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        self._duplicateShaderButton = QtWidgets.QPushButton('Duplicate')
        self._duplicateShaderButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        self._refreshButton = QtWidgets.QPushButton('Refresh')
        self._refreshButton.setFixedSize(
            self.__class__.BUTTON_SIZE,
            self.__class__.BUTTON_SIZE
        )

        row3.layout().addWidget(self._addCollectionButton, 0)
        row3.layout().addWidget(self._removeCollectionButton, 0)
        row3.layout().addStretch()
        row3.layout().addWidget(self._selectShapesButton, 0)
        row3.layout().addWidget(self._renameShaderButton, 0)
        row3.layout().addWidget(self._duplicateShaderButton, 0)
        row3.layout().addWidget(self._refreshButton, 0)

        # row4
        row4 = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row4)
        row4.layout().setContentsMargins(0, 0, 0, 0)

        self._searchField = QtWidgets.QLineEdit()
        self._searchField.setPlaceholderText('Search')
        self._searchGroups = QtWidgets.QComboBox()
        row4.layout().addWidget(self._searchField)
        row4.layout().addWidget(self._searchGroups)

        self.layout().addWidget(row1, 0)
        self.layout().addWidget(row2, 0)
        self.layout().addWidget(row3, 0)
        self.layout().addWidget(row4, 0)
        self.layout().addStretch()

        # row5 : ListView
        self._shadersWidget = ShadersWidget()
        self.layout().addWidget(self._shadersWidget)

        # row6: Arnold Properties
        self._propertyOverrideWidget = PropertyOverrideWidget()
        self.layout().addWidget(self._propertyOverrideWidget)

        # row6: Arnold Properties
        self._shaderOverrideWidget = ShaderOverrideWidget()
        self.layout().addWidget(self._shaderOverrideWidget)


    def _connectSignals(self):
        """Connects the qt signals."""
        self._addLayerButton.pressed.connect(
            self.addLayerButtonPressed
        )
        self._activeLayer.currentIndexChanged.connect(
            self.activeLayerCurrentIndexChanged
        )
        self._visibleLayer.currentIndexChanged.connect(
            self.visibleLayerCurrentIndexChanged
        )
        self._renderSetupButton.pressed.connect(
            self.renderSetupButtonPressed
        )
        self._addCollectionButton.pressed.connect(
            self.addCollectionButtonPressed
        )
        self._removeCollectionButton.pressed.connect(
            self.removeCollectionButtonPressed
        )
        self._selectShapesButton.pressed.connect(
            self.selectShapesButtonPressed
        )
        self._renameShaderButton.pressed.connect(
            self.renameShaderButtonPressed
        )
        self._duplicateShaderButton.pressed.connect(
            self.duplicateShaderButtonPressed
        )
        self._refreshButton.pressed.connect(
            self.refreshButtonPressed
        )
        self._searchField.returnPressed.connect(
            self.searchFieldReturnPressed
        )
        self._searchGroups.currentIndexChanged.connect(
            self.searchGroupsCurrentIndexChanged
        )

    def addLayerButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'addLayerButtonPressed'

    def renderSetupButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'renderSetupButtonPressed'

    def addCollectionButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'addCollectionButtonPressed'

    def removeCollectionButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'removeCollectionButtonPressed'

    def selectShapesButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'selectShapesButtonPressed'

    def renameShaderButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'renameShaderButtonPressed'

    def duplicateShaderButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'duplicateShaderButtonPressed'

    def refreshButtonPressed(self):
        """Action to perform when the button is pressed."""
        print 'refreshButtonPressed'

    def searchFieldReturnPressed(self):
        """Action to perform when the search button is pressed."""
        print 'searchFieldReturnPressed'

    def searchGroupsCurrentIndexChanged(self):
        """Action to perform when the search button is pressed."""
        print 'searchFieldReturnPressed'

    def visibleLayerCurrentIndexChanged(self):
        """Action to perform when the visible layer is changed."""
        print 'visibleLayerCurrentIndexChanged'

    def activeLayerCurrentIndexChanged(self):
        """Action to perform when the active layer is changed."""
        print 'activeLayerCurrentIndexChanged'


if __name__ == '__main__':
    app.w = RenderSetupUtilityWindow()
    app.w.show()
    app.exec_()
