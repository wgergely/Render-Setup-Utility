# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413
"""Shaders model.

Attributes

"""
from PySide2 import QtCore
from RenderSetupUtility.main.shaderUtility import ShaderUtility


class Node(object):
    """Class for displaying and navigating information in a tree hierarchy.

    Attributes:
        database (Database): Database interface instance.
        base (Base): The associated base object.

    """

    def __init__(self, name, parentNode=None):
        """__init__ method.

        Attributes:
            name (str): The name of the shader.
            parentNode (Node): the parent of this node.

        """
        super(Node, self).__init__()
        self._name = name
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    @property
    def name(self):
        """The name of this node."""
        return self._name

    def removeSelf(self):
        """Removes itself from the parent's children."""
        if self.parentNode:
            if self in self.parentNode.children:
                idx = self.parentNode.children.index(self)
                del self.parentNode.children[idx]

    def removeChild(self, child):
        """Remove the given node from the children."""
        if child in self.children:
            idx = self.children.index(child)
            del self.children[idx]

    def addChild(self, child):
        """Add a child node."""
        self.children.append(child)

    @property
    def children(self):
        """Children of the node."""
        return self._children

    @property
    def childCount(self):
        """Children of the this node."""
        return len(self._children)

    @property
    def parentNode(self):
        """Parent of this node."""
        return self._parentNode

    @parentNode.setter
    def parentNode(self, node):
        self._parentNode = node

    def getChild(self, row):
        """Child at the provided index/row."""
        if row < self.childCount:
            return self.children[row]
        return None

    @property
    def row(self):
        """Row number of this node."""
        if self.parentNode:
            return self.parentNode.children.index(self)
        return None

    @property
    def nodeType(self):
        """Class name."""
        return self.__class__.__name__


class ShadersModel(QtCore.QAbstractItemModel):
    """Base-class for a static, single-column model.

    It defines all attributes and methods needed to
    manage a tree-hierarchy."""

    COLUMN_COUNT = 1

    def __init__(self, rootNode=None, parent=None):
        super(ShadersModel, self).__init__(parent=parent)
        if not rootNode:
            rootNode = Node('rootNode')
        self._rootNode = rootNode

        self.shaderUtility = ShaderUtility()
        for k in self.shaderUtility.data:
            Node(self.shaderUtility.data[k], parentNode=self._rootNode)

    @property
    def rootNode(self):
        """ The current root node of the model """
        return self._rootNode

    @rootNode.setter
    def rootNode(self, node):
        """ The current root node of the model """
        self._rootNode = node

    def rowCount(self, parent):
        """Row count."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount

    def columnCount(self, parent):  # pylint: disable=W0613
        """Column count."""
        return self.__class__.COLUMN_COUNT

    def parent(self, index):
        """The parent of the node."""
        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        parentNode = node.parentNode

        if not parentNode:
            return QtCore.QModelIndex()
        elif parentNode == self.rootNode:
            return QtCore.QModelIndex()
        elif parentNode == self.originalRootNode:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row, 0, parentNode)

    def index(self, row, column, parent):
        """Returns a QModelIndex()."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()

        childItem = parentNode.getChild(row)
        if not childItem:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def data(self, index, role):  # pylint: disable=W0613, R0201
        """Name data."""
        if not index.isValid():
            return None
        node = index.internalPointer()
        return node.name

    def sortData(self, reverse):
        """ Sort the data of the model based on the given key """
        parent = self.rootNode

        def sort(parent):
            """ recursive sort """
            parent.children.sort(key=lambda x: x.name, reverse=reverse)
            for child in (f for f in parent.children):
                child.children.sort(key=lambda x: x.name, reverse=reverse)
                sort(child)
        sort(parent)

    def headerData(self, section, orientation, role):  # pylint: disable=W0613, R0201
        """Static header data."""
        return 'ShaderName'
