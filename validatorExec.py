import maya.cmds as cmds

import os

from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from maya import OpenMayaUI
from shiboken2 import wrapInstance
from PySide2.QtGui import QPixmap
import json

# from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.OpenMayaUI as omui

mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()
mayaMainWindow = wrapInstance(int(mayaMainWindowPtr), QWidget)


class NamingValidator(QWidget):
    mesh_nodeDefaults = {}
    notFound = []

    def __init__(self, *args, **kwargs):
        super(NamingValidator, self).__init__(*args, **kwargs)
        self.invalidMeshes = {}
        self.invalidBs = {}
        self.setParent(mayaMainWindow)
        self.setObjectName('NamingValidator')
        self.setWindowTitle('Mesh Naming Validator')
        self.setWindowFlags(Qt.Window)
        self.init_UI()

    def init_UI(self):
        usd = cmds.internalVar(usd=True)
        UI_FILE = os.path.join(usd, 'Naming_Validator', 'Resources', 'ValidatorWindow.ui')
        ui_file = QFile(UI_FILE)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()

        self.ui = loader.load(ui_file, parentWidget=self)
        ui_file.close()

        self.txtEditDefaults = self.ui.txtEditDefaults
        self.tableSearchResult = self.ui.tableSearchResult

        self.ui.btnValidate.clicked.connect(self.validateList)

        self.ui.refreshNameButton.clicked.connect(self.loadNameSpace)
        self.ui.btnRetrieveConventions.clicked.connect(self.retrieveConventions)

        self.nameSpaceComboBox = self.ui.nameSpaceComboBox

        self.ui.btnRenameMesh.clicked.connect(lambda: self.rename(self.invalidMeshes))
        self.ui.btnRenameBS.clicked.connect(lambda: self.rename(self.invalidBs))

        self.convComboBox = self.ui.convComboBox

        self.loadNameSpace()
        self.loadConventions()

    def run_UI(self):
        self.ui.show()

    def loadConventions(self):
        self.convComboBox.clear()
        usd = cmds.internalVar(usd=True)
        directory = os.path.join(usd, 'Naming_Validator', 'defaults')

        if directory:
            files = os.listdir(directory)

            for file in files:
                if os.path.isfile(os.path.join(directory, file)):
                    self.convComboBox.addItem(file)

    def retrieveConventions(self):
        usd = cmds.internalVar(usd=True)
        directory = os.path.join(usd, 'Naming_Validator', 'defaults')

        if directory:

            file = self.convComboBox.currentText()
            if os.path.isfile(os.path.join(directory, file)):
                with open(os.path.join(directory, file), 'r') as f:
                    content = json.loads(f.read())
                    self.txtEditDefaults.clear()
                    for item in content:
                        itemStr = item + " - " + content[item] + "\n"
                        self.txtEditDefaults.insertPlainText(itemStr)

    def validateNames(self, default, input):
        if input == default:
            return True
        else:
            return False

    def loadNameSpace(self):
        self.nameSpaceComboBox.clear()
        nameSpaceLs = cmds.namespaceInfo(":", lon=True)
        for name in nameSpaceLs:
            if name != "UI" and name != "shared":
                self.nameSpaceComboBox.addItem(name + ':')
        self.nameSpaceComboBox.addItem(':')

    def rename(self, invalidList):
        name_space = str(self.nameSpaceComboBox.currentText())
        if name_space == ':':
            if invalidList.items is not None:
                for x, y in invalidList.items():
                    cmds.rename(name_space + y, name_space + x)
                    print(y + ' renamed as ' + x)
            else:
                print('No invalids')
        else:
            cmds.warning('References are read only')

        self.validateList()

    def detectLayers(self, meshDictionary):
        self.invalidMeshes.clear()
        self.invalidBs.clear()

        self.tableSearchResult.clearContents()

        cmds.select(cl=True)
        cmds.select(all=True)
        meshes = cmds.listRelatives(ad=True, type='transform')
        name_space = str(self.nameSpaceComboBox.currentText())

        for x, y in meshDictionary.items():

            index = list(meshDictionary).index(x)

            minimum = 100000
            matched_mesh = ''
            self.tableSearchResult.insertRow(index)

            label = QLabel()
            label.setText(x)
            self.tableSearchResult.setCellWidget(index, 0, label)

            label2 = QLabel()
            label2.setText(y)
            self.tableSearchResult.setCellWidget(index, 3, label2)

            for mesh in meshes:
                if name_space == ':' or (not mesh.startswith(name_space)):
                    unprefixed_MeshName = mesh
                else:
                    unprefixed_MeshName = mesh.split(':')[1]

                distance = self.levenshtein_distance(unprefixed_MeshName, x)
                if distance < minimum:
                    minimum = distance
                    if minimum < 3:
                        matched_mesh = unprefixed_MeshName

            # if no matches found
            if len(matched_mesh) == 0:
                label3 = QLabel()
                label3.setText("-")
                self.tableSearchResult.setCellWidget(index, 1, label3)

                label4 = QLabel()
                label4.setText("Not Found")
                label4.setStyleSheet("background-color:rgb(204,102,0)")
                self.tableSearchResult.setCellWidget(index, 2, label4)

                label5 = QLabel()
                label5.setText("-")
                self.tableSearchResult.setCellWidget(index, 4, label5)

                label6 = QLabel()
                label6.setText("Not Found")
                label6.setStyleSheet("background-color:rgb(204,102,0)")
                self.tableSearchResult.setCellWidget(index, 5, label6)

            else:

                label3 = QLabel()
                label3.setText(matched_mesh)
                self.tableSearchResult.setCellWidget(index, 1, label3)

                label4 = QLabel()
                if self.validateNames(x, matched_mesh):
                    label4.setText('Valid')
                    label4.setStyleSheet("background-color:rgb(0,153,76)")
                else:
                    label4.setText('Invalid')
                    label4.setStyleSheet("background-color:rgb(170,80,80)")
                    self.invalidMeshes[x] = matched_mesh

                self.tableSearchResult.setCellWidget(index, 2, label4)

                if name_space == ':':

                    if len(self.getBlendShape(matched_mesh)) > 0:
                        affiliatedBlendShape = self.getBlendShape(matched_mesh)[0]

                    else:
                        affiliatedBlendShape = '-'

                else:

                    if len(self.getBlendShape(name_space + matched_mesh)) > 0:
                        affiliatedBlendShape = self.getBlendShape(name_space + matched_mesh)[0].split(':')[1]

                    else:
                        affiliatedBlendShape = '-'

                label5 = QLabel()
                label5.setText(affiliatedBlendShape)
                self.tableSearchResult.setCellWidget(index, 4, label5)

                label6 = QLabel()
                if self.validateNames(y, affiliatedBlendShape):
                    label6.setText('Valid')
                    label6.setStyleSheet("background-color:rgb(0,153,76)")
                else:
                    label6.setText('Invalid')
                    label6.setStyleSheet("background-color:rgb(170,80,80)")
                    self.invalidBs[y] = affiliatedBlendShape
                self.tableSearchResult.setCellWidget(index, 5, label6)

        print(self.invalidMeshes)
        print(self.invalidBs)

    def validateList(self):
        dict = {}
        text = self.txtEditDefaults.toPlainText()
        splitL1 = text.split('\n')
        splitL1.remove("")
        for i in range(len(splitL1)):
            splitL1[i] = splitL1[i].replace(" ", "")
        for item in splitL1:
            splitL2 = item.split('-')
            dict[splitL2[0]] = splitL2[1]
        self.detectLayers(dict)

    def getBlendShape(self, obj):
        return cmds.ls(cmds.listHistory(obj), type="blendShape")

    def levenshtein_distance(self, str1, str2):
        len_str1 = len(str1)
        len_str2 = len(str2)

        # Create a matrix to store the distances
        dp = [[0] * (len_str2 + 1) for _ in range(len_str1 + 1)]

        # Initialize the first row and column
        for i in range(len_str1 + 1):
            dp[i][0] = i
        for j in range(len_str2 + 1):
            dp[0][j] = j

        # Fill in the matrix
        for i in range(1, len_str1 + 1):
            for j in range(1, len_str2 + 1):
                cost = 0 if str1[i - 1] == str2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # Deletion
                    dp[i][j - 1] + 1,  # Insertion
                    dp[i - 1][j - 1] + cost  # Substitution
                )

        # The bottom-right cell contains the Levenshtein distance
        return dp[len_str1][len_str2]


try:
    namingValidator.close()
    namingValidator.deleteLater()
except:
    pass
namingValidator = NamingValidator()
namingValidator.run_UI()
