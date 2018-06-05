# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413

"""Shaders list widget."""

from PySide2 import QtWidgets
from RenderSetupUtility._dev.model import ShadersModel
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin


class ShadersWidget(MayaQWidgetBaseMixin, QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(ShadersWidget, self).__init__(parent=parent)
        # QtWidgets.QListView.__init__(self, parent=parent)
        # MayaQWidgetBaseMixin.__init__(self)
        self.setModel(ShadersModel(parent=self))
        self.setRootIndex(self.model().createIndex(0, 0, self.model().rootNode))
        rootNode = self.rootIndex().internalPointer()
