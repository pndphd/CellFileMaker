# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CellFileMaker
								 A QGIS plugin
 Makes the Cell File for inSALMO
							  -------------------
		begin				: 2016-10-28
		git sha			  : $Format:%H$
		copyright			: (C) 2016 by Peter Dudley
		email				: pndphd@gmail.com
 ***************************************************************************/

/***************************************************************************
 *																		 *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or	 *
 *   (at your option) any later version.								   *
 *																		 *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.analysis import *
import qgis.utils
import processing
import os.path
import os

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from CellFileMaker_dialog import CellFileMakerDialog

class CellFileMaker:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.
		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'CellFileMaker_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		# Create the dialog (after translation) and keep reference
		self.dlg = CellFileMakerDialog()

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&CellFileMaker')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar(u'CellFileMaker')
		self.toolbar.setObjectName(u'CellFileMaker')
		
		# set up and the line input and push button
		self.dlg.lineEdit.clear()
		self.dlg.pushButton.clicked.connect(self.select_output_file)
	
		# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.
		We implement this ourselves since we do not inherit QObject.
		:param message: String for translation.
		:type message: str, QString
		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('CellFileMaker', message)

	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.
		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""
		icon_path = ':/plugins/CellFileMaker/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Cell File Maker'),
			callback=self.run,
			parent=self.iface.mainWindow())

	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginMenu(
				self.tr(u'&CellFileMaker'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar
		
	def select_output_file(self):
		# define the interface for selecting a file
		filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","", '*.Data')
		self.dlg.lineEdit_2.setText(filename)

	def run(self):
		"""Run method that performs all the real work"""
		
		# load all layers into combo boxes
		layers = self.iface.legendInterface().layers()
		layer_list = []
		self.dlg.coverComboBox.clear()
		self.dlg.gravelComboBox.clear()
		self.dlg.gridComboBox.clear()
		self.dlg.gridComboBox.addItems(layer_list)
		self.dlg.coverComboBox.addItems(layer_list)
		self.dlg.gravelComboBox.addItems(layer_list)
		
		# show the dialog
		self.dlg.show()
		
		# Run the dialog event loop
		result = self.dlg.exec_()
		
		# See if OK was pressed
		if result:
			fileName = self.dlg.lineEdit_2.text()
		
			factor = float(self.dlg.lineEdit.text())
			outputFile = open(fileName, 'w')
		
			# get the layers
			coverLayer = layers[self.dlg.coverComboBox.currentIndex()]
			gravelLayer = layers[self.dlg.gravelComboBox.currentIndex()]
			gridLayer = layers[self.dlg.gridComboBox.currentIndex()]
			
			QgsMessageLog.logMessage(coverLayer.source(), "New")
			QgsMessageLog.logMessage(gravelLayer.source(), "New")
			QgsMessageLog.logMessage(gridLayer.source(), "New")
			
			coverStatistics = QgsZonalStatistics( gridLayer, coverLayer.source())
			coverStatistics.calculateStatistics(None)
			gravelStatistics = QgsZonalStatistics( gridLayer, gravelLayer.source())
			gravelStatistics.calculateStatistics(None)
								
			# make a blank string called coords
			text = ''
			
			# Write ther first 2 lines plus forst catagory label
			text = "Line 1\nLine 2\n"
			text = text + "Cell#,FracVelShelter,DistToHidingCover,FracSpawnGravel,ReachEndCode\n"
			
			# get ther list of features form ther layer
			features = gridLayer.getFeatures()
			
			for feature in features:
				# get ther feature id
				number = feature.id()+1
				# write the feature ID

				if not(feature[3]):
					shelter = 0
				else:
					shelter = feature[3]
				cover = (1 - shelter) * factor
				if not(feature[6]):
					gravel = 0
				else:
					gravel = feature[6]
				ID = feature[0]
				text = text + str(number) + ", " + str(shelter) + ", " + str(cover) + ", " + str(gravel) + ", " + str(ID) + "\n"

			# Remove adations to grid
			gridLayer.dataProvider().deleteAttributes([1,2,3,4,5,6])
			gridLayer.updateFields()
			unicodeLine = text.encode('utf-8')
			outputFile.write(unicodeLine)
			outputFile.close()
			#QgsMapLayerRegistry.instance().removeMapLayer( tempLayer.id() )
			
			
			