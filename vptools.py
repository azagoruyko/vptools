try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

except:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

import math
import time
import os
import re
import xml.etree.ElementTree as ET
import glob
import string
import json
from xml.sax.saxutils import escape, unescape

import pymel.core as core
import pymel.api as api
import maya.cmds as cmds

from maya import OpenMayaUI as apiUI
from shiboken2 import wrapInstance

MayaProjectDirectory = os.path.dirname(cmds.workspace(q=True, rd=True))
VPToolsDirectory = "D:/My/3D/Scripts/vptools"
VPToolsLocalDirectory = MayaProjectDirectory+"/vptools"

def color2hex(color):
    return "#%.2x%.2x%.2x"%color

def point2str(p):
    return "%d %d"%p

def points2str(points):
    return ",".join([point2str(p) for p in points])

def text2points(text):
    if not text:
        return []
    
    points = []
    for pd in text.split(","):
        x,y = pd.split()
        x = int(x.strip())
        y = int(y.strip())
        points.append((x,y))

    return points

class VPControlProps(object):
    PolygonType = 0
    EllipseType = 1
    RectType = 2

    Margin = 2

    MinPositionX = 0
    MinPositionY = 0

    def __init__(self,
                 type=RectType,
                 position=(0, 0),
                 rotation=0,
                 invert=False,
                 size=(10, 10),
                 textColor=(0, 0, 0),
                 color=(0, 0, 0),
                 roundRadius=25,
                 gradient=True,
                 label="",
                 points=[],
                 control="",
                 command="print \"hello world\""):

        self.type = type

        self.position = position
        self.rotation = rotation
        self.invert = invert
        self.size = size

        self.textColor = textColor
        self.color = color
        self.gradient = gradient
        self.roundRadius = roundRadius

        self.label = label

        self.points = list(points)

        self.control = control
        self.command = command

    def copy(self):
        s = VPControlProps()
        s.type = self.type

        s.position = tuple(self.position)
        s.rotation = self.rotation
        s.invert = self.invert
        s.size = tuple(self.size)

        s.textColor = self.textColor
        s.color = self.color
        s.gradient = self.gradient
        s.roundRadius = self.roundRadius

        s.label = self.label

        s.points = list(self.points)

        s.control = self.control
        s.command = self.command
        return s        
    
    def getScaledPoints(self):
        maxX, maxY = 0.001, 0.001
        for x,y in self.points:
            if x > maxX:
                maxX = x
            if y > maxY:
                maxY = y

        scaledPoints = []
        for x,y in self.points:
            scaledX = x / float(maxX) * self.size[0]
            scaledY = y / float(maxY) * self.size[1]

            scaledX += VPControlProps.Margin
            scaledY += VPControlProps.Margin

            scaledPoints.append((scaledX, scaledY))

        return scaledPoints

    def boundingRect(self):
        if self.type == VPControlProps.PolygonType:
            w = 0
            h = 0
            for p in self.getScaledPoints():
                if p[0] > w:
                    w = p[0]

                if p[1] > h:
                    h = p[1]

            return (0,0,w+VPControlProps.Margin,h+VPControlProps.Margin)

        else:
            return (0,0,self.size[0] + VPControlProps.Margin, self.size[1] + VPControlProps.Margin)

    def toXml(self):
        return "\n".join(["".join(["<control ",
                                   " ".join(["type=\"{type}\"",
                                             "position=\"{x},{y}\"",
                                             "rotation=\"{rotation}\"",
                                             "invert=\"{invert}\"",
                                             "size=\"{w},{h}\"",
                                             "label=\"{label}\"",
                                             "color=\"{color}\"",
                                             "gradient=\"{gradient}\"",
                                             "textColor=\"{textColor}\"",
                                             "roundRadius=\"{roundRadius}\"",
                                             "points=\"{points}\"",
                                             "control=\"{control}\""]).format(
                                                 type=self.type,
                                                 x=int(self.position[0]),
                                                 y=int(self.position[1]),
                                                 rotation=int(self.rotation),
                                                 invert=int(self.invert),
                                                 w=int(self.size[0]),
                                                 h=int(self.size[1]),
                                                 label=self.label,
                                                 roundRadius=int(self.roundRadius),
                                                 color="%d,%d,%d"%self.color,
                                                 gradient=int(self.gradient),
                                                 textColor="%d,%d,%d"%self.textColor,
                                                 points=points2str(self.points),
                                                 control=self.control),
                                   ">"]),
                          "\n".join(["<command>",
                                     "<![CDATA[%s]]>"%self.command.strip(),
                                     "</command>"]),
                          "</control>"])

    def saveToFile(self, path):
        with open(path, "w") as f:
            f.write(self.toXml())

    @staticmethod
    def saveToFileList(path, props):
        xmls = []
        for p in props:
            xmls.append(p.toXml())

        with open(path, "w") as f:
            f.write("\n".join(["<props>",
                               "\n".join(xmls),
                               "</props>"]))


    @staticmethod
    def fromXmlElement(element):
        s = VPControlProps()
        s.type = int(element.get("type",0))
        s.position = tuple([int(v) for v in element.get("position", (0,0)).split(",")])
        s.rotation = int(element.get("rotation", 0))
        s.invert = bool(int(element.get("invert", False)))
        s.size = tuple([int(v) for v in element.get("size", (0,0)).split(",")])
        s.label = element.get("label", "")
        s.color = tuple([int(v) for v in element.get("color").split(",")])
        s.textColor = tuple([int(v) for v in element.get("textColor").split(",")])
        s.gradient = bool(int(element.get("gradient")))
        s.roundRadius = int(element.get("roundRadius", 0))
        if element.get("points"):
            s.points = [(int(x), int(y)) for x,y in [p.split() for p in element.get("points").split(",")]]

        s.control = element.get("control","")
        s.command = element.findtext("command","").strip()

        if s.position[0] < VPControlProps.MinPositionX:
            VPControlProps.MinPositionX = s.position[0]
        if s.position[1] < VPControlProps.MinPositionY:
            VPControlProps.MinPositionY = s.position[1]            
        return s

    @staticmethod
    def fromXml(text):
        root = ET.fromstring(text).getroot()
        return VPControlProps.fromXmlElement(root)

    @staticmethod
    def loadFromFileList(path):
        root = ET.parse(path).getroot()
        props = []
        for e in root.iter("control"):
            props.append(VPControlProps.fromXmlElement(e))
        return props

    @staticmethod
    def loadFromFile(path):
        root = ET.parse(path).getroot()
        return VPControlProps.fromXmlElement(root)

    @staticmethod
    def listControls():
        files = []
        for f in glob.glob(VPToolsDirectory+"/controls/*.xml"):
            files.append(f)
        return files

def clamp(mn, mx, val):
    if mn!=None and val < mn:
        return mn
    elif mx!=None and val > mx:
        return mx
    else:
        return val
    
class VPcontrol(QGraphicsItem):
    def __init__(self, vpcontrolProps, editable=True, **kwargs):
        super(VPcontrol, self).__init__(**kwargs)

        self.vpcontrolProps = vpcontrolProps
        self.isDragging = False
        self.isHover = False
        self.isEditable = editable
        self.dragDelta = QPoint()
        self.defaultColor = None

        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self.setToolTip(self.vpcontrolProps.control)

        x = self.vpcontrolProps.position[0] - VPControlProps.MinPositionX
        y = self.vpcontrolProps.position[1] - VPControlProps.MinPositionY

        self.setRotation(self.vpcontrolProps.rotation)
        self.setTransform(QTransform.fromScale(-1 if self.vpcontrolProps.invert else 1, 1))
        self.setPos(x, y)

    def boundingRect(self):
        sc = self.vpcontrolProps
        r = sc.boundingRect()
        return QRectF(r[0], r[1], r[2], r[3])

    def paint(self, painter, option, widget=None):
        props = self.vpcontrolProps

        painter.setRenderHints(QPainter.Antialiasing)
        self.defaultColor = QColor(props.color[0], props.color[1], props.color[2])

        color = self.defaultColor.lighter(133) if self.isHover else self.defaultColor
        color = color if self.isEnabled() else QColor(88,88, 88)
        color.setAlpha(166)
        painter.setPen(QColor(33,33,33))
        if props.gradient and self.isEnabled():
            rect = self.boundingRect()
            gradient = QLinearGradient(0, rect.height() / 2, 0, 0)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor.fromRgbF(1, 1, 1, 1))
            painter.setBrush(gradient)
        else:
            painter.setBrush(color)

        margin = VPControlProps.Margin

        if props.type == VPControlProps.PolygonType:
           poly = QPolygonF()
           for x, y in props.getScaledPoints():
               poly.append(QPoint(x, y))
           painter.drawPolygon(poly)

        elif props.type == VPControlProps.EllipseType:
            painter.drawEllipse(margin, margin, props.size[0]-margin, props.size[1]-margin)

        elif props.type == VPControlProps.RectType:
            painter.drawRoundedRect(margin, margin, props.size[0]-margin, props.size[1]-margin, props.roundRadius, props.roundRadius)

        if props.label: # draw text on the center
            center = QPoint(margin + (props.size[0]-margin)/2,
                            margin + (props.size[1]-margin)/2)

            textWidth = painter.fontMetrics().width(props.label)
            textHeight = painter.fontMetrics().height()

            textOffset = QPoint(textWidth/2, -textHeight/4)
            painter.setPen(QColor(props.textColor[0], props.textColor[1], props.textColor[2]))
            painter.drawText(center - textOffset, props.label)

        r = props.boundingRect()
        if self.isSelected():
            painter.setBrush(Qt.NoBrush)
            pen = painter.pen()
            pen.setColor(Qt.white) # white
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            margin = 0
            painter.drawRect(r[0]-margin, r[1]-margin, r[2]+margin*2, r[3]+margin*2)

        '''
        if self.isHover:
            pen = painter.pen()
            pen.setColor(Qt.white) # white
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r[0], r[1], r[2], r[3])
        '''

    def hoverMoveEvent (self, event):
        self.isHover = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self.isHover = False
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def contextMenuEvent(self, event):
        if not self.isEditable:
            ns = unicode(self.scene().mainWindow.namespaceWidget.currentText())+":"
            ctrl = self.vpcontrolProps.control

            # draw context menu here

            return

        menu = QMenu()

        copyAction = menu.addAction("Copy")
        copyAction.triggered.connect(self.copyItems)

        saveAction = menu.addAction("Save")
        saveAction.triggered.connect(self.saveToFile)

        removeAction = menu.addAction("Remove")
        removeAction.triggered.connect(self.removeItems)

        menu.exec_(event.screenPos())

    def removeItems(self):
        for item in self.scene().selectedItems():
            self.scene().removeItem(item)

    def copyItems(self):
        selected = self.scene().selectedItems()
        isMulti = len(selected) > 1

        Offset = QPoint(50, 50)

        newItems = []
        for item in selected:
            it = self.scene().insertControl(item.vpcontrolProps.copy())
            if isMulti:
                it.setPos(item.pos() + Offset)
                newItems.append(it)

        if isMulti:
            self.scene().clearSelection()

            for it in newItems:
                it.setSelected(True)

    def saveToFile(self):
        text, ok = QInputDialog.getText(self.scene().mainWindow, "VPTools", "Name")
        if ok:
            self.vpcontrolProps.saveToFile("./controls/%s.xml"%(text))

    def mouseMoveEvent(self, event):
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        alt = event.modifiers() & Qt.AltModifier

        if not self.isDragging or not self.isEditable:
            return

        for item in self.scene().selectedItems():
            if item.isDragging:
                tr = item.transform()
                newPos = event.scenePos() - item.dragDelta

                if shift:
                    newPos.setX(int(newPos.x()) / 5 * 5)
                    newPos.setY(int(newPos.y()) / 5 * 5)

                newPos.setX(clamp(0, self.scene().mainWindow.width()-self.boundingRect().width()-25, newPos.x()))
                newPos.setY(clamp(0, self.scene().mainWindow.height()-self.boundingRect().height()-25, newPos.y()))
                item.setPos(newPos)

    def mousePressEvent(self, event):
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        alt = event.modifiers() & Qt.AltModifier

        scene = self.scene()
        
        if self.isEditable:
            if event.buttons() == Qt.LeftButton:

                if self.isSelected(): # move
                    for item in scene.selectedItems():
                        item.isDragging = True
                        item.dragDelta = event.scenePos() - item.pos()

                else:
                    if not shift:
                        scene.clearSelection()

                    self.setSelected(True)
            else:
                pass
        else:
            if event.buttons() == Qt.LeftButton:
                shift = event.modifiers() & Qt.ShiftModifier

                sc = self.vpcontrolProps
                ns = unicode(scene.mainWindow.namespaceWidget.currentText())+":"

                if sc.control:
                    core.select(ns+sc.control, add=True if shift else False)

                if sc.command:
                    cmd = re.sub("\\$NAMESPACE\\b", "\""+ns+"\"", sc.command)
                    exec cmd in {}

    def mouseReleaseEvent(self, event):
        if not self.isEditable:
            return

        for item in self.scene().selectedItems():
            item.isDragging = False
            item.vpcontrolProps.position = (item.pos().x(), item.pos().y()) # update final position

    def wheelEvent(self, event):
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        alt = event.modifiers() & Qt.AltModifier
        if not self.isEditable:
            return

        if ctrl:
            scaleFactor = 1.033 if event.delta() > 0 else 0.966
            toInt = lambda x: int(round(x * scaleFactor))
            for item in self.scene().selectedItems():
                item.vpcontrolProps.size = (toInt(item.vpcontrolProps.size[0]), toInt(item.vpcontrolProps.size[1]))

            self.scene().update()

class ControlsBrowser(QDialog):
    def __init__(self, **kwargs):
        super(ControlsBrowser, self).__init__(**kwargs)

        self.selectedProp = None

        self.setWindowTitle("Controls Browser")

        pos = QCursor.pos()
        self.setGeometry(pos.x(), pos.y(), 900, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)

        self.update()

    def update(self):
        self.scene.clear()

        x, y = 0, 0
        maxHeight = 0
        NumColumns = 3
        Offset = 10
        for i, f in enumerate(VPControlProps.listControls()):
            s = VPControlProps.loadFromFile(f)
            item = VPcontrol(s, editable=False)
            item.fileName = f
            item.setPos(x,y)
            self.scene.addItem(item)

            item.mousePressEvent = lambda event, item=item: self.itemMousePressEvent(event, item)
            item.contextMenuEvent = lambda event, item=item: self.itemContextMenuEvent(event, item)

            bbox = item.boundingRect()
            if i % NumColumns == 0 and i > 0:
                x = 0
                y += maxHeight
                maxHeight = 0
            else:
                x += bbox.width() + Offset
                if bbox.height() > maxHeight:
                    maxHeight = bbox.height()

    def itemContextMenuEvent(self, event, item):
        menu = QMenu()

        removeAction = menu.addAction("Remove")
        removeAction.triggered.connect(lambda: self.removeItem(item))

        menu.exec_(event.screenPos())

    def removeItem(self, item):
        if QMessageBox.question(self, "VPTools", "Remove?", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Yes:
            os.remove(item.fileName)
            self.update()

    def itemMousePressEvent(self, event, item):
        if event.buttons() == Qt.LeftButton:
            self.selectedProp = item.vpcontrolProps.copy()
            self.done(0)

class VPToolsView(QGraphicsView):
    def __init__(self, scene, mainWindow, editable=False, **kwargs):
        super(VPToolsView, self).__init__(scene, **kwargs)

        self.mainWindow = mainWindow
        self.isEditable = editable
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def event(self, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Tab:
                self.insertProp()

                event.accept()
                return True
            
        return QGraphicsView.event(self, event)

    def insertProp(self):
        pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))

        cld = ControlsBrowser(parent=self.mainWindow)
        cld.exec_()

        if cld.selectedProp:
            self.scene().insertControl(cld.selectedProp, pos)
            self.scene().update()
    
    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Insert:
            self.insertProp()

        elif key == Qt.Key_Delete:
            if self.isEditable:
                scene = self.scene()
                
                for item in scene.selectedItems():
                    scene.removeItem(item)

class VPToolsScene(QGraphicsScene):
    def __init__(self, mainWindow, editable=False, **kwargs):
        super(VPToolsScene, self).__init__(**kwargs)

        self.isEditable = editable
        self.isDragging = False
        self.mainWindow = mainWindow

        self.startSelectionPosition = None

        self.selectionChanged.connect(self.selectionChangedCallback)

    def updateControls(self):
        ns = unicode(self.mainWindow.namespaceWidget.currentText())+":"
        for item in self.listControls():
            ctrl = item.vpcontrolProps.control
            ctrlNode = ns+ctrl

            # item.setSelected(ctrlNode in cmds.ls(sl=True, an=True))
            item.setEnabled((cmds.objExists(ctrlNode) and isActualVisible(ctrlNode)) or not ctrl)            
        
    def insertControl(self, prop=None, pos=None):
        if self.isEditable:
            if not pos:
                view = self.views()[0]
                pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))

            if not prop:
                prop = VPControlProps(type=VPControlProps.RectType, position=(0, 0), size=(100,30), color=(121, 255, 12), label="button")

            item = VPcontrol(prop)
            self.addItem(item)
            item.setPos(pos)

            return item

    def listControls(self):
        return [item for item in self.items() if type(item) == VPcontrol]

    def toggleControlsVisibility(self):
        for item in self.listControls():
            item.setVisible(not item.isVisible())

    def mouseMoveEvent(self, event):
        super(VPToolsScene, self).mouseMoveEvent(event)
        if self.isDragging:
            start = self.startSelectionPosition
            end = event.scenePos()

            path = QPainterPath()
            path.addRect(start.x(), start.y(), end.x()-start.x(), end.y()-start.y())
            self.setSelectionArea(path)

    def mousePressEvent(self, event):
        super(VPToolsScene, self).mousePressEvent(event)
        buttons = event.buttons()

        if self.isEditable and buttons == Qt.LeftButton and not self.selectedItems():
            self.startSelectionPosition = event.scenePos()
            self.isDragging = True

    def mouseReleaseEvent(self, event):
        super(VPToolsScene, self).mouseReleaseEvent(event)

        self.isDragging = False

    def wheelEvent(self, event):
        # wheelEvent = QWheelEvent(event.pos(), event.delta(), event.buttons(), event.modifiers())
        # w = QApplication.focusWidget()
        # QApplication.sendEvent(w, wheelEvent)
        pass

    def importFromFile(self, path, append=True):
        if not append:
            self.clear()

        views = self.views()
        for prop in VPControlProps.loadFromFileList(path):
            self.addItem(VPcontrol(prop, editable=views[0].isEditable))

    def selectionChangedCallback(self):
        if self.isEditable:
            self.mainWindow.vpcontrolPropsWidget.update()

class TwoFieldWidget(QWidget):
    def __init__(self, **kwargs):
        super(TwoFieldWidget, self).__init__(**kwargs)

        self.onChanged = None

        layout = QHBoxLayout()
        layout.setMargin(0)
        self.setLayout(layout)

        self.widthWidget = QLineEdit()
        self.widthWidget.setValidator(QIntValidator())
        self.widthWidget.editingFinished.connect(self.valueChanged)

        self.heightWidget = QLineEdit()
        self.heightWidget.setValidator(QIntValidator())
        self.heightWidget.editingFinished.connect(self.valueChanged)

        layout.addWidget(self.widthWidget)
        layout.addWidget(self.heightWidget)

    def valueChanged(self):
        if self.onChanged:
            self.onChanged()

    def setValue(self, w, h):
        self.widthWidget.setText(str(w))
        self.heightWidget.setText(str(h))

    def getValue(self):
        return (int(self.widthWidget.text()), int(self.heightWidget.text()))

class VPControlPropsWidget(QWidget):
    def __init__(self, mainWindow, **kwargs):
        super(VPControlPropsWidget, self).__init__(**kwargs)

        self.isUpdating = False
        self.mainWindow = mainWindow

        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.ToolTip)

        self.hide()

        self.idWidget = QLabel()

        self.typeWidget = QComboBox()
        self.typeWidget.addItems(["Polygon", "Ellipse", "Rect"])
        self.typeWidget.currentIndexChanged.connect(lambda idx: self.updateValue("type", idx))

        self.rotationWidget = QLineEdit()
        self.rotationWidget.setValidator(QIntValidator())
        self.rotationWidget.returnPressed.connect(lambda: self.updateValue("rotation", int(self.rotationWidget.text())))

        self.invertWidget = QCheckBox()
        self.invertWidget.stateChanged.connect(lambda: self.updateValue("invert", self.invertWidget.isChecked()))

        self.sizeWidget = TwoFieldWidget()
        self.sizeWidget.onChanged = lambda: self.updateValue("size", self.sizeWidget.getValue())

        self.labelWidget = QLineEdit()
        self.labelWidget.returnPressed.connect(lambda: self.updateValue("label", self.labelWidget.text()))

        self.colorWidget = QPushButton()
        self.colorWidget.clicked.connect(lambda: (self.colorClicked(self.colorWidget),
                                                  self.updateValue("color", (self.colorWidget.color.red(),
                                                                             self.colorWidget.color.green(),
                                                                             self.colorWidget.color.blue()))))

        self.textColorWidget = QPushButton()
        self.textColorWidget.clicked.connect(lambda: (self.colorClicked(self.textColorWidget),
                                                      self.updateValue("textColor", (self.textColorWidget.color.red(),
                                                                                     self.textColorWidget.color.green(),
                                                                                     self.textColorWidget.color.blue()))))

        self.roundRadiusWidget = QLineEdit("0")
        self.roundRadiusWidget.setValidator(QIntValidator())
        self.roundRadiusWidget.editingFinished.connect(lambda: self.updateValue("roundRadius", int(self.roundRadiusWidget.text())))

        self.gradientWidget = QCheckBox()
        self.gradientWidget.stateChanged.connect(lambda: self.updateValue("gradient", self.gradientWidget.isChecked()))

        self.pointsWidget = QLineEdit()
        self.pointsWidget.returnPressed.connect(lambda: self.updateValue("points", text2points(unicode(self.pointsWidget.text()))))

        self.controlWidget = QLineEdit()
        self.controlWidget.returnPressed.connect(lambda: self.updateValue("control", str(self.controlWidget.text())))

        self.commandWidget = QTextEdit()
        self.commandWidget.textChanged.connect(lambda: self.updateValue("command", unicode(self.commandWidget.toPlainText())))

        layout = QGridLayout()
        layout.setDefaultPositioning(2, Qt.Horizontal)

        layout.addWidget(QLabel("Type"))
        layout.addWidget(self.typeWidget)

        layout.addWidget(QLabel("Rotation"))
        layout.addWidget(self.rotationWidget)

        layout.addWidget(QLabel("Invert"))
        layout.addWidget(self.invertWidget)

        layout.addWidget(QLabel("Size"))
        layout.addWidget(self.sizeWidget)

        layout.addWidget(QLabel("Color"))
        layout.addWidget(self.colorWidget)

        layout.addWidget(QLabel("Text Color"))
        layout.addWidget(self.textColorWidget)

        layout.addWidget(QLabel("Gradient"))
        layout.addWidget(self.gradientWidget)

        layout.addWidget(QLabel("Round Radius"))
        layout.addWidget(self.roundRadiusWidget)

        layout.addWidget(QLabel("Label"))
        layout.addWidget(self.labelWidget)

        layout.addWidget(QLabel("Points"))
        layout.addWidget(self.pointsWidget)

        layout.addWidget(QLabel("Control"))
        layout.addWidget(self.controlWidget)

        layout.addWidget(QLabel("Command"))
        layout.addWidget(self.commandWidget)

        layout.setRowStretch(layout.rowCount(), 1)
        self.setLayout(layout)

    def showEvent(self, event):
        rect = self.mainWindow.geometry()
        self.setGeometry(rect.x()+rect.width(), rect.y()+20, 400, 400)
        self.setFocus()

    def updateValue(self, type, value):
        if self.isUpdating:
            return

        scene = self.mainWindow.vptoolsScene

        for item in scene.selectedItems():
            sc = item.vpcontrolProps
            item.vpcontrolProps.__setattr__(type, value)

            if type=="rotation":
                item.setRotation(value)

            elif type=="invert":
                oldPos = item.pos()
                item.setPos(0,0)
                item.setTransform(QTransform.fromScale(-1 if value else 1, 1))
                item.setPos(oldPos)

            # print "set '%s' to '%s'"%(type, value)

        scene.update()

    def colorClicked(self, widget):
        self.colorDialog = QColorDialog(parent=self.mainWindow)
        self.colorDialog.setCurrentColor(widget.color)
        if self.colorDialog.exec_() == 1:
            c = self.colorDialog.selectedColor()
            widget.color = c
            widget.setStyleSheet("background: %s"%color2hex((c.red(), c.green(), c.blue())))

    def update(self):
        scene = self.mainWindow.vptoolsScene
        items = scene.selectedItems()
        if not items:
            self.hide()
            return

        self.show()
        self.isUpdating = True

        # isMulti = len(items) > 1

        # self.labelWidget.setEnabled(not isMulti)
        # self.commandWidget.setEnabled(not isMulti)

        sc = items[-1].vpcontrolProps

        self.typeWidget.setCurrentIndex(sc.type)
        self.rotationWidget.setText(str(sc.rotation))
        self.invertWidget.setChecked(sc.invert)
        self.sizeWidget.setValue(sc.size[0], sc.size[1])
        self.labelWidget.setText(sc.label)
        self.pointsWidget.setText(",".join(["%d %d"%(x,y) for x,y in sc.points]))
        self.controlWidget.setText(sc.control)
        self.commandWidget.setText(sc.command)

        self.colorWidget.color = QColor(sc.color[0], sc.color[1], sc.color[2])
        self.colorWidget.setStyleSheet("background: %s"%color2hex(sc.color))

        self.textColorWidget.color = QColor(sc.textColor[0], sc.textColor[1], sc.textColor[2])
        self.textColorWidget.setStyleSheet("background: %s"%color2hex(sc.textColor))

        self.gradientWidget.setChecked(sc.gradient)
        self.roundRadiusWidget.setText(str(sc.roundRadius))

        self.isUpdating = False

class MainControlWidget(QPushButton):
    def __init__(self, mainWindow, **kwargs):
        super(MainControlWidget, self).__init__(**kwargs)

        self.mainWindow = mainWindow
        
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setText("VPTools")

        self.clicked.connect(lambda: self.mainWindow.vptoolsScene.toggleControlsVisibility())

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        updateAction = QAction("Update", self)
        updateAction.triggered.connect(self.mainWindow.update)
        menu.addAction(updateAction)

        menu.addSeparator()
        
        editModeAction = QAction("Edit Mode", self)
        editModeAction.triggered.connect(self.mainWindow.toggleEditMode)
        menu.addAction(editModeAction)

        closeAction = QAction("Close", self)
        closeAction.triggered.connect(self.mainWindow.close)
        menu.addAction(closeAction)

        menu.popup(event.globalPos())

class VPToolsWindow(QWidget):
    def __init__(self, modelPanel, **kwargs):
        super(VPToolsWindow, self).__init__(**kwargs)

        self.viewportWidget = getViewportWidget(modelPanel)
        self.isEditable = False

        self.attributesForCallback = ["ikfk", "v"]
        self.selectionChangedCallbackId = -1
        self.callbackIds = []
        
        self.appEventFilter = AppEventFilter(self)
        self.vptoolsEventFilter = VPToolsEventFilter(self)

        self.defaultFlags = self.windowFlags() | Qt.FramelessWindowHint | Qt.ToolTip
        self.activeFlags = self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.ToolTip #| Qt.NoDropShadowWindowHint

        self.setWindowTitle("VPTools")
        self.setGeometry(500, 200, 800, 500)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0,0,0,0); border: 0px;")
        self.setWindowFlags(self.activeFlags)

        self.namespaceWidget = QComboBox()
        self.namespaceWidget.addItems(listCharacterReferences())

        self.vptoolsScene = VPToolsScene(self)
        self.vptoolsScene.addWidget(MainControlWidget(self))
        w = self.vptoolsScene.addWidget(self.namespaceWidget)
        w.setPos(80,0)

        self.vptoolsView = VPToolsView(self.vptoolsScene, editable=False, mainWindow=self)
        self.vpcontrolPropsWidget = VPControlPropsWidget(self, parent=None)

        if os.path.exists(VPToolsLocalDirectory+"/user.xml"):
            self.vptoolsScene.importFromFile(VPToolsLocalDirectory+"/user.xml")
        else:
            self.vptoolsScene.importFromFile(VPToolsDirectory+"/biped.xml")

        splitter = QSplitter(Qt.Horizontal)

        splitter.addWidget(self.vptoolsView)

        splitter.setSizes([500, 10])
        layout = QHBoxLayout()
        # layout.setMargin(0)
        layout.addWidget(splitter)

        self.setLayout(layout)

        self.updateGeometry()
        self.vptoolsScene.updateControls()
        self.installCallbacks()

    def update(self):
        self.namespaceWidget.clear()
        self.namespaceWidget.addItems(listCharacterReferences())        
        self.updateGeometry()
        self.vptoolsScene.updateControls()
        
    def updateGeometry(self):
        self.setGeometry(getViewportRect(self.viewportWidget))

        self.vptoolsView.setTransform(QTransform())
        rect = self.vptoolsView.sceneRect()
        region = QRegion(rect.x(), rect.y(), rect.width()+10, rect.height()+10)
        self.setMask(region)

    def attributeChangeCallback(self):
        self.vptoolsScene.updateControls()
        
    def selectionChangedCallback(self):
        if self.isEditable:
            return

        ls = cmds.ls(sl=True)
        if not ls:
            return
        node = ls[0]

        for id in self.callbackIds:
            core.scriptJob(kill=id)
        self.callbackIds = []
        
        for a in self.attributesForCallback:
            attr = "%s.%s"%(node, a)
            if cmds.objExists(attr):
                self.callbackIds.append( core.scriptJob(ac=[attr, self.attributeChangeCallback]) )
    
    def installCallbacks(self):
        self.selectionChangedCallbackId = core.scriptJob(e=["SelectionChanged", self.selectionChangedCallback])
        
        self.viewportWidget.installEventFilter(self.vptoolsEventFilter)
        QApplication.instance().installEventFilter(self.appEventFilter)

    def removeCallbacks(self):
        self.viewportWidget.removeEventFilter(self.vptoolsEventFilter)
        QApplication.instance().removeEventFilter(self.appEventFilter)
        
        core.scriptJob(kill=self.selectionChangedCallbackId)        
        for id in self.callbackIds:
            core.scriptJob(kill=id)
        self.callbackIds = []
        
        self.selectionChangedCallbackId = -1
    
    def toggleEditMode(self):
        self.isEditable = not self.isEditable
        self.vptoolsView.isEditable = self.isEditable
        self.vptoolsScene.isEditable = self.isEditable

        for item in self.vptoolsScene.listControls():
            item.isEditable = self.isEditable
            item.setSelected(False)

            if self.isEditable:
                item.setEnabled(True)

        if self.isEditable:
            self.setStyleSheet("border: 0px;")
            self.clearMask()
        else:
            self.setStyleSheet("background-color: rgba(0,0,0,0); border: 0px;")
            self.updateGeometry()

            props = [item.vpcontrolProps for item in self.vptoolsScene.listControls()]
            VPControlProps.saveToFileList(VPToolsLocalDirectory + "/user.xml", props)
            print "Saved to '%s'"%(VPToolsLocalDirectory + "/user.xml")

        self.setWindowFlags(self.defaultFlags if self.isEditable else self.activeFlags)
        self.setWindowOpacity(0.8 if self.isEditable else 1)
        self.show()

    def closeEvent(self, event):
        self.removeCallbacks()

class AppEventFilter(QObject):
    def __init__(self, mainWindow, **kwargs):
        super(AppEventFilter, self).__init__(**kwargs)

        self.mainWindow = mainWindow

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ApplicationDeactivate:
            self.mainWindow.hide()
            
        elif event.type() == QEvent.ApplicationActivate:
            self.mainWindow.hide()
            self.mainWindow.show()
            
        return QObject.eventFilter(self, obj, event)
    
class VPToolsEventFilter(QObject):
    def __init__(self, mainWindow, **kwargs):
        super(VPToolsEventFilter, self).__init__(**kwargs)

        self.mainWindow = mainWindow
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.mainWindow.updateGeometry()
            self.mainWindow.hide()
            self.mainWindow.show()

        return QObject.eventFilter(self, obj, event)
    
def listCharacterReferences():
    namespaces = []
    for ref in core.ls(type="reference"):
        try:
            isLoaded = core.referenceQuery(ref, isLoaded=True)
        except:
            continue

        if not isLoaded:
            continue

        ns = core.referenceQuery(ref, shn=True, namespace=True)
        if core.objExists(ns+":M_spine_fk_1_control"):
            namespaces.append(ns)

    return namespaces

def isActualVisible(obj, checkShapes=True):
    obj = core.PyNode(obj)

    visShapes = False
    if checkShapes:
        for sh in obj.getShapes():
            visShapes = visShapes or sh.v.get()
    else:
        visShapes = True

    if obj.getShapes() and not visShapes:
        return False

    if obj.hasAttr("visibility") and obj.v.get()==False:
        return False

    if obj.getParent():
        return isActualVisible(obj.getParent(), False)
    else:
        return True

mayaMainWindow = wrapInstance(long(apiUI.MQtUtil.mainWindow()), QWidget)

def getViewportWidget(name):
    view = apiUI.M3dView()
    apiUI.M3dView.getM3dViewFromModelPanel(name, view) #Given the name of a model panel,
    return wrapInstance(long(view.widget()), QWidget)
    
def getViewportRect(widget):
    rect = widget.geometry()
    pos = widget.mapToGlobal(QPoint())
    rect.translate(pos)
    return rect

class ActionWidget(QWidget):
    def __init__(self, label, buttonFunc, isTitle=False, parent=None):
        super(ActionWidget, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setMargin(3)
        self.setLayout(layout)

        self.label = QLabel("     %s     "%label)
        self.label.enterEvent = self.label_enterEvent
        self.label.leaveEvent = self.label_leaveEvent

        if isTitle:
            font = self.label.font()
            font.setBold(True)
            self.label.setFont(font)

        layout.addWidget(self.label)
        layout.addStretch(1)

        if buttonFunc:
            self.button = QPushButton("X")
            self.button.clicked.connect(buttonFunc)
            layout.addWidget(self.button)

    def label_enterEvent(self, event):
        self.label.setStyleSheet("background-color: #5577aa;")

    def label_leaveEvent(self, event):
        self.label.setStyleSheet("")

class MenuAction(QWidgetAction):
    def __init__(self, label, buttonFunc, isTitle, parent=None):
        super(MenuAction, self).__init__(parent)
        self.label = label
        self.buttonFunc = buttonFunc
        self.isTitle = isTitle

    def createWidget(self, parent):
        return ActionWidget(self.label, self.buttonFunc, self.isTitle, parent)

def vptools():
    if not os.path.exists(VPToolsLocalDirectory):
        os.makedirs(VPToolsLocalDirectory)
    
    # panel = core.getPanel(wf=True)
    vptoolsWindow = VPToolsWindow("modelPanel4")
    vptoolsWindow.show()
    
vptools()    
