from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QColorDialog, QListWidgetItem, QMessageBox, QDialogButtonBox
import wfdb
import numpy as np
import sys
from pyqtgraph.Qt import QtCore
from PyQt6 import QtWidgets, uic
import pyqtgraph as pg
import csv
from fpdf import FPDF
from pyqtgraph.exporters import ImageExporter
import os
import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon
import qdarkstyle

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # "graph1":[[(time,data),end_index],[....]] Each list in the nested lists represent a signal
        self.signals = {"graph1": [], "graph2": []}
        # contain the line plots for each graph ordered by insertion
        self.signals_lines = {"graph1": [], "graph2": []}
        # {"graph1": [[visibility_flag,color,label],[....]],"graph2": [[...]]}
        self.signals_info = {"graph1": [], "graph2": []}

        self.channels_color = {'graph1': [], 'graph2': []}

        self.graph1_signals_paths = []
        self.graph2_signals_paths = []

        # Play/Pause State
        self.is_playing = [{"graph": "graph1", "is_playing": True}, {
            "graph": "graph2", "is_playing": False}]

        # Link Mode
        self.sourceGraph = "both"  # flag for link mode
        self.graph_mapping = {"graph1": 0, "graph2": 1, "both": 2}

        self.transfer_button1_state = False
        self.transfer_button2_state = False

        # Other Attributes
        self.data_index = {"graph1": 5, "graph2": 5}
        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)

        # Initialize the UI
        self.init_ui()

    def init_ui(self):
        # Load the UI Page
        self.ui = uic.loadUi('ui/mainwindow.ui', self)
        self.setWindowTitle("Multi-Channel Signal Viewer")
        self.setWindowIcon(QIcon("assets/Icons/ECG.png"))
        self.lookup = {"graph1": self.graph1, "graph2": self.graph2}
        self.current_graph = self.graph1  # default value
        self.current_graph.clear()

        # to know what the channels I selected in each combobox
        # None will be int, 0 --> all signals, 1 --> the end (each channel individually)
        self.channels_selected = {"graph1": 0, "graph2": 0}

        self.snapshoot_data = []
        self.stat_lst = []

        self.channelsGraph1.addItem("All Channels")
        self.channelsGraph2.addItem("All Channels")

        # Set labels and grid visibility for graphs
        self.graph1.setLabel("bottom", "Time")
        self.graph1.setLabel("left", "Amplitude")
        self.graph2.setLabel("bottom", "Time")
        self.graph2.setLabel("left", "Amplitude")
        self.graph1.showGrid(x=True, y=True)
        self.graph2.showGrid(x=True, y=True)

        # Connect signals to slots
        self.timer.timeout.connect(self.update_plot_data)
        self.importButton.clicked.connect(self.browse)
        self.reportButton.clicked.connect(self.generate_signal_report)
        self.playButton.clicked.connect(self.toggle_play_pause)
        self.linkButton.clicked.connect(self.link_graphs)
        self.clearButton.clicked.connect(self.clear_graph)
        self.rewindButton.clicked.connect(self.rewind_graph)
        self.zoomIn.clicked.connect(self.zoom_in)
        self.zoomOut.clicked.connect(self.zoom_out)
        self.snapShoot_Button.clicked.connect(self.take_snapshot)

        # Set speed slider properties
        self.speedSlider.setMinimum(0)
        self.speedSlider.setMaximum(100)
        self.speedSlider.setSingleStep(5)
        self.speedSlider.setValue(self.data_index[self.get_graph_name()])
        self.speedSlider.valueChanged.connect(self.change_speed)

        # Connect color buttons to channel color picking
        self.colorButtonGraph1.clicked.connect(self.pick_channel_color)
        self.colorButtonGraph2.clicked.connect(self.pick_channel_color)

        # Connect graph selection combo box to graph change
        self.graphSelection.currentIndexChanged.connect(
            self.update_selected_graph)

        # Connect channel combo boxes to channel change
        self.channelsGraph1.currentIndexChanged.connect(
            lambda i, graph="graph1": self.handle_selected_channels_change(graph, i))
        self.channelsGraph2.currentIndexChanged.connect(
            lambda i, graph="graph2": self.handle_selected_channels_change(graph, i))

        # Connect delete buttons to channel deletion
        self.deleteButtonGraph1.clicked.connect(self.delete_selected_ch)
        self.deleteButtonGraph2.clicked.connect(self.delete_selected_ch)

        # Connect label text input to channel label change
        self.addLabelGraph1.returnPressed.connect(self.change_channel_label)
        self.addLabelGraph2.returnPressed.connect(self.change_channel_label)

        # Connect hide list items to item checking/unchecking
        self.hideList1.itemChanged.connect(self.on_item_checked)
        self.hideList2.itemChanged.connect(self.on_item_checked)
        self.hideList1.itemChanged.connect(self.on_item_unchecked)
        self.hideList2.itemChanged.connect(self.on_item_unchecked)

        self.transferButtonGraph1_2.clicked.connect(self.button1_clicked)
        self.transferButtonGraph2_1.clicked.connect(self.button2_clicked)
        self.transferButtonGraph1_2.clicked.connect(self.transfer_signal)
        self.transferButtonGraph2_1.clicked.connect(self.transfer_signal)

        # Connect label text input to adding legends
        self.addLabelGraph1.returnPressed.connect(
            lambda: self.add_legend("graph1"))
        self.addLabelGraph2.returnPressed.connect(
            lambda: self.add_legend("graph2"))

        # Create shortcuts for actions
        self.create_shortcuts()

    def create_shortcuts(self):
        # Create a shortcut for the Import button
        import_shortcut = QShortcut(QKeySequence('Ctrl+O'), self)
        import_shortcut.activated.connect(self.browse)

        # Create a shortcut for the snapshoot button
        report_shortcut = QShortcut(QKeySequence('Ctrl+S'), self)
        report_shortcut.activated.connect(self.take_snapshot)

        # Create a shortcut for the REPORT button
        report_shortcut = QShortcut(QKeySequence('Ctrl+P'), self)
        report_shortcut.activated.connect(self.generate_signal_report)

        # Create a shortcut for the play button
        paly_shortcut = QShortcut(Qt.Key.Key_Space, self)
        paly_shortcut.activated.connect(self.toggle_play_pause)

        # Create a shortcut for the rewind button
        rewind_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        rewind_shortcut.activated.connect(self.rewind_graph)

        # Create a shortcut for the link button
        link_shortcut = QShortcut(QKeySequence('Ctrl+L'), self)
        link_shortcut.activated.connect(self.link_graphs)

        # Create a shortcut for the clear button
        clear_shortcut = QShortcut(QKeySequence('Ctrl+C'), self)
        clear_shortcut.activated.connect(self.clear_graph)


# ************************************** HELPER FUNCTIONS **************************************

    def button1_clicked(self):
        self.transfer_button1_state = True

    def button2_clicked(self):
        self.transfer_button2_state = True

    def get_curr_graph_channels(self):
        if self.get_graph_name() == "graph1":
            return self.channelsGraph1
        else:
            return self.channelsGraph2

    def get_curr_graph_list(self):
        if self.get_graph_name() == "graph1":
            return self.fill_list1()
        else:
            return self.fill_list2()

    def clear_curr_graph_list(self):
        if self.get_graph_name() == "graph1":
            return self.hideList1.clear()
        else:
            return self.hideList2.clear()

    def get_graph_paths(self):
        if self.get_graph_name() == "graph1":
            return self.graph1_signals_paths
        else:
            return self.graph2_signals_paths

    def set_icon(self, icon_path):
        # Load an icon
        icon = QIcon(icon_path)
        # Set the icon for the button
        self.playButton.setIcon(icon)

    def fill_list1(self):
        self.hideList1.clear()
        for i in range(self.channelsGraph1.count()-1):
            text = self.channelsGraph1.itemText(i+1)
            item = QListWidgetItem(text)
            item.setCheckState(Qt.CheckState.Checked)
            self.hideList1.addItem(item)

    def fill_list2(self):
        self.hideList2.clear()
        for i in range(self.channelsGraph2.count()-1):
            text = self.channelsGraph2.itemText(i+1)
            item = QListWidgetItem(text)
            item.setCheckState(Qt.CheckState.Checked)
            self.hideList2.addItem(item)

    def get_unchecked_indexes(self, listWidget):
        unchecked_indexes = []
        for i in range(listWidget.count()):
            item = listWidget.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                unchecked_indexes.append(i)
        return unchecked_indexes

    def get_checked_indexes(self, listWidget):
        checked_indexes = []
        for i in range(listWidget.count()):
            item = listWidget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_indexes.append(i)
        return checked_indexes

    def on_item_unchecked(self):
        unchecked_indexes_list1 = self.get_unchecked_indexes(self.hideList1)
        for index in unchecked_indexes_list1:
            self.signals_lines['graph1'][index].setPen((0, 0, 0))
        unchecked_indexes_list2 = self.get_unchecked_indexes(self.hideList2)
        for index in unchecked_indexes_list2:
            self.signals_lines['graph2'][index].setPen((0, 0, 0))

    def on_item_checked(self):
        checked_indexes_list1 = self.get_checked_indexes(self.hideList1)
        for index in checked_indexes_list1:
            self.signals_lines['graph1'][index].setPen(
                self.channels_color['graph1'][index])
        checked_indexes_list2 = self.get_checked_indexes(self.hideList2)
        for index in checked_indexes_list2:
            self.signals_lines['graph2'][index].setPen(
                self.channels_color['graph2'][index])

    def show_error_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec()

    def sudden_appearing(self, graph, j):
        (time, data), end_ind = self.signals[graph][j]
        signal_line = self.signals_lines[graph][j]
        X = time[:end_ind]
        Y = data[:end_ind]
        signal_line.setData(X, Y, visible=True)

    def sudden_disappearing(self, graph, j):
        self.signals_lines[graph][j].setData([], [], visible=False)

    def handle_selected_channels_change(self, graph, i):
        self.channels_selected[graph] = i

        if self.channels_selected[graph] == 0:
            for j in range(len(self.signals_lines[graph])):
                self.signals_info[graph][j][0] = True
                self.sudden_appearing(graph, j)

        else:
            selected_channel_index = self.channels_selected[graph] - 1
            for j in range(len(self.signals_lines[graph])):
                if j == selected_channel_index:
                    self.signals_info[graph][j][0] = True
                    # sudden appearing
                    self.sudden_appearing(graph, j)

                else:
                    self.signals_info[graph][j][0] = False
                    # sudden disappearing
                    self.sudden_disappearing(graph, j)

    def initialize_data(self,):
        if (self.current_graph == self.graph1):
            self.signals["graph1"] = []
            self.signals_lines["graph1"] = []
        elif (self.current_graph == self.graph2):
            self.signals["graph2"] = []
            self.signals_lines["graph2"] = []
        else:
            self.signals = {"graph1": [], "graph2": []}
            self.signals_lines = {"graph1": [], "graph2": []}

    def update_selected_graph(self, index):
        if index == 0:  # to graph1
            self.current_graph = self.graph1
            self.speedSlider.setValue(self.data_index["graph1"])
            # graph2 is playing and graph1 is not
            if self.is_playing[1]["is_playing"] and self.is_playing[0]["is_playing"] == False:
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")
            # graph2 is not playing and graph1 is not
            elif self.is_playing[1]["is_playing"] == False and self.is_playing[0]["is_playing"] == False:
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")
            # graph2 is playing graph1 is playing
            elif self.is_playing[1]["is_playing"] and self.is_playing[0]["is_playing"]:
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
            # graph2 is not playing and graph1 is playing
            elif self.is_playing[1]["is_playing"] == False and self.is_playing[0]["is_playing"]:
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")

        elif index == 1:
            self.current_graph = self.graph2  # to graph2
            self.speedSlider.setValue(self.data_index["graph2"])
            # graph2 is playing and graph1 is not
            if self.is_playing[1]["is_playing"] and self.is_playing[0]["is_playing"] == False:
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
            # graph2 is not playing and graph1 is not
            elif self.is_playing[1]["is_playing"] == False and self.is_playing[0]["is_playing"] == False:
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")
            # graph2 is playing graph1 is playing
            elif self.is_playing[1]["is_playing"] and self.is_playing[0]["is_playing"]:
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
            # graph2 is not playing and graph1 is playing
            elif self.is_playing[1]["is_playing"] == False and self.is_playing[0]["is_playing"]:
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")

        elif index == 2:
            self.current_graph = [self.graph1, self.graph2]
            self.data_index["graph2"] = 5
            self.data_index["graph1"] = 5
            self.speedSlider.setValue(self.data_index["graph1"])
            for graph in self.is_playing:
                graph["is_playing"] = True

    def get_index(self):
        index = self.channelsGraph1.currentIndex()
        return index

    def generate_random_color(self):
        while True:
            # Generate random RGB values
            red = random.randint(0, 255)
            green = random.randint(0, 255)
            blue = random.randint(0, 255)

            # Calculate brightness using a common formula
            brightness = (red * 299 + green * 587 + blue * 114) / 1000

            # Check if the color is not too light (adjust the threshold as needed)
            if brightness > 100:
                return red, green, blue

    def get_graph_name(self):
        if self.current_graph == self.graph1:
            return "graph1"
        elif self.current_graph == self.graph2:
            return "graph2"
        else:
            return self.sourceGraph


# ************************************** Plot Graphs **************************************


    def browse(self):
        file_filter = "Raw Data (*.csv *.txt *.xls *.hea *.dat *.rec)"
        self.file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, 'Open Signal File', './', filter=file_filter)

        if self.current_graph == self.graph1 and self.file_path:

            self.graph1_signals_paths.append(self.file_path)

            self.channelsGraph1.addItem(
                f"Channel{len(self.signals['graph1']) + 1}")

            self.fill_list1()

            self.signals_info["graph1"].append([True, None, None])

        elif self.current_graph == self.graph2 and self.file_path:

            self.graph2_signals_paths.append(self.file_path)

            self.channelsGraph2.addItem(
                f"Channel{len(self.signals['graph2']) + 1}")
            self.fill_list2()

            self.signals_info["graph2"].append([True, None, None])
        elif self.current_graph == [self.graph1, self.graph2] and self.file_path:

            self.graph1_signals_paths.append(self.file_path)
            self.graph2_signals_paths.append(self.file_path)

            self.channelsGraph1.addItem(
                f"Channel{len(self.signals['graph1']) + 1}")
            self.fill_list1()

            self.channelsGraph2.addItem(
                f"Channel{len(self.signals['graph2']) + 1}")
            self.fill_list2()

            self.signals_info["graph1"].append([True, None, None])
            self.signals_info["graph2"].append([True, None, None])

        if self.file_path:
            self.open_file(self.file_path)

    def open_file(self, path: str):
        self.time = []
        self.data = []
        # Initialize the sampling frequency
        self.fsampling = 1

        # Extract the file extension (last 3 characters) from the path
        filetype = path[-3:]

        # Check if the file type is one of "hea," "rec," or "dat"
        if filetype in ["hea", "rec", "dat"]:
            # Read the WFDB record
            self.record = wfdb.rdrecord(path[:-4], channels=[0])

            # Extract the signal data
            self.data = np.concatenate(self.record.p_signal)

            # Update the sampling frequency
            self.fsampling = self.record.fs

            # Generate time values for each sample (sampling interval x its multiples)
            self.time = np.arange(len(self.data)) / self.fsampling

        # Check if the file type is CSV, text (txt), or Excel (xls)
        if filetype in ["csv", "txt", "xls"]:
            # Open the data file for reading ('r' mode)
            with open(path, 'r') as data_file:
                # Create a CSV reader object with comma as the delimiter
                data_reader = csv.reader(data_file, delimiter=',')

                # Iterate through each row (line) in the data file
                for row in data_reader:
                    # Extract the time value from the first column (index 0)
                    time_value = float(row[0])

                    # Extract the amplitude value from the second column (index 1)
                    amplitude_value = float(row[1])

                    # Append the time and amplitude values to respective lists
                    self.time.append(time_value)
                    self.data.append(amplitude_value)

        self.data_x = []
        self.data_y = []

        if self.current_graph == self.graph1:
            # self.validate_dublicates('graph1',signal_data[0][1])

            self.signals["graph1"].append(
                [(self.time, self.data), 50])
            self.is_playing[0]["is_playing"] = True
            self.playButton.setText('Pause')
            self.set_icon("Icons/pause.svg")
            self.plot_graph_signal()

        elif self.current_graph == self.graph2:

            self.signals["graph2"].append(
                [(self.time, self.data), 50])
            self.is_playing[1]["is_playing"] = True
            self.playButton.setText('Pause')
            self.set_icon("Icons/pause.svg")
            self.plot_graph_signal()

        else:  # link mode

            if self.sourceGraph == "both":
                self.signals["graph1"].append(
                    [(self.time, self.data), 50])

                self.is_playing[0]["is_playing"] = True
                self.signals["graph2"].append(
                    [(self.time, self.data), 50])

                self.is_playing[1]["is_playing"] = True
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
                self.plot_common_linked_signal()

            elif self.sourceGraph == "graph1":
                self.signals["graph1"].append(
                    [(self.time, self.data), 50])

                self.is_playing[0]["is_playing"] = True
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
                self.plot_unique_linked_signal()

            elif self.sourceGraph == "graph2":
                self.signals["graph2"].append(
                    [(self.time, self.data), 50])

                self.is_playing[1]["is_playing"] = True
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
                self.plot_unique_linked_signal()

    def plot_graph_signal(self):
        if len(self.signals[self.get_graph_name()]) == 1:  # first plot in the graph
            # Create a pen with the generated color
            pen = pg.mkPen((self.generate_random_color()))
            self.data_x = self.time[:50]
            self.data_y = self.data[:50]
            curve = self.current_graph.plot(
                self.data_x, self.data_y, pen=pen)
            self.signals_lines[self.get_graph_name()].append(curve)
            self.channels_color[self.get_graph_name()].append(pen)
            self.signals_info[self.get_graph_name()][0][1] = pen
        else:  # other plots in the graph have been added
            pen = pg.mkPen((self.generate_random_color()))
            curr_index = len(self.signals[self.get_graph_name()]) - 1
            end_ind = self.signals[self.get_graph_name()][0][1]
            self.signals[self.get_graph_name()][-1] = [(self.time,
                                                        self.data), end_ind]
            self.data_x = self.time[:end_ind]
            self.data_y = self.data[:end_ind]
            curve = self.current_graph.plot(self.data_x, self.data_y, pen=pen)
            self.signals_lines[self.get_graph_name()].append(curve)
            self.channels_color[self.get_graph_name()].append(pen)
            self.signals_info[self.get_graph_name()][curr_index][1] = pen

        if not self.timer.isActive():
            self.timer.start(50)

    def plot_common_linked_signal(self):
        for i, graph_name in enumerate(["graph1", "graph2"]):
            if len(self.signals[graph_name]) == 1:  # first plot in the graph
                if self.signals_info[graph_name][0][1] == None:
                    pen = pg.mkPen((self.generate_random_color()))
                    self.channels_color[graph_name].append(pen)
                    self.signals_info[graph_name][0][1] = pen
                else:
                    pen = self.channels_color[graph_name][0]

                self.data_x = self.time[:50]
                self.data_y = self.data[:50]
                curve = self.current_graph[i].plot(
                    self.data_x, self.data_y, pen=pen)
                self.signals_lines[graph_name].append(curve)

            else:  # other plots in the graph have been added
                curr_index = len(self.signals[graph_name]) - 1

                if self.signals_info[graph_name][i][1] == None:
                    pen = pg.mkPen((self.generate_random_color()))
                    self.signals_info[graph_name][curr_index][1] = pen
                    self.channels_color[graph_name].append(pen)
                else:
                    pen = self.signals_info[graph_name][curr_index][1]
                    pen = self.channels_color[graph_name][curr_index]

                end_ind = self.signals[graph_name][0][1]
                self.signals[graph_name][-1] = [(self.time,
                                                 self.data), end_ind]
                self.data_x = self.time[:end_ind]
                self.data_y = self.data[:end_ind]
                curve = self.current_graph[i].plot(
                    self.data_x, self.data_y, pen=pen)
                self.signals_lines[graph_name].append(curve)

            if not self.timer.isActive():
                self.timer.start(50)

    def plot_unique_linked_signal(self):
        if len(self.signals[self.get_graph_name()]) == 1:  # first plot in the graph
            pen = self.channels_color[self.get_graph_name()][0]
            self.data_x = self.time[:50]
            self.data_y = self.data[:50]
            curve = self.lookup[self.get_graph_name()].plot(
                self.data_x, self.data_y, pen=pen)
            self.signals_lines[self.get_graph_name()].append(curve)
        else:  # other plots in the graph have been added
            curr_index = len(self.signals[self.get_graph_name()]) - 1
            pen = self.channels_color[self.get_graph_name()][curr_index]

            end_ind = self.signals[self.get_graph_name()][0][1]
            self.signals[self.get_graph_name()][-1] = [(self.time,
                                                        self.data), end_ind]
            self.data_x = self.time[:end_ind]
            self.data_y = self.data[:end_ind]
            curve = self.lookup[self.get_graph_name()].plot(
                self.data_x, self.data_y, pen=pen)
            self.signals_lines[self.get_graph_name()].append(curve)

        if not self.timer.isActive():
            self.timer.start(50)

    def update_plot_data(self):
        for item in self.is_playing:
            if item["is_playing"]:
                self.updating_graphs(item["graph"])

    def updating_graphs(self, graph: str):
        for i, signal in enumerate(self.signals[graph]):
            (time, data), end_ind = signal
            signal_line = self.signals_lines[graph][i]

            X = time[:end_ind + self.data_index[graph]]
            Y = data[:end_ind + self.data_index[graph]]
            self.signals[graph][i] = [
                (time, data), end_ind + self.data_index[graph]]
            if (X[-1] < time[-1] / 5):
                self.lookup[graph].setXRange(0, time[-1] / 5)
            else:
                self.lookup[graph].setXRange(
                    X[-1] - time[-1] / 5, X[-1])

            if self.signals_info[graph][i][0]:  # error
                signal_line.setData(X, Y, visible=True)
                last_data = self.get_last_data_point(graph)[0]
                self.lookup[graph].setLimits(xMin=0, xMax=last_data)
            else:
                signal_line.setData([], [], visible=False)

    def link_graphs(self):
        self.update_selected_graph(2)
        self.graphSelection.setCurrentIndex(2)
        for graph in self.is_playing:
            graph["is_playing"] = True


# ************************************** Transfer signals **************************************

    def update_after_transfer(self, curr_graph, i, item_names):
        if i == 0:
            self.get_curr_graph_channels().clear()
            self.clear_curr_graph_list()
            self.get_curr_graph_channels().addItem(item_names[0])
            self.get_curr_graph_list()
            for i in range(len(self.signals[curr_graph])):
                self.signals[curr_graph][i][1] = self.signals[curr_graph][0][1]
            for i, signal in enumerate(self.signals[curr_graph]):
                pen = self.channels_color[curr_graph][i]
                (time, data), end_ind = signal
                X = time[:end_ind]
                Y = data[:end_ind]
                curve = self.current_graph.plot(X, Y, pen=pen)
                self.signals_lines[curr_graph][i] = curve
                self.get_curr_graph_channels().addItem(
                    item_names[i+1])  # combobox refill
                self.get_curr_graph_list()
            if not self.timer.isActive():
                self.timer.start(50)
        else:
            if curr_graph == "graph1":
                self.channelsGraph1.addItem(item_names)
                self.fill_list1()
            else:
                self.channelsGraph2.addItem(item_names)
                self.fill_list2()
            for item in self.is_playing:
                if item["is_playing"]:
                    for i in range(len(self.signals[item["graph"]])):
                        self.signals[item["graph"]
                                     ][i][1] = self.signals[item["graph"]][0][1]
                    for i, signal in enumerate(self.signals[item["graph"]]):
                        pen = self.channels_color[item["graph"]][i]
                        (time, data), end_ind = signal
                        X = time[:end_ind]
                        Y = data[:end_ind]
                        curve = self.lookup[item["graph"]].plot(
                            X, Y, pen=pen)
                        self.signals_lines[item["graph"]][i] = curve
                    if not self.timer.isActive():
                        self.timer.start(50)

    def transfer_signal(self):
        if self.get_graph_name() == "graph1":  # from graph1 --> graph2
            curr_channel_ind = self.channels_selected["graph1"]
            self.transfer_data_between_globals(curr_channel_ind)
        elif self.get_graph_name() == "graph2":
            curr_channel_ind = self.channels_selected["graph2"]
            self.transfer_data_between_globals(curr_channel_ind)
        else:
            self.show_error_message("Can't transfer, specify a graph!")

    def transfer_data_between_globals(self, i):
        if self.get_graph_name() == "graph1" and self.transfer_button1_state:
            source_graph = "graph1"
            drain_graph = "graph2"
            self.transfer_button1_state = False
        elif self.get_graph_name() == "graph2" and self.transfer_button2_state:
            source_graph = "graph2"
            drain_graph = "graph1"
            self.transfer_button2_state = False
        else:
            return
        if i == 0:
            self.signals[drain_graph] += self.signals[source_graph]
            self.signals_lines[drain_graph] += self.signals_lines[source_graph]
            self.signals_info[drain_graph] += self.signals_info[source_graph]

            if source_graph == "graph1":
                self.channels_color["graph2"] += self.channels_color["graph1"]
                temp = [self.channelsGraph1.itemText(
                    i) for i in range(len(self.graph1_signals_paths)+1)]
                if len(self.graph2_signals_paths) == 0:
                    item_names = temp
                else:
                    item_names = [self.channelsGraph2.itemText(
                        i) for i in range(len(self.graph2_signals_paths)+1)] + temp[1:]
                self.graph2_signals_paths += self.graph1_signals_paths
                self.clear_graph1()
                self.graphSelection.setCurrentIndex(1)
                self.update_selected_graph(1)
                self.is_playing[1]["is_playing"] = True
                self.playButton.setText('Pause')
                if self.is_playing[0]["is_playing"]:
                    self.is_playing[0]["is_playing"] = False
                self.update_after_transfer("graph2", i, item_names)
            else:
                self.channels_color["graph1"] += self.channels_color["graph2"]
                temp = [self.channelsGraph2.itemText(
                    i) for i in range(len(self.graph2_signals_paths)+1)]
                if len(self.graph1_signals_paths) == 0:
                    item_names = temp
                else:
                    item_names = [self.channelsGraph1.itemText(
                        i) for i in range(len(self.graph1_signals_paths)+1)] + temp[1:]
                self.graph1_signals_paths += self.graph2_signals_paths
                self.clear_graph2()
                self.graphSelection.setCurrentIndex(0)
                self.update_selected_graph(0)  # cur graph == graph1
                self.is_playing[0]["is_playing"] = True
                self.playButton.setText('Pause')
                if self.is_playing[1]["is_playing"]:
                    self.is_playing[1]["is_playing"] = False
                self.update_after_transfer("graph1", i, item_names)

        else:
            self.signals[drain_graph].append(self.signals[source_graph][i-1])
            self.signals_info[drain_graph].append(
                self.signals_info[source_graph][i-1])
            self.signals_lines[drain_graph].append(
                self.signals_lines[source_graph][i-1])
            self.channels_color[drain_graph].append(
                self.channels_color[source_graph][i-1])

            if source_graph == "graph1":
                self.graph2_signals_paths.append(
                    self.graph1_signals_paths[i-1])
                item_name = self.channelsGraph1.itemText(i)
                self.channelsGraph1.removeItem(i)
                if len(self.signals["graph1"]) == 1:
                    self.is_playing[0]["is_playing"] = False
                    self.clear_graph1()
                    self.graphSelection.setCurrentIndex(1)
                    self.update_selected_graph(1)
                else:
                    self.is_playing[0]["is_playing"] = True
                    self.sudden_disappearing("graph1", i-1)
                    self.delete_selected_ch()
                    self.graphSelection.setCurrentIndex(2)
                    self.update_selected_graph(2)
                self.is_playing[1]["is_playing"] = True
                self.update_after_transfer("graph2", i, item_name)

            else:
                self.graph1_signals_paths.append(
                    self.graph2_signals_paths[i-1])
                item_name = self.channelsGraph2.itemText(i)
                self.channelsGraph2.removeItem(i)
                if len(self.signals["graph2"]) == 1:
                    self.clear_graph2()
                    self.is_playing[1]["is_playing"] = False
                    self.graphSelection.setCurrentIndex(0)
                    self.update_selected_graph(0)
                else:
                    self.is_playing[1]["is_playing"] = True
                    self.sudden_disappearing("graph2", i-1)
                    self.delete_selected_ch()
                    self.graphSelection.setCurrentIndex(2)
                    self.update_selected_graph(2)

                self.is_playing[0]["is_playing"] = True
                self.update_after_transfer("graph1", i, item_name)

# ************************************** Controllers and Manipulation **************************************

    def delete_selected_ch(self):
        graph_name = self.get_graph_name()
        if graph_name not in ["graph1", "graph2"]:
            self.show_error_message('Please select a graph first.')
            return

        channelsGraph = self.channelsGraph1 if graph_name == "graph1" else self.channelsGraph2

        curve_index = channelsGraph.currentIndex()
        if curve_index == 0:
            self.show_error_message("No channels selected")
            return

        curve_index_stored = curve_index - 1
        signals = self.signals[graph_name]
        signals_lines = self.signals_lines[graph_name]
        signals_info = self.signals_info[graph_name]
        signals_paths = self.graph1_signals_paths if graph_name == "graph1" else self.graph2_signals_paths
        channels_color = self.channels_color[graph_name]

        del signals[curve_index_stored]
        signals_lines[curve_index_stored].clear()
        del signals_lines[curve_index_stored]
        del signals_info[curve_index_stored]
        del signals_paths[curve_index_stored]
        del channels_color[curve_index_stored]

        channelsGraph.removeItem(len(signals_paths) + 1)
        self.fill_list1() if graph_name == "graph1" else self.fill_list2()
        channelsGraph.setCurrentIndex(0)
        self.channels_selected[graph_name] = channelsGraph.currentIndex()

        if channelsGraph.count() == 1:
            self.graph1.clear() if graph_name == "graph1" else self.graph2.clear()

    def change_speed(self):
        if self.get_graph_name() == "both":
            self.data_index["graph1"] = self.speedSlider.value()
            self.data_index["graph2"] = self.speedSlider.value()
        else:
            self.data_index[self.get_graph_name()] = self.speedSlider.value()

    def zoom_in(self):
        # Scale the viewbox around the specified center point
        if (self.current_graph == self.graph1):
            view_box = self.graph1.plotItem.getViewBox()
            view_box.scaleBy((0.5, 0.5))
        elif (self.current_graph == self.graph2):
            view_box = self.graph2.plotItem.getViewBox()
            view_box.scaleBy((0.5, 0.5))
        else:  # link mode
            for graph in self.current_graph:
                view_box = graph.plotItem.getViewBox()
                view_box.scaleBy((0.5, 0.5))

    def zoom_out(self):
        # Scale the viewbox around the specified center point
        if (self.current_graph == self.graph1):
            view_box = self.graph1.plotItem.getViewBox()
            view_box.scaleBy((1.5, 1.5))
        elif (self.current_graph == self.graph2):
            view_box = self.graph2.plotItem.getViewBox()
            view_box.scaleBy((1.5, 1.5))
        else:  # link mode
            for graph in self.current_graph:
                view_box = graph.plotItem.getViewBox()
                view_box.scaleBy((1.5, 1.5))

    def rewind_graph(self):
        if (self.current_graph == self.graph1):
            self.initialize_data()
            self.current_graph.clear()
            self.assign_colors(self.get_graph_name())
        elif (self.current_graph == self.graph2):
            self.initialize_data()
            self.current_graph.clear()
            self.assign_colors(self.get_graph_name())
        else:  # link mode
            self.initialize_data()
            self.current_graph[0].clear()
            self.current_graph[1].clear()

            for signal_path in self.graph1_signals_paths:
                # so that the plot appears only on its corresponding graph
                self.sourceGraph = "graph1"
                self.assign_colors(self.sourceGraph)
            for signal_path in self.graph2_signals_paths:
                self.sourceGraph = "graph2"
                self.assign_colors(self.sourceGraph)
            self.sourceGraph = "both"  # so that the controls apply to both graphs

    def clear_graph(self):
        msg_box = QMessageBox()
        # msg_box.setIcon(QMessageBox.warning)
        msg_box.setText("Do you want to clear the graph?")
        msg_box.setWindowTitle("Clear Graph")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        result = msg_box.exec()

        if result == QMessageBox.StandardButton.Ok:
            if self.current_graph == self.graph1:
                self.clear_graph1()
            elif self.current_graph == self.graph2:
                self.clear_graph2()
            else:
                self.clear_graph1()
                self.clear_graph2()

    def clear_graph1(self):
        self.initialize_data()
        self.graph1.clear()
        self.playButton.setText('Play')
        self.set_icon("Icons/play-svgrepo-com.svg")
        self.graph1_signals_paths = []
        self.channels_color["graph1"] = []
        self.channelsGraph1.clear()
        self.hideList1.clear()
        self.channelsGraph1.addItem("All Channels")
        self.graph1.setXRange(0, 1)
        self.channelsGraph1.setCurrentIndex(0)
        self.handle_selected_channels_change("graph1", 0)

    def clear_graph2(self):
        self.initialize_data()
        self.graph2.clear()

        self.playButton.setText('Play')
        self.set_icon("Icons/play-svgrepo-com.svg")
        self.graph2_signals_paths = []
        self.channels_color["graph2"] = []
        self.channelsGraph2.clear()
        self.hideList2.clear()
        self.channelsGraph2.addItem("All Channels")
        self.graph2.setXRange(0, 1)
        self.channelsGraph2.setCurrentIndex(0)
        self.handle_selected_channels_change("graph2", 0)

    def toggle_play_pause(self):
        if self.current_graph == self.graph1:
            if self.is_playing[0]["is_playing"]:
                self.is_playing[0]["is_playing"] = False
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")
                last_data = self.get_last_data_point("graph1")[0]
                self.graph1.setLimits(xMin=0)
                self.graph1.setLimits(yMin=-0.5, yMax=1)
            else:
                self.is_playing[0]["is_playing"] = True
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")

        elif self.current_graph == self.graph2:
            if self.is_playing[1]["is_playing"]:
                self.is_playing[1]["is_playing"] = False
                self.playButton.setText('Play')
                self.set_icon("Icons/play-svgrepo-com.svg")
                last_data = self.get_last_data_point("graph2")[0]
                self.graph2.setLimits(xMin=0, xMax=last_data)
                self.graph2.setLimits(yMin=-0.5, yMax=1)

            else:
                self.is_playing[1]["is_playing"] = True
                self.playButton.setText('Pause')
                self.set_icon("Icons/pause.svg")
                # Allow free panning when playing
                # self.set_panning_limits(self.graph2, False)

        else:  # link mode
            for graph in self.is_playing:
                if graph["is_playing"]:
                    graph["is_playing"] = False
                    self.playButton.setText('Play')
                    self.set_icon("Icons/play-svgrepo-com.svg")
                    # Restrict panning beyond the last data point when pausing
                    # self.set_panning_limits(self.current_graph, True)
                    self.graph1.setLimits(xMin=0, xMax=last_data)
                    self.graph2.setLimits(xMin=0, xMax=last_data)
                    self.graph1.setLimits(yMin=-0.5, yMax=1)
                    self.graph2.setLimits(yMin=-0.5, yMax=1)
                else:
                    graph["is_playing"] = True
                    self.playButton.setText('Pause')
                    self.set_icon("Icons/pause.svg")
                    # Allow free panning when playing
                    # self.set_panning_limits(self.current_graph, False)

    def get_last_data_point(self, graph):
        if graph in self.signals and self.signals[graph]:
            last_signal = self.signals[graph][-1]
            (time, data), end_ind = last_signal
            if end_ind < len(time) and end_ind < len(data):
                return (time[end_ind], data[end_ind])
        return None

# ************************************** Colors, Labels, and Legends **************************************

    def change_channel_label(self):
        graph_name = self.get_graph_name()
        if graph_name == 'graph1':
            if self.channelsGraph1.currentIndex() == 0:
                self.show_error_message('Select Channel first')
            else:
                self.channelsGraph1.setItemText(
                    self.channelsGraph1.currentIndex(), self.addLabelGraph1.text())
                self.fill_list1()
        elif graph_name == 'graph2':
            if self.channelsGraph2.currentIndex() == 0:
                self.show_error_message('Select Channel first')
            else:
                self.channelsGraph2.setItemText(
                    self.channelsGraph2.currentIndex(), self.addLabelGraph2.text())
                self.fill_list2()
        else:
            self.show_error_message('Select Graph first')

    def add_legend(self, graph_name):
        channelsGraph = self.channelsGraph1 if graph_name == "graph1" else self.channelsGraph2
        addLabel = self.addLabelGraph1 if graph_name == "graph1" else self.addLabelGraph2

        index = channelsGraph.currentIndex()

        # if index == 0:
        #     self.show_error_message("No channel selected")
        #     return

        legend_text = addLabel.text()

        current_index = self.get_index()
        signals_info = self.signals_info.setdefault(graph_name, [])

        while len(signals_info) <= current_index:
            signals_info.append([True, None, None])

        signals_info[current_index][2] = legend_text

        # Initialize legends for all channels
        # self.initialize_legends(graph_name)

        addLabel.clear()

    def initialize_legends(self, graph_name):
        current_graph = getattr(self, graph_name)
        signals_info = self.signals_info.get(graph_name, [])

        if current_graph.plotItem.legend is not None:
            current_graph.plotItem.legend.clear()

        current_graph.addLegend()

        for channel_info in signals_info:
            if channel_info[2]:
                channel_index = signals_info.index(channel_info)
                channel_color = self.channels_color[graph_name][channel_index - 1].color()
                pen = pg.mkPen(color=channel_color)
                current_graph.plot(name=channel_info[2], pen=pen)

    def assign_colors(self, graph_name):
        signals_paths = self.graph1_signals_paths if graph_name == 'graph1' else self.graph2_signals_paths
        channels_color = self.channels_color[graph_name]
        signals_lines = self.signals_lines[graph_name]

        for i, signal_path in enumerate(signals_paths):
            self.open_file(signal_path)
        for j, color in enumerate(channels_color):
            if j < len(signals_lines):
                signals_lines[j].setPen(color)

    def pick_channel_color(self):
        graph = self.get_graph_name()
        channelsGraph = self.channelsGraph1 if graph == 'graph1' else self.channelsGraph2

        selected_channel_index = channelsGraph.currentIndex()

        if selected_channel_index == 0:
            self.show_error_message('Channel not selected')
        else:
            color_dialog = QColorDialog(self)
            color = color_dialog.getColor()

            if color.isValid():
                new_color = pg.mkColor(color.name())
                channels_color = self.channels_color[graph]
                signals_lines = self.signals_lines[graph]

                if selected_channel_index <= len(channels_color) and selected_channel_index <= len(signals_lines):
                    channels_color[selected_channel_index - 1] = new_color
                    signals_lines[selected_channel_index - 1].setPen(new_color)


# ************************************** Snapshot and PDF Report **************************************

    def take_snapshot(self):
        index = self.graphSelection.currentIndex()
        graph_items = {
            0: self.graph1.plotItem,
            1: self.graph2.plotItem
        }

        if index in graph_items:
            graph_item = graph_items[index]
            screenshot = ImageExporter(graph_item)
            screenshot.parameters()['width'] = 640
            screenshot.parameters()['height'] = 480
            screenshot_path = f"Screenshot_{len(self.snapshoot_data)}.png"
            screenshot.export(screenshot_path)
            self.snapshoot_data.append(screenshot_path)
        else:
            QtWidgets.QMessageBox.warning(
                self, 'Warning', 'Please select a graph')

    def add_snapshots_to_pdf(self, pdf):
        # Capture the snapshots
        snap_data = self.snapshoot_data

        # Iterate over each snapshot
        for graph_image in snap_data:
            # Add the graph name to the PDF
            # Extract the image file name
            image_name = os.path.basename(graph_image[:12])

            pdf.cell(200, 10, text=image_name)
            pdf.ln(10)

            pdf.image(graph_image, x=10, w=190)
            pdf.ln(10)

    def create_report(self, graph_widget, pdf_title="Signal_Report.pdf"):
        self.folder_path, _ = QFileDialog.getSaveFileName(
            None, 'Save the signal file', None, 'PDF Files (*.pdf)')
        if self.folder_path:
            self.pdf = FPDF()
            self.pdf.add_page()
            self.add_page_border()
            self.add_title("Signal Report")
            self.add_logos()
            self.add_snapshots_to_pdf(self.pdf)
            self.add_statistics_tables()
            self.save_pdf()

    def add_page_border(self):
        self.pdf.set_draw_color(0, 0, 0)  # Set line color to black
        # Draw a border around the entire page
        self.pdf.rect(1, 1, self.pdf.w, self.pdf.h)

    def add_title(self, title):
        self.pdf.set_font("times", "B", size=25)
        self.pdf.cell(200, 5, txt=title, align="C")
        # Reset the font to the previous settings
        self.pdf.set_font("times", size=12)

    def add_logos(self):
        self.pdf.image('LOGO/asset-cairo.png', 2, 3, 40, 40)
        self.pdf.image('LOGO/Asset-SBE.png', 160, 3, 40, 40)
        self.pdf.ln(30)

    def add_statistics_tables(self):
        graph_names = ["graph1", "graph2"]

        for graph_name in graph_names:
            statistics = self.get_signal_statistics(graph_name)

            if statistics:
                self.pdf.cell(200, 10, text=f"Statistics for {graph_name}")
                self.pdf.ln(10)  # Move to the next line

                mean, std, maximum, minimum = self.access_nested_list_items(
                    statistics)

                self.create_statistics_table(mean, std, maximum, minimum)

    def create_statistics_table(self, mean, std, maximum, minimum):
        self.pdf.ln(10)  # Move to the next line
        col_width = 25
        num_plots = len(mean)

        self.pdf.set_fill_color(211, 211, 211)  # Set a light gray fill color

        # Add headers
        self.pdf.cell(col_width, 10, "Metric", border=1, fill=True)
        for i in range(num_plots):
            self.pdf.cell(col_width, 10, f"Plot {i + 1}", border=1, fill=True)
        self.pdf.ln()

        metrics = ["Mean", "Std", "Maximum", "Minimum"]
        data_lists = [mean, std, maximum, minimum]

        for metric, data_list in zip(metrics, data_lists):
            self.pdf.cell(col_width, 10, metric, border=1)
            for value in data_list:
                self.pdf.cell(col_width, 10, f"{value: .4f}", border=1)
            self.pdf.ln(10)

    def get_signal_statistics(self, graph_widget: str):
        statistics = []
        for signal in self.signals[graph_widget]:
            _, data = signal[0]
            mean = np.mean(data)
            std = np.std(data)
            maximum = np.max(data)
            minimum = np.min(data)
            statistics.append([mean, std, maximum, minimum])
        return statistics

    def access_nested_list_items(self, nested_list):
        mean_list, std_list, max_list, min_list = [], [], [], []

        for sublist in nested_list:
            if len(sublist) == 4:
                mean_list.append(sublist[0])
                std_list.append(sublist[1])
                max_list.append(sublist[2])
                min_list.append(sublist[3])

        return mean_list, std_list, max_list, min_list

    def save_pdf(self):
        self.pdf.output(str(self.folder_path))
        # This message appears when the PDF is EXPORTED
        QMessageBox.information(self, 'Done', 'PDF has been created')
        for i in range(len(self.snapshoot_data)):
            os.remove(f"Screenshot_{i}.png")

    def generate_signal_report(self):
        if isinstance(self.current_graph, list):
            # If in link mode, generate reports for both graphs
            for graph in self.current_graph:
                self.create_report(graph)
        else:
            # Generate a report for the current graph
            self.create_report(self.current_graph)
        self.snapshoot_data = []
        self.stat_lst = []


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
    main = MainWindow()
    main.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
