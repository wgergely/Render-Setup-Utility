# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413

"""Shaders list widget."""

from PySide2 import QtWidgets, QtCore
from maya import cmds
from RenderSetupUtility.shaderUtility import ShaderUtility


class ShadersWidget(QtWidgets.QListWidget):
    """The shader list widget."""

    def __init__(self, parent=None):
        super(ShadersWidget, self).__init__(parent=parent)
        self.su = ShaderUtility()
        self._delegate = None
        self.setMouseTracking(True)

    def showEvent(self, event):
        self.su.update()
        self.updateItems()

    def updateIfSceneChanged(self):
        """Updates the widget items if the scene changed."""
        self.su.update()
        self.updateItems()

    def enterEvent(self, event):
        self.su.update()
        self.updateItems()

    def updateItems(self):
        """Updates the list of shaders."""
        self.clear()
        for k in self.su.data:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, '{} ({})'.format(k, self.su.data[k]['count']))
            item.setData(QtCore.Qt.UserRole, k)
            self.addItem(item)
