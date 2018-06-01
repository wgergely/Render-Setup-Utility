
class WindowStyle(QtWidgets.QStyledItemDelegate):
    """
    Custom ui and delegate for model.
    """

    ROW_HEIGHT = 30
    FONT_PIXEL_SIZE = 11
    FONT_PIXEL_SIZE_OFFSET = (((ROW_HEIGHT / 2)) / 2) + 2
    ROW_WIDTH = WINDOW_WIDTH - (FRAME_MARGIN[0] * 2) - 6

    def __init__(self, parent=None, *args):
        super(WindowStyle, self).__init__(parent=parent)
        # QtWidgets.QStyledItemDelegate.__init__(self, parent=parent, *args)

        self.warningIcon = tempfile.gettempdir() + '\RS_warning.png'
        cmds.resourceManager(saveAs=['RS_warning.png', self.warningIcon])
        self.shaderOverrideIcon = tempfile.gettempdir() + '\out_shadingEngine.png'
        cmds.resourceManager(
            saveAs=['out_shadingEngine.png', self.shaderOverrideIcon])

    def sizeHint(self, option, index):
        return QtCore.QSize(self.__class__.ROW_WIDTH, self.__class__.ROW_HEIGHT)

    def paint(self, painter, option, index):
        """
        Main paint function for the Render Setup Utility
        """

        q.getQItem('%s_ShaderScrollList' % (windowID), QtWidgets.QListWidget)

        # Reset pen
        painter.save()
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        # Set font
        font = QtGui.QFont()
        font.setFamily('Segoe UI')
        font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
        font.setItalic(False)
        painter.setFont(font)

        # UI Properties
        leadRectangleWidth = 4
        textSpacer = 4
        leadTextMargin = (leadRectangleWidth * 2) + textSpacer

        # Items
        allItems = cmds.textScrollList('%s_ShaderScrollList' %
                                       (windowID), query=True, allItems=True)
        item = allItems[index.row()]
        value = index.data(QtCore.Qt.DisplayRole)

        # Check weather the shader is in part of the ShaderUtility.
        # I noticed sometimes with updateUI there is a latency whilst the shaderUtility updates,
        # hence I get paint errors.
        try:
            shaderUtility.data[shaderUtility.customStringToShaderName(
                item)]
        except:
            return False

        # Getting information about the item
        shaderName = shaderUtility.customStringToShaderName(
            value, properties=False)
        nameSpace = shaderUtility.data[shaderName]['nameSpace']
        shaderType = shaderUtility.data[shaderName]['type']
        attr = shaderUtility.customStringToShaderName(value, properties=True)

        # Getting visual width of the text to be drawn
        # in Maya 2017 update 4 I'm not getting the ':' anymore..
        shaderNameWidth = QtGui.QFontMetrics(
            font).width(shaderName.split(':')[-1])

        font.setBold(False)
        font.setPixelSize(10)
        painter.setFont(font)
        nameSpaceWidth = QtGui.QFontMetrics(font).width(nameSpace)

        # Draw active items
        if shaderUtility.isActive(item):
            if 'M-' in attr:
                mOffset = leadRectangleWidth
            else:
                mOffset = 0

            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82, 133, 166)))
            else:
                if shaderUtility.data[shaderName]['environment']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(70, 70, 90)))
                elif shaderUtility.data[shaderName]['light']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(150, 100, 50)))
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(90, 90, 90)))

            # Background rectangle
            painter.drawRect(option.rect)

            # 'Active' marker
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 170, 100)))
            painter.drawRect(
                QtCore.QRect(
                    option.rect.left(),
                    option.rect.top(),
                    leadRectangleWidth,
                    option.rect.height()
                )
            )

            # Draw namespace
            if nameSpace != ':':  # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace
                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(75, 75, 75)))
                    painter.drawRect(
                        QtCore.QRect(
                            leadRectangleWidth + mOffset,
                            option.rect.top(),
                            nameSpaceWidth + leadRectangleWidth * 2,
                            option.rect.height()
                        )
                    )

                # Draw namespace
                painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        leadTextMargin - leadRectangleWidth + mOffset,  # vertical offset
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width(),
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignLeft,
                    '%s' % (nameSpace)
                )

            # Draw shader name
            painter.setPen(QtGui.QPen(QtGui.QColor(210, 210, 210)))
            font.setBold(True)
            font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
            painter.setFont(font)

            painter.drawText(
                QtCore.QRect(
                    (leadRectangleWidth if nameSpace != '' else 0) + (leadRectangleWidth * 3) +
                    nameSpaceWidth + mOffset,  # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderName.split(':')[-1])
            )

            # Draw warning icon
            if '!!' in attr:
                QIcon = QtGui.QImage(self.warningIcon)
                if shaderUtility.data[shaderName]['environment'] is False:
                    painter.drawImage(
                        QtCore.QPoint(
                            (leadRectangleWidth if nameSpace != '' else 0) + (leadRectangleWidth * 3) + nameSpaceWidth +
                            mOffset + QtGui.QFontMetrics(font).width('%s' %
                                                                     (shaderName.split(':')[-1])) + 1,
                            option.rect.top() + ((self.__class__.ROW_HEIGHT / 2) - (QIcon.height() / 2))
                        ),
                        QIcon)
                attr = attr.replace('!!', '')

            # If the item is a mask append a small black rectangle to mark it
            if 'M-' in attr:
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
                painter.drawRect(
                    QtCore.QRect(
                        leadRectangleWidth,
                        option.rect.top(),
                        leadRectangleWidth,
                        option.rect.height()
                    )
                )

            # Arnold shader override and attributes
            painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
            font.setBold(False)
            font.setPixelSize(10)
            painter.setFont(font)

            if '#' in attr:  # check if the item is being overriden by a shader

                # Shader override icon
                QIcon = QtGui.QImage(self.shaderOverrideIcon)
                painter.drawImage(
                    QtCore.QPoint(
                        option.rect.width() - QIcon.width() - leadRectangleWidth,
                        option.rect.top() + ((self.__class__.ROW_HEIGHT / 2) - (QIcon.height() / 2))
                    ),
                    QIcon
                )

                # Remove shader override character and draw arnold attributes
                attr = attr.replace('#', '')

                painter.drawText(
                    QtCore.QRect(
                        0,
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width() - QIcon.width() - leadRectangleWidth * 2,
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignRight,
                    '{0}-{1}'.format(shaderType, attr)
                )
            else:
                painter.drawText(
                    QtCore.QRect(
                        0,
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width() - leadRectangleWidth,
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignRight,
                    '{0}-{1}'.format(shaderType, attr)
                )

        # !!! Draw inactive items
        if shaderUtility.isActive(item) is False:
            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82, 133, 166)))
            else:
                if shaderUtility.data[shaderName]['environment']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(40, 40, 70)))
                elif shaderUtility.data[shaderName]['light']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(65, 65, 35)))
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(55, 55, 55)))

            painter.drawRect(option.rect)

            # Draw namespace
            if nameSpace != ':':  # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace
                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
                    painter.drawRect(
                        QtCore.QRect(
                            0,
                            option.rect.top(),
                            nameSpaceWidth + leadRectangleWidth * 2,
                            option.rect.height()
                        )
                    )

                # Draw namespace rectangle and text
                painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        textSpacer,  # vertical offset
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width(),
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignLeft,
                    '%s' % (nameSpace)
                )

            # Draw shader name
            painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
            font.setBold(False)
            font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
            painter.setFont(font)

            painter.drawText(
                QtCore.QRect(
                    (textSpacer if nameSpace != '' else 0) + textSpacer + nameSpaceWidth +
                    leadRectangleWidth,  # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderName.split(':')[-1])
            )

            try:
                # Arnold shader override and attributes
                painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        0,
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width() - leadRectangleWidth,
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignRight,
                    '{0}-{1}'.format(shaderType, attr[1:][:-1])
                )

            except:
                raise RuntimeError('Error drawing text.')

        # Separators
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
        painter.drawRect(
            QtCore.QRect(
                option.rect.left(),
                option.rect.top(),
                option.rect.width(),
                1
            )
        )

        painter.restore()

    def apply(self, delegate):
        """
        Applies custom skin to the Render Setup Utility window

        """

        window.layout().setSpacing(0)
        window.layout().addStretch(1)

        for item in ['%s_frameLayoutLayers', '%s_frameLayout02', '%s_rowLayout04', '%s_rowLayout03']:
            q.getQItem(item % (windowID), QtWidgets.QWidget)
            q.widget.setStyleSheet(
                'QWidget {\
                    padding:0;\
                    margin:0;\
                }'
            )

        q.getQItem('%s_ShaderScrollList' % (windowID), QtWidgets.QListWidget)

        QSize = QtCore.QSize(delegate.ROW_WIDTH, delegate.ROW_HEIGHT)

        for i in range(q.widget.count()):
            q.widget.setItemDelegateForRow(i, delegate)
            q.widget.item(i).setSizeHint(QSize)

        q.widget.setStyleSheet(
            'QListWidget {\
                padding:0;\
                margin:0;\
                color: rgb(200,200,200);\
                background-color:rgb(60,60,60);\
                border-style:solid;\
                border-radius:2\
            }'
        )

        # Filter list
        q.getQItem('%s_rowLayout03' % (windowID), QtWidgets.QWidget)
        q.widget.setStyleSheet(
            'QWidget {\
                background-color: rgb(60,60,60);\
                color: rgb(200,200,200);\
                padding:1 0;\
                margin:0;\
        }')

        # Arnold Propery / Shader Overrides
        for item in ['%s_columnLayout20', '%s_columnLayout21']:
            q.getQItem(item % (windowID), QtWidgets.QWidget)
            q.widget.setStyleSheet(
                '.QWidget {\
                    background-color: rgb(60,60,60);\
                    color: rgb(200,200,200);\
                    padding: 4px 0px 2px 4px;\
                    margin: 0;\
                    border-radius:2px\
                }\
                QWidget {\
                    padding: 0 4;\
                }'
            )

        for item in ['%s_selectActiveLayer' % (windowID), '%s_selectVisibleLayer' % (windowID), '%s_optionMenu02' % (windowID), '%s_optionMenu03' % (windowID), '%s_outputVersionMenu' % (windowID)]:
            q.getQItem(item, QtWidgets.QComboBox)
            q.widget.setStyleSheet(
                'QComboBox {\
                    color: rgb(200,200,200);\
                    background-color: rgb(95,95,95);\
                    padding:0 4px 0 4px;\
                    margin:0;\
                }\
                QComboBox QAbstractItemView  {\
                    padding: 0;\
                    border-width: 0;\
                    border-style: none;\
                }'
            )
        for item in ['%s_optionMenu01' % (window.gwCustomRenamer.windowID), '%s_optionMenu02' % (window.gwCustomRenamer.windowID), '%s_optionMenu03' % (window.gwCustomRenamer.windowID)]:
            q.getQItem(item, QtWidgets.QComboBox)
            q.widget.setStyleSheet(
                'QComboBox {\
                    color: rgb(200,200,200);\
                    background-color: rgb(68,68,68);\
                    padding:0 4px 0 0;\
                    margin:0;\
                    }\
                QComboBox QAbstractItemView {\
                    border-width:0;\
                    border-style: none;\
                }'
            )

        # Buttons
        def setButtonStylesheet(inName, eColor, eBackgroundColor, ehColor, ehBackgroundColor):
            q.getQItem(inName, QtWidgets.QPushButton)
            q.widget.setStyleSheet('QPushButton {\
                color: rgb(%s);\
                background-color: rgb(%s);\
                border: none;\
                border-radius: 2px;\
                font-size:12px\
            }\
            QPushButton:hover {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }\
            QPushButton:disabled {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }' % (eColor, eBackgroundColor, ehColor, ehBackgroundColor, dColor, dBackgroundColor))

        def setAdobeButtonStylesheet(inName, eColor, eBackgroundColor, ehBackgroundColor):
            q.getQItem(inName, QtWidgets.QPushButton)
            q.widget.setStyleSheet('QPushButton {\
                color: rgb(%s);\
                background-color: rgb(%s);\
                border: solid;\
                border-color: rgb(%s);\
                border-width: 1px;\
                border-radius: 2px;\
                font-size:11px\
            }\
            QPushButton:hover {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }\
            QPushButton:disabled {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }' % (eColor, eBackgroundColor, eColor, eColor, ehBackgroundColor, eColor, eBackgroundColor))

        eColor = '200,200,200'
        eBackgroundColor = '95,95,95'
        ehColor = '230,230,230'
        ehBackgroundColor = '100,100,100'
        dColor = '95,95,95'
        dBackgroundColor = '68,68,68'

        for item in ['rsAddCollection', 'rsRemoveCollection', 'updateConnections', '%s_incrementOutputVersionButton' % (windowID), '%s_button01' % (window.gwCustomRenamer.windowID), '%s_button02' % (window.gwCustomRenamer.windowID), '%s_button03' % (window.gwCustomRenamer.windowID)]:
            setButtonStylesheet(item, eColor, eBackgroundColor,
                                ehColor, ehBackgroundColor)
        for item in ['editTexture', 'uvSnapshot']:
            setAdobeButtonStylesheet(
                item, '27, 198, 251', '0,29,38', '0,39,48')
        setAdobeButtonStylesheet(
            'makeCompButton', '198,140,248', '31,0,63', '41,0,73')

        for item in ['%s_filterShaderList' % (windowID), '%s_textField01' % (window.gwCustomRenamer.windowID), '%s_textField02' % (window.gwCustomRenamer.windowID), '%s_textField03' % (window.gwCustomRenamer.windowID)]:
            q.getQItem(item, QtWidgets.QLineEdit)
            q.widget.setStyleSheet('QLineEdit {\
                background-color: rgb(60,60,60);\
                padding:2 2;\
                margin:0;\
            }')

        # Arnold Property override checkbox labels
        for index, item in enumerate(rsUtility.overrideAttributes):
            q.getQItem(
                '%s_text%s' % (windowID, str(index).zfill(2)),
                QtWidgets.QLabel
            )
            q.widget.setStyleSheet('QLabel {\
                border-style: dashed;\
                border-width: 0 0 1px 0;\
                border-color: rgb(50,50,50);\
                color: rgb(175,175,175);\
                font-size: 10px;\
                margin-left: 0;\
                margin-bottom: 2\
            }')

        q.getQItem('%s_revealOutputDirectory' % (windowID), QtWidgets.QPushButton)
        q.widget.setStyleSheet('QPushButton {\
            color: rgb(150,150,150);\
            background-color: rgb(50,50,50);\
            border: none;\
            border-radius: 2px;\
            font-size:12px\
        }')

        q.getQItem('rsShaderGroups', QtWidgets.QComboBox)
        q.widget.setStyleSheet(
            'QComboBox {\
                color: rgb(150,150,150);\
                background-color: rgb(60,60,60);\
                font-size:11px\
                }\
            }'
        )
