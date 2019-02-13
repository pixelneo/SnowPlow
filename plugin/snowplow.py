# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SnowPlow
                                 A QGIS plugin
 SnowPlow controller
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-01-30
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Ondrej Mekota
        email                : on84@icloud.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import * # QSettings, QTranslator, qVersion, QCoreApplication 
from PyQt5.QtGui import * #QIcon
from PyQt5.QtWidgets import *#QAction, QDialogButtonBox

from qgis.core import * #QgsMessageLog, QgsExpression, QgsFeatureRequest
from itertools import compress

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .snowplow_dialog import SnowPlowDialog
import os.path

# from utils_snowplow import *

def qgis_list_to_list(qgis_str):
    '''
        This method converts list in string in format (element_count:element0,element1,...,elementn-1)
        to python list
    '''
    # comma delimited list
    lst = [int(x) for x in qgis_str.split(',')]
    return lst

class DataHolder:
    def __init__(self):
        self.colours = [(230, 25, 75), (60, 180, 75), (235, 235, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230)]
        # self.colours = ['green', 'red', 'yellow', 'blue']
        self.current = 0

    def next_colour(self):
        self.current = (self.current + 1) % len(self.colours)
        return QColor(*self.colours[self.current])



class SnowPlow:
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
            'SnowPlow_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SnowPlow')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

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
        return QCoreApplication.translate('SnowPlow', message)


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
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/snowplow/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Snow Plow Controller'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SnowPlow'),
                action)
            self.iface.removeToolBarIcon(action)

    def get_by_field(self, values, layer, field):
        '''Returns ids of those items which have given `field` equal to `value`'''

        queries = ['{}=\'{}\''.format(field, x) for x in values]
        query = ' OR '.join(queries)
        expr = QgsExpression(query)
        selection = layer.getFeatures(QgsFeatureRequest(expr))
        ids = [x.id() for x in selection]
        return ids


    def get_inputs(self):
        checked = [
        self.dlg.priority1.isChecked(),
        self.dlg.priority2.isChecked(),
        self.dlg.priority3.isChecked()
        ]
        checked2 = [
        self.dlg.salt.isChecked(),
        self.dlg.inert.isChecked(),
        self.dlg.plow.isChecked()
        ]
        priorities = [x+1 for x in list(compress(list(range(len(checked))), checked))]      # bool list to indices (from 1) of true values eg. [T, F, T] -> [0,2] 
        no_priorities = set(range(len(checked)+1)[1:]).difference(set(priorities))          # those indices which are not in `priorities`

        method = [x+1 for x in list(compress(list(range(len(checked2))), checked2))]      # bool list to indices (from 1) of true values eg. [T, F, T] -> [0,2] 
        no_method = set(range(len(method)+1)[1:]).difference(set(method))          # those indices which are not in `priorities`

        return ((priorities, no_priorities), (method, no_method))

    def select_new_car(self, symbol, renderer, label, expression, color):
        layer = self.iface.activeLayer()
        root_rule = renderer.rootRule()
        rule = root_rule.children()[0].clone()
        rule.setLabel(label)
        rule.setFilterExpression(expression)
        rule.symbol().setColor(color)
        root_rule.appendChild(rule)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def select_cars(self):
        layer = self.iface.activeLayer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        selected = []
        for car in self.dlg.cars.selectedItems():
            QgsMessageLog.logMessage(car.text(), 'SnowPlow')
            selected.append(' \"car_id_str\" NOT LIKE \'% {} %\''.format(str(car.text())))
            self.select_new_car(symbol, renderer, 'Car {}'.format(str(car.text())), ' \"car_id_str\" LIKE \'% {} %\''.format(str(car.text())), self.data_holder.next_colour())

        # set the not selected colour
        self.select_new_car(symbol, renderer, 'Others' ,' AND '.join(selected), QColor(220,220,220))



    def colourize(self):
        pass

    def apply_filter(self):
        """Apply selected filtering rules."""

        QgsMessageLog.logMessage('aplied', 'SnowPlow')

        # colourize 
        # TODO undo
        if self.dlg.colourize.isChecked():
            self.colourize()

        if self.dlg.cars_activate.isChecked():
            self.select_cars()


        ((priorities, no_priorities), (method, no_method)) = self.get_inputs()
        layer = self.iface.activeLayer()

        # Debugging messages
        x = 'prio: {}'.format(','.join(map(str, priorities)))
        y = 'noio: {}'.format(','.join(map(str, no_priorities)))
        QgsMessageLog.logMessage(x, 'SnowPlow')
        QgsMessageLog.logMessage(y, 'SnowPlow')

        deselected = self.get_by_field(no_priorities, layer, 'priority')
        deselected += self.get_by_field(no_method, layer, 'maintenance_method')
        layer.deselect(deselected)

        selected = self.get_by_field(priorities, layer, 'priority')
        selected += self.get_by_field(method, layer, 'maintenance_method')
        layer.select(selected)
        self.iface.mapCanvas().setSelectionColor( QColor("blue") )
        # self.iface.mapCanvas().zoomToSelected()

    def fill_listwidget(self):
        # fill listview with car IDs
        layer = self.iface.activeLayer()
        car_ids = set()
        try:
            for f in layer.getFeatures():
                for car in qgis_list_to_list(f['car_id_str']):
                    car_ids.add(car)

            self.dlg.cars.addItems([str(x) for x in list(car_ids)])
            QgsMessageLog.logMessage(', '.join([str(x) for x in list(car_ids)]), 'SnowPlow')
        except Exception as e:
            iface.messageBar().pushMessage("Error", "Most likely, no layer is selected.", level=Qgis.Critical)
            raise e



    def run(self):
        """Run method that performs all the real work"""
        self.data_holder = DataHolder()

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SnowPlowDialog()
            apply_button = self.dlg.buttons.button(QDialogButtonBox.Apply)
            apply_button.clicked.connect(self.apply_filter)
            ok_button = self.dlg.buttons.button(QDialogButtonBox.Ok)
            ok_button.clicked.connect(self.apply_filter)
            # fill list_widget
            self.fill_listwidget()

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass
