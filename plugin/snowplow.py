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
from statistics import mean
import statistics
import re
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
        plug_dir = os.path.dirname(__file__)
        path = os.path.join(plug_dir, 'data_holder_settings.json')

        self.colours = [(230, 25, 75, 220), (60, 180, 75, 220), (225, 225, 25, 220), (0, 130, 200, 220), (245, 130, 48, 220), (145, 30, 180, 220), (70, 220, 220, 220), (220, 50, 210, 220)]
        self.current = 0
        self.column_function = {}
        self.column_to_id = {}
        self.funcs = {0: ('sum', lambda x: sum(x)), 1: ('avg', lambda x: mean(x)), 2: ('max',lambda x: max(x)), 3: ('min',lambda x: min(x))}
        self.car_label = 'maintaining_car'
        self.priority_column = 'priority'
        self.transit_column = 'transit_cars'
        self.priority_options = [1,2,3]
        self.method_column = 'method'
        self.method_options = ['sold','inert','snowplow']

        # restore settings if there is any
        if os.path.exists(path):
            self.retore_settings(path)

    def add_column_function(self, column_id, column_name, func_id):
        self.column_to_id[column_name] = column_id
        self.column_function[column_id] = func_id

    def function_for_column(self, column_name):
        return self.funcs[self.column_function[self.column_to_id[column_name]]][1]
    
    def function_for_column_id(self, column_id):
        return self.funcs[self.column_function[column_id]][1]

    def function_name_for_column(self, column_name):
        return self.funcs[self.column_function[self.column_to_id[column_name]]][0]

    def next_colour(self):
        self.current = (self.current + 1) % len(self.colours)
        return QColor(*self.colours[self.current])

    def reset(self):
        self.column_function = {}
        self.column_to_id = {}

    def restore_settings(self, path):
        self.priority_column = 'priority'
        self.transit_column = 'transit_cars'
        self.priority_options = [1,2,3]
        self.method_column = 'method'
        self.method_options = ['sold','inert','snowplow']






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


    def msg(self, msg):
        QgsMessageLog.logMessage(str(msg), 'SnowPlow')

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

    def get_layer(self):
        '''
            returns currently selected layer
        '''
        layer = QgsProject.instance().mapLayer(self.dlg.layer_sel.currentData())
        if not layer:
            self.iface.messageBar().pushMessage("Error", "No layer is selected.", level=Qgis.Critical)
        else:
            return layer

    def _get_feat_names(self):
        '''
            return the names and types of features of selected layer
        '''
        layer = self.get_layer()
        fs = layer.getFeatures()
        f = next(fs)
        return list(set([(x.name(), x.typeName()) for x in f.fields()]))

    def fill_cars(self):
        '''
            Fill list of cars for transits highlighting.
        '''
        self.dlg.cars.clear()

        layer = self.get_layer()
        car_ids = set()
        try:
            for f in layer.getFeatures():
                if 'car' in f['id']:
                    car_ids.add(f['id'])

            car_ids = sorted(car_ids)
            self.dlg.cars.addItems([str(x) for x in list(car_ids)])
        except Exception as e:
            self.iface.messageBar().pushMessage("Warning", "Most likely, selected layer contains no cars.")
            raise e

    def fill_rows(self):
        '''
            Fills lists for selection of rows and columns when computing stats.
        '''
        self.dlg.listRows.clear()
        names = self._get_feat_names()


        self.dlg.listRows.addItems([str(x[0]) for x in list(names) if x[1] in ['Integer', 'String', 'Boolean']])
        self.dlg.listRows.sortItems()


    def layer_changed(self, i):
        '''
            Layer has been changed in the selection.
        '''
        self.reset_data(self.data_holder)
        if not self.first_start:
            self.fill_column_sel()
            self.fill_func_sel()
            self.fill_rows()
            self.fill_cars()

    def column_sel_changed(self, i):
        '''
            Display function to selected column
        '''

        self.msg(self.data_holder.column_function)
        if i != -1:
            func_id = self.data_holder.column_function[i]
            self.dlg.func_sel.setCurrentIndex(func_id)

    def func_sel_changed(self, i):
        '''
            Stores new, selected function for current column
        '''
        self.data_holder.column_function[self.dlg.column_sel.currentIndex()] = i

    def reset_data(self, data_holder):
        '''
            Resets data_holder and fills again the combobox with columns
            Usually called when layer is changed.
        '''
        data_holder.reset()
        names_col = self._get_feat_names()
        columns = [x[0] for x in names_col if x[1] in ['Integer', 'Real']]

        for i,c in enumerate(sorted(columns)):
            data_holder.add_column_function(i,c, 0)   # 0 = 'sum' function

 
    def fill_layers(self):
        '''
            Fills the list with LineString layers.
        '''
        layer_list = QgsProject.instance().layerTreeRoot().findLayers()
        layers = [lyr.layer() for lyr in layer_list if lyr.layer().geometryType()]      # get LineString layers

        for i, layer in enumerate(layers):
            item = QStandardItem('{}. {}'.format(i, layer.name()))
            self.dlg.layer_sel.model().appendRow(item)
            self.dlg.layer_sel.setItemData(i, str(layer.id()))

    def fill_column_sel(self):
        '''
            Fills ComboBox with the names of columns on which statisctics may be applied
        '''
        self.dlg.column_sel.clear()
        names_col = self._get_feat_names()
        columns = [x[0] for x in names_col if x[1] in ['Integer', 'Real']]

        for i,c in enumerate(sorted(columns)):
            self.dlg.column_sel.addItem(c)
            self.data_holder.add_column_function(i,c, 0)   # 0 = 'sum' function


    def fill_func_sel(self):
        '''
            Fills ComboBox with the names or function to be applied on column 
        '''
        self.dlg.func_sel.clear()
        for i in self.data_holder.funcs.keys():
            self.dlg.func_sel.addItem(self.data_holder.funcs[i][0])


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

        layer = self.get_layer()
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

    def initial_colours_draw(self):
        '''
            Colour lines in the map
        '''
        layer = self.get_layer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        self.renderer = QgsRuleBasedRenderer(symbol)
        colour_method = [ (255, 30, 30, 15),(30, 30, 255, 15), (30, 255, 30, 15)]
        colour_priority = [(230, 25, 75), (0, 0, 255), (50, 170, 65)]
        self.colour_feature(colour_priority, self.data_holder.priority_column, self.renderer, options=self.data_holder.priority_options)
        self.colour_feature(colour_method, self.data_holder.method_column, self.renderer, 2.5, options=self.data_holder.method_options)

    def initial_draw(self):
        '''
            Colours edges by priority and maintenance_method
            Sets label to curcuits
        '''
         # set colours
        layer = self.get_layer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        self.renderer = QgsRuleBasedRenderer(symbol)

        self.initial_colours_draw()
        self.set_labels()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def set_labels(self):
        '''
            Sets labels to circuits
        '''
        layer = self.get_layer()
        tf = QgsTextFormat()

        tf.setFont(QFont("Arial", 10))
        tf.setSize(10)

        ls  = QgsPalLayerSettings()
        ls.setFormat(tf)
        ls.fieldName = self.data_holder.car_label 
        ls.placement = 2
        ls.enabled = True
        ls = QgsVectorLayerSimpleLabeling(ls)

        layer.setLabelsEnabled(True)
        layer.setLabeling(ls)
        layer.triggerRepaint()

    def select_new_transit(self, symbol, renderer, label, expression, color, size=4.0):
        root_rule = renderer.rootRule()
        rule = root_rule.children()[0].clone()
        rule.setLabel(label)
        rule.setFilterExpression(expression)
        rule.symbol().setColor(color)
        rule.symbol().setWidth(size)
        root_rule.appendChild(rule)


    def _apply_transit(self):
        '''
            Colour transits of selected cars.
        '''
        self.initial_colours_draw()

        selected_cars_texts = [x.text() for x in self.dlg.cars.selectedItems()]
        selected_cars = [re.sub(r'[^\d]+', '', x) for x in selected_cars_texts]

        layer = self.get_layer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        colour = QColor(0,255,0)

        exprs = []
        for t, car in zip(selected_cars_texts, selected_cars):
            expr = 'regexp_match( "{}", \'((^)|(.*,)){}((,.*)|($))\')'.format(self.data_holder.transit_column, str(car))
            exprs.append(expr)
            # select_new_transit(symbol, self.renderer, t, ' or '.join(exprs), colour)
            self.select_new_transit(symbol, self.renderer, t, expr, colour)

        QgsMessageLog.logMessage(str(' OR '.join(exprs)), 'SnowPlow')

        layer.setRenderer(self.renderer)
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())


    def _all_transits(self):
        '''
            Adds new rule to the renderer to highlight all transits.
        '''
        layer = self.get_layer()
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        colour = QColor(0,255,0)

        expr = '"{}" IS NOT NULL AND "{}" != \'\''.format(self.data_holder.transit_column, self.data_holder.transit_column)
        self.select_new_transit(symbol, self.renderer, 'Transits', expr, colour)
        layer.setRenderer(self.renderer)
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def _reset_selection_cars(self):
        '''
            Resets selection of columns and rows.
        '''
        self.dlg.cars.clearSelection()
        self.initial_draw()


    def _reset_selection_columns(self):
        '''
            Resets selection of columns and rows.
        '''
        self.dlg.listRows.clearSelection()


    def _apply_rows_cols(self):
        '''
            Computes statistics and diplays them in tableview
        '''
        self.dlg.tableStats.clear()

        layer = self.get_layer()
        selected_rows = [x.text() for x in self.dlg.listRows.selectedItems()]

        names_col = self._get_feat_names()
        names = [x[0] for x in names_col]

        # all reasonable (numerical, summable) columns which are not in the rows
        columns = sorted([x[0] for x in names_col if x[1] in ['Integer', 'Real'] and x[0] not in selected_rows])
        # columns = list((set(names).difference(selected_rows)).intersection(set(possible_columns)))

        # get all possible options of each feature in rows
        row_opts = []
        for f in selected_rows:
            options = set()
            for x in layer.getFeatures():
                if x[f] != NULL:
                    options.add(x[f])
            row_opts.append(list(options))

        # rows = product of selected rows
        rows = sorted([x for x in product(*row_opts)])

        table_rows = {}     # Value for each row X column after func has bee applied
        to_func = {}        # Accumulated values for each row X column
        use_row = {}        # Does the row contain any useful info?
        feature_count = {}  # Number of rows (features) in the original file for each of the computer row
        use_col = {}        # Does the column contain any useful info?

        # Initialize lists and dicts
        for row in rows:
            row_key = ','.join([str(i) for i in row])
            table_rows[row_key] = {}
            to_func[row_key] = {}
            for col in columns:
                to_func[row_key][col] = []
                table_rows[row_key][col] = None
            use_row[row_key] = False
            feature_count[row_key] = 0
        for col in columns:
            use_col[col] = False

        # accumulate values for each row X column
        for f in layer.getFeatures():
            row_key = ','.join([str(f[x]) for x in selected_rows]) 
            if 'NULL' in row_key:
                continue
            # if the previous statement does not fail, use row
            use_row[row_key] = True
            feature_count[row_key] += 1
            for col in columns:
                if f[col] != NULL:
                    to_func[row_key][col].append(float(f[col]))

        # apply function to accumulated list for each row X column
        for row_key in to_func.keys():
            if use_row[row_key]:
                for col in columns:
                    if len(to_func[row_key][col]) != 0:
                        use_col[col] = True
                        func = self.data_holder.function_for_column(col)
                        try:
                            table_rows[row_key][col] = func(to_func[row_key][col])
                        except ValueError as e:
                            raise e

        row_count = len([1 for x in use_row.keys() if use_row[x]]) + 1          # + 1 for final row
        self.dlg.tableStats.setRowCount(row_count)

        # create translation from id to row name 
        row_to_id = {}
        id_to_row = []
        i = 0
        for row_key in to_func.keys():
            if use_row[row_key]:
                row_to_id[row_key] = i
                id_to_row.append(row_key)
                i += 1

        # create names for the vertical header
        vertical_header = []
        for index in range(len(id_to_row)):
            for row in rows:
                if use_row[id_to_row[index]] and ','.join([str(x) for x in row]) == id_to_row[index]:
                    vertical_header.append(' ✕ '.join([str(x) for x in row]))


        vertical_header.append('TOTAL')
        self.dlg.tableStats.setVerticalHeaderLabels(vertical_header)
        self.msg(vertical_header)

        # create translation from id to row name 
        col_to_id = {}
        id_to_col = []
        i = 0
        for col in columns:
            if use_col[col]:
                col_to_id[col] = i
                id_to_col.append(col)
                i += 1

        # create names for horizontal header
        self.dlg.tableStats.setColumnCount(len([1 for index in range(len(id_to_col)) if use_col[id_to_col[index]]]) + 1)
        horizontal_func_cols = ['{}({})'.format(self.data_holder.function_name_for_column(id_to_col[index]),id_to_col[index]) for index in range(len(id_to_col)) if use_col[id_to_col[index]]]
        horizontal_func_cols.append('# ROWS')
        self.dlg.tableStats.setHorizontalHeaderLabels(horizontal_func_cols)

        # fill in the (ui) table
        for row_index in range(len(id_to_row)):
            row_key = id_to_row[row_index]
            if use_row[row_key]:
                for col_index in range(len(id_to_col)):
                    col_key = id_to_col[col_index]
                    v = '---' if table_rows[row_key][col_key] is None else '{:.2f}'.format(float(table_rows[row_key][col_key]))         # if there is no value for given field, write '---'
                    item = QTableWidgetItem()
                    item.setData(Qt.DisplayRole, QVariant(v))
                    self.dlg.tableStats.setItem(row_index,col_index,item)
                item = QTableWidgetItem()
                item.setData(Qt.DisplayRole, QVariant('{}'.format(feature_count[row_key])))
                self.dlg.tableStats.setItem(row_index, len(id_to_col), item)



        # final row = last_row[column] = func(value[row=1...n][column]) where func is sum, avg, min, max, ..
        for col_index in range(len(id_to_col)):
            col_key = id_to_col[col_index]
            ls = []
            for row_index in range(len(id_to_row)):
                row_key = id_to_row[row_index]
                if use_row[row_key]:
                    ls.extend(to_func[row_key][col_key])
            if len(ls) != 0:
                func = self.data_holder.function_for_column(col_key)
                v = func(ls)
                item = QTableWidgetItem()
                item.setData(Qt.DisplayRole, QVariant('{:.2f}'.format(float(v))))
                self.dlg.tableStats.setItem(len(id_to_row), col_index, item)


        # bottom right corner, sum  
        item = QTableWidgetItem()
        item.setData(Qt.DisplayRole, QVariant('{}'.format(int(sum([feature_count[k] for k in feature_count.keys()])))))
        self.dlg.tableStats.setItem(len(id_to_row), len(id_to_col), item)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.data_holder = DataHolder()
            self.dlg = SnowPlowDialog()
            self.fill_layers()

            # Init of buttons
            apply_row_column = self.dlg.row_sel_buttons.button(QDialogButtonBox.Apply)
            apply_row_column.clicked.connect(self._apply_rows_cols)
            reset_row_column_selection = self.dlg.row_sel_buttons.button(QDialogButtonBox.Reset)
            reset_row_column_selection.clicked.connect(self._reset_selection_columns)
            apply_transit = self.dlg.car_sel_buttons.button(QDialogButtonBox.Apply)
            apply_transit.clicked.connect(self._apply_transit)
            reset_transit = self.dlg.car_sel_buttons.button(QDialogButtonBox.Reset)
            reset_transit.clicked.connect(self._reset_selection_cars)
            all_transit = self.dlg.car_sel_buttons.button(QDialogButtonBox.YesToAll)
            all_transit.clicked.connect(self._all_transits)
            self.dlg.refresh.clicked.connect(self.initial_draw)

            layer = self.get_layer()
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            self.renderer = QgsRuleBasedRenderer(symbol)

            # Init of UI elements
            self.fill_column_sel()
            self.fill_func_sel()
            self.fill_rows()
            self.fill_cars()
            self.dlg.layer_sel.currentIndexChanged.connect(self.layer_changed)
            self.dlg.column_sel.currentIndexChanged.connect(self.column_sel_changed)
            self.dlg.func_sel.currentIndexChanged.connect(self.func_sel_changed)
            self.first_start = False


        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
         #   pass
