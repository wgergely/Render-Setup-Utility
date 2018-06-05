# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413

"""Shaders list widget."""

from PySide2 import QtWidgets, QtCore
from RenderSetupUtility.shaderUtility import ShaderUtility


class ShadersWidget(QtWidgets.QListWidget):
    """The shader list widget."""

    def __init__(self, parent=None):
        super(ShadersWidget, self).__init__(parent=parent)

        for k in ShaderUtility().data:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, k)
            item.setData(QtCore.Qt.UserRole, k)
            self.addItem(item)
