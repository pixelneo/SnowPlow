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
from itertools import compress, product

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .snowplow_dialog import SnowPlowDialog
import os.path
import concurrent.futures
import threading
from functools import partial
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
        self.colours = [(230, 25, 75, 220), (60, 180, 75, 220), (225, 225, 25, 220), (0, 130, 200, 220), (245, 130, 48, 220), (145, 30, 180, 220), (70, 220, 220, 220), (220, 50, 210, 220)]
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

    def _select_new_car(self, symbol, renderer, label, expression, color, size=0.5):
        root_rule = renderer.rootRule()
        rule = root_rule.children()[0].clone()
        rule.setLabel(label)
        rule.setFilterExpression(expression)
        rule.symbol().setColor(color)
        rule.symbol().setWidth(size)
        root_rule.appendChild(rule)

    def _select_cars(self):
        layer = self.iface.activeLayer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        selected = []
        # set the not selected colour
        renderer.rootRule().children()[0].symbol().setColor(QColor(200,200,200,255))
        for car in self.dlg.cars.selectedItems():
            QgsMessageLog.logMessage(car.text(), 'SnowPlow')
            selected.append(' \"car_id_str\" NOT LIKE \'% {} %\''.format(str(car.text())))
            self._select_new_car(symbol, renderer, 'Car {}'.format(str(car.text())), ' \"car_id_str\" LIKE \'% {} %\''.format(str(car.text())), self.data_holder.next_colour(), 1)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())


    def colourize(self):
        pass

    def apply_filter(self):
        """Apply selected filtering rules."""

        QgsMessageLog.logMessage('aplied', 'SnowPlow')

        if self.dlg.cars_activate.isChecked():
            self._select_cars()

        self.set_priorities_and_methods()

    def _get_feat_names(self):
        layer = self.iface.activeLayer()
        fs = layer.getFeatures()
        f = next(fs)
        return set([x.name() for x in f.fields()])

    def fill_cars(self):
        # fill listview with car IDs
        layer = self.iface.activeLayer()
        car_ids = set()
        try:
            for f in layer.getFeatures():
                if 'car' in f['id']:
                    car_ids.add(f['id'])

            car_ids = sorted(car_ids)
            self.dlg.cars.addItems([str(x) for x in list(car_ids)])
        except Exception as e:
            iface.messageBar().pushMessage("Error", "Most likely, no layer is selected.", level=Qgis.Critical)
            raise e
    def fill_rows_and_columns(self):
        '''
            Fills lists for selection of rows and columns when computing stats.
        '''
        names = self._get_feat_names()

        self.dlg.listRows.addItems([str(x) for x in list(names)])
        self.dlg.listRows.sortItems()

    def fill_layers(self):
        layer_list = QgsProject.instance().layerTreeRoot().children() 
        layers = [lyr.layer() for lyr in layer_list if lyr.layer().geometryType()]      # get LineString layers
        for i, layer in enumerate(layers):
            item = QStandardItem('1. {}'.format(layer.name()))
            self.dlg.layer_sel.model().appendRow(item)
            self.dlg.layer_sel.setItemData(i, str(layer.id()))
        # self.dlg.layer_sel.addItems(layer_names)


    def colour_feature(self, colours, column, renderer, size=0.5, options=[1,2,3]):
        '''
            Set colour by priority and maintenance_method.
            Called on `initial_draw`.
        '''

        def select_new_priority(symbol, renderer, label, expression, color, size=0.5):
            root_rule = renderer.rootRule()
            rule = root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(color)
            rule.symbol().setWidth(size)
            root_rule.appendChild(rule)

        layer = self.iface.activeLayer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        selected = []
        # set the not selected colour
        renderer.rootRule().children()[0].symbol().setColor(QColor(200,200,200,0))
        for i, colour in zip(options,colours):
            QgsMessageLog.logMessage(str(i), 'SnowPlow')
            # selected.append(' \"priority\" NOT LIKE \'% {} %\''.format(str(car.text())))
            select_new_priority(symbol, renderer, '{} {}'.format(column, str(i)), ' \"{}\" LIKE \'%{}%\''.format(column, str(i)), QColor(*colour), size)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def initial_draw(self):
        '''
            Colours edges by priority and maintenance_method
            Sets label to curcuits
        '''
         # set colours
        layer = self.iface.activeLayer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        colour_method = [ (255, 30, 30, 15),(30, 30, 255, 15), (30, 255, 30, 15)]
        colour_priority = [(230, 25, 75), (0, 0, 255), (50, 170, 65)]
        self.colour_feature(colour_priority, 'priority', renderer)
        self.colour_feature(colour_method, 'method', renderer, 2.5, ['sold', 'inert', 'snowplow'])
        self.set_labels()

    def set_labels(self):
        '''
            Sets labels to circuits
        '''
        layer = self.iface.activeLayer()
        tf = QgsTextFormat()

        tf.setFont(QFont("Arial", 10))
        tf.setSize(10)

        ls  = QgsPalLayerSettings()
        ls.setFormat(tf)
        ls.fieldName = "maintaining_car"
        ls.placement = 2
        ls.enabled = True
        ls = QgsVectorLayerSimpleLabeling(ls)

        layer.setLabelsEnabled(True)
        layer.setLabeling(ls)
        layer.triggerRepaint()

    def _reset_selection(self, obj):
        '''
            Resets selection of columns and rows.
        '''
        obj.clearSelection()

    def _apply_transit(self):
        pass
    def _apply_rows_cols(self):
        '''
            Computes statistics.
        '''
        layer = self.iface.activeLayer()
        selected_rows = [x.text() for x in self.dlg.listRows.selectedItems()]

        names = self._get_feat_names()
        possible_columns = ['length','transit_length','maintaining_lenght','length_1','length_2','length_3','remaining_capacity', 'maintaining_capacity']

        # all reasonable (numerical, summable) columns which are not in the rows
        columns = list((set(names).difference(selected_rows)).intersection(set(possible_columns)))

        # get all possible options of each feature in rows
        row_opts = []
        for f in selected_rows:
            options = set()
            for x in layer.getFeatures():
                if x[f]:
                    options.add(x[f])
            row_opts.append(list(options))

        # rows = product of selected rows
        rows = [x for x in product(*row_opts)]

        # create dict with keys like '1,salt'
        table_rows = {}
        for row in rows:
            table_rows[','.join([str(i) for i in row])] = [0.0]*len(columns)

        self.dlg.tableStats.setRowCount(len(rows))
        self.dlg.tableStats.setColumnCount(len(columns))
        self.dlg.tableStats.setHorizontalHeaderLabels(columns)
        self.dlg.tableStats.setVerticalHeaderLabels([' ✕ '.join([str(x) for x in row]) for row in rows])
        # fill the dict  
        for f in layer.getFeatures():
            for i, col in enumerate(columns):
                if f[col] != NULL:
                    try:
                        table_rows[','.join([str(f[x]) for x in selected_rows])][i] += float(f[col])
                    except KeyError as ke:
                        QgsMessageLog.logMessage('Key error 1', 'SnowPlow')

                else:
                    QgsMessageLog.logMessage('fcol je NULL warning', 'SnowPlow')



        for i,k in enumerate(table_rows.keys()):
            for j,v in enumerate(table_rows[k]):
                self.dlg.tableStats.setItem(i,j,QTableWidgetItem(str(v)))

        QgsMessageLog.logMessage(','.join([str(r) for r in rows]), 'SnowPlow')
        QgsMessageLog.logMessage(','.join([str(r) for r in columns]), 'SnowPlow')


    def run(self):
        """Run method that performs all the real work"""
        self.data_holder = DataHolder()

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SnowPlowDialog()
            apply_row_column = self.dlg.row_sel_buttons.button(QDialogButtonBox.Apply)
            apply_row_column.clicked.connect(self._apply_rows_cols)
            reset_row_column_selection = self.dlg.row_sel_buttons.button(QDialogButtonBox.Reset)
            reset_row_column_selection.clicked.connect(partial(self._reset_selection, self.dlg.listRows))

            apply_transit = self.dlg.car_sel_buttons.button(QDialogButtonBox.Apply)
            apply_transit.clicked.connect(self._apply_transit)
            reset_transit = self.dlg.car_sel_buttons.button(QDialogButtonBox.Reset)
            reset_transit.clicked.connect(partial(self._reset_selection, self.dlg.cars))

            self.dlg.refresh.clicked.connect(self.initial_draw)


            self.fill_rows_and_columns()
            self.fill_cars()
            self.fill_layers()

            try:
                self.initial_draw()
            except Exception as e:
                self.iface.messageBar().pushMessage("Error", "Wrong layer is selected.", level=Qgis.Critical)

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
         #   pass
