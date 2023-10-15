# Multi-Port, Multi-Channel Signal Viewer

This desktop application allows you to browse and open signal files, display them in two main identical graphs, and manipulate them using UI elements. The application also supports cine mode and exporting reports to PDF.

## **Features:**

* Browse and open signal files in multiple formats, such as CSV, and dat.
* Display signals in two main identical graphs, each with its own controls for zoom, pan, and play/pause.
* Link the two graphs so that they display the same time frames, signal speed, and viewport.
* Display signals in cine mode (i.e., a running signal through time, similar to the one you see in ICU monitors).
* Provide a rewind option to either stop the signal or start running it again from the beginning.
* Allow users to manipulate the running signals using UI elements, such as changing color, adding/removing labels, controlling cine speed, zooming, panning, and moving signals from one graph to the other.
* Handle boundary conditions so that the user cannot scroll or pan beyond the beginning or end of the signal or above its maximum or below its minimum values.
* Export reports to PDF, including one or more snapshots for the graphs and data statistics for the displayed signals.

## **Usage:**

1. To open a signal file, click on the "Open File" button and select the desired file.
2. To display the signal in cine mode, click on the "Play" button.
3. To manipulate the signal, use the UI elements provided at the side of the window.
4. To export a report, click on the "Pdf report" button and select the desired destination.

## **Examples:**

The following are some examples of how to use the application:

* To view an ECG signal, open an ECG signal file and click on the "Play" button.
* To compare two ECG signals, open the two signal files and display them in the two graphs. You can then link the two graphs so that they display the same time frames, signal speed, and viewport.

## **Preview**
![program preview](/LOGO/prototype.gif)

## **Troubleshooting:**

If you are having problems with the application, please consult the following troubleshooting tips:

* Make sure that you have installed the required Python packages, such as NumPy, Pandas, and Qt.
* Make sure that you are using a supported signal format.
* Try restarting the application.
* If you are still having problems, please post a question on the project's GitHub page.

## **Install the required dependencies:**
  ```
  pip install -r requirements.txt
  ```
```
python main.py
```
