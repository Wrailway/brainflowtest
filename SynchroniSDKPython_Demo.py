import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'SimHei'  # 使用黑体字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

import sys
import signal
from typing import List
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QRunnable, QThreadPool
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import numpy as np
from sensor import *

SCAN_DEVICE_PERIOD_IN_MS = 3000
PACKAGE_COUNT = 5
POWER_REFRESH_PERIOD_IN_MS = 60000
PLOT_UPDATE_INTERVAL = 50
SAMPLE_INTERVAL = 1  # 采样间隔

# 定义周期选项
PERIOD_OPTIONS = {
    "500ms": 0.5,
    "1s": 1,
    "5s": 5,
    "10s": 10,
    "30s": 30,
    "60s": 60
}


class DataProcessingTask(QRunnable):
    def __init__(self, parent, data):
        super().__init__()
        self.parent = parent
        self.data = data

    def run(self):
        try:
            self.parent.add_data_to_buffer(self.data)
        except Exception as e:
            print(f"DataProcessingTask 中出现异常: {e}")


class BluetoothDeviceScanner(QtWidgets.QWidget):
    data_received = QtCore.pyqtSignal(object)
    add_device_signal = QtCore.pyqtSignal(str)
    update_plot_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.discovered_devices = []
        self.connected_device = None
        self.SensorControllerInstance = SensorController()
        self.sensor_profiles = {}
        self.sampling_rate = 250
        self.period = 1  # 默认周期为 1s
        self.data_buffer = None
        self.buffer_index = 0
        self.line = None
        self.background = None
        self.callback_counter = 0
        self.thread_pool = QThreadPool.globalInstance()  # 获取全局线程池
        self.current_channel = 0  # 默认显示通道 1 的数据
        self.EegChannelCount = 0  # 通道数目初始化为 0
        self.initUI()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(PLOT_UPDATE_INTERVAL)

        self.add_device_signal.connect(self.add_device_to_list)
        self.update_plot_signal.connect(self.update_plot)
        self.data_received.connect(self.start_data_processing)

        if not self.SensorControllerInstance.hasDeviceFoundCallback:
            self.SensorControllerInstance.onDeviceFoundCallback = self.deviceFoundCallback

        self.init_blitting()

    def initUI(self):
        main_layout = QtWidgets.QHBoxLayout()

        left_layout = QtWidgets.QVBoxLayout()
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        left_layout.addWidget(self.canvas)
        toolbar = NavigationToolbar2QT(self.canvas, self)
        left_layout.addWidget(toolbar)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlim(0, self.period)
        self.ax.set_ylim(-1000, 1000)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (uV)')
        self.ax.set_title('EEG Waveform (Real-time)')

        right_layout = QtWidgets.QVBoxLayout()
        self.scan_button = QtWidgets.QPushButton('开始扫描蓝牙设备')
        self.scan_button.clicked.connect(self.start_scan)
        right_layout.addWidget(self.scan_button)

        self.stop_scan_button = QtWidgets.QPushButton('停止扫描蓝牙设备')
        self.stop_scan_button.clicked.connect(self.stop_scan)
        self.stop_scan_button.setEnabled(False)
        right_layout.addWidget(self.stop_scan_button)

        self.disconnect_button = QtWidgets.QPushButton('断开连接')
        self.disconnect_button.clicked.connect(self.disconnect_device)
        self.disconnect_button.setEnabled(False)
        right_layout.addWidget(self.disconnect_button)

        self.device_list = QtWidgets.QListWidget()
        self.device_list.itemClicked.connect(self.connect_device)
        right_layout.addWidget(self.device_list)

        # 添加周期选择下拉框
        self.period_combobox = QtWidgets.QComboBox()
        for option in PERIOD_OPTIONS.keys():
            self.period_combobox.addItem(option)
        self.period_combobox.setCurrentText("1s")  # 默认选择 1s
        self.period_combobox.currentTextChanged.connect(self.change_period)
        right_layout.addWidget(QtWidgets.QLabel("选择周期:"))
        right_layout.addWidget(self.period_combobox)

        # 添加通道选择下拉框
        self.channel_combobox = QtWidgets.QComboBox()
        self.channel_combobox.currentIndexChanged.connect(self.change_channel)
        right_layout.addWidget(QtWidgets.QLabel("选择通道:"))
        right_layout.addWidget(self.channel_combobox)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        main_layout.setStretch(0, 7)
        main_layout.setStretch(1, 3)

        self.setLayout(main_layout)
        self.setWindowTitle('SynchroniSDKPython Demo')
        self.resize(1000, 600)
        self.show()

    def start_scan(self):
        try:
            if not self.SensorControllerInstance.isEnable:
                print('please open bluetooth')
                return
            if not self.SensorControllerInstance.isScaning:
                if not self.SensorControllerInstance.startScan(SCAN_DEVICE_PERIOD_IN_MS):
                    print('please try scan later')
                self.scan_button.setEnabled(False)
                self.stop_scan_button.setEnabled(True)
        except Exception as e:
            print(f"扫描出错: {e}")

    def stop_scan(self):
        try:
            self.SensorControllerInstance.stopScan()
            self.scan_button.setEnabled(True)
            self.stop_scan_button.setEnabled(False)
        except Exception as e:
            print(f"停止扫描出错: {e}")

    def connect_device(self, item):
        item_text = item.text()
        address_start = item_text.find("Address: ") + len("Address: ")
        address_end = item_text.find(", RSSI:")
        device_address = item_text[address_start:address_end]

        target_device = next((d for d in self.discovered_devices if d.Address == device_address), None)

        if target_device:
            try:
                sensor = self.SensorControllerInstance.requireSensor(target_device)
                if sensor is None:
                    print("Failed to create SensorProfile")
                    return

                sensor.onDataCallback = self.onDataCallback
                sensor.onPowerChanged = self.onPowerChanged
                sensor.onStateChanged = self.onStateChanged
                sensor.onErrorCallback = self.onErrorCallback

                if sensor.deviceState != DeviceStateEx.Ready:
                    if not sensor.connect():
                        print('connect device: ' + sensor.BLEDevice.Name + ' failed')
                        return

                if not sensor.hasInited:
                    result = sensor.setParam('DEBUG_BLE_DATA_PATH', '/temp/test.csv')
                    if not sensor.init(PACKAGE_COUNT, POWER_REFRESH_PERIOD_IN_MS):
                        print('init device: ' + sensor.BLEDevice.Name + ' failed')
                        return
                    deviceInfo = sensor.getDeviceInfo()
                    self.sampling_rate = deviceInfo.EegSampleRate
                    self.EegChannelCount = deviceInfo.EegChannelCount
                    self.update_buffer_size()
                    # 清空原有的通道选项
                    self.channel_combobox.clear()
                    # 根据读取到的通道数目添加通道选项
                    for i in range(self.EegChannelCount):
                        self.channel_combobox.addItem(f"通道 {i + 1}")
                    self.channel_combobox.setCurrentIndex(0)

                if not sensor.startDataNotification():
                    print('start data transfer with device: ' + sensor.BLEDevice.Name + ' failed')
                    return

                self.connected_device = target_device
                self.sensor_profiles[device_address] = sensor
                self.disconnect_button.setEnabled(True)

                self.init_blitting()

            except Exception as e:
                print(f"连接设备出错: {e}")

    def add_device_to_list(self, item_text):
        self.device_list.addItem(item_text)

    def disconnect_device(self):
        if self.connected_device:
            device_address = self.connected_device.Address
            sensor = self.sensor_profiles.get(device_address)
            if sensor:
                try:
                    sensor.disconnect()
                    print(f"Disconnected from device {self.connected_device.Name}")
                    self.connected_device = None
                    self.disconnect_button.setEnabled(False)
                except Exception as e:
                    print(f"断开设备连接时出现异常: {e}")
            else:
                print("No sensor profile found for the connected device.")
        else:
            print("No device is currently connected.")

    def deviceFoundCallback(self, deviceList: List[BLEDevice]):
        try:
            self.SensorControllerInstance.stopScan()
            self.scan_button.setEnabled(True)
            self.stop_scan_button.setEnabled(False)

            filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
            for device in filteredDevice:
                if device.Address not in [d.Address for d in self.discovered_devices]:
                    item_text = f"Name: {device.Name}, Address: {device.Address}, RSSI: {device.RSSI}"
                    self.add_device_signal.emit(item_text)
                    self.discovered_devices.append(device)
        except Exception as e:
            print(f"设备发现回调中出现异常: {e}")

    def onDataCallback(self, sensor: SensorProfile, data: SensorData):
        self.callback_counter += 1
        if self.callback_counter % 10 == 0:
            if data and data.channelSamples and data.dataType in [DataType.NTF_EEG]:
                sampled_channel = []
                for channel in data.channelSamples:
                    sampled_channel.append([sample for index, sample in enumerate(channel) if index % SAMPLE_INTERVAL == 0])
                data.channelSamples = sampled_channel
            self.data_received.emit(data)
            self.callback_counter = 0

    def onPowerChanged(self, sensor: SensorProfile, power: int):
        print('connected sensor: ' + sensor.BLEDevice.Name + ' power: ' + str(power))
        if not sensor.isDataTransfering:
            try:
                sensor.disconnect()
                self.SensorControllerInstance.startScan(SCAN_DEVICE_PERIOD_IN_MS)
            except Exception as e:
                print(f"电源变化时断开连接并重新扫描出现异常: {e}")

    def onStateChanged(self, sensor: SensorProfile, newstate: DeviceStateEx):
        print('device: ' + sensor.BLEDevice.Name + str(newstate))

    def onErrorCallback(self, sensor: SensorProfile, reason: str):
        print('device: ' + sensor.BLEDevice.Name + reason)

    def update_buffer_size(self):
        buffer_size = int(self.period * self.sampling_rate)
        self.data_buffer = np.zeros((self.EegChannelCount, buffer_size))
        self.buffer_index = 0

    def add_data_to_buffer(self, data: SensorData):
        try:
            if data and data.channelSamples:
                for i, channel in enumerate(data.channelSamples):
                    if i >= self.EegChannelCount:
                        print(f"Warning: Index {i} is out of bounds for self.data_buffer with size {self.EegChannelCount}. Skipping...")
                        continue
                    new_data = np.array([sample.data for sample in channel])
                    buffer_size = len(self.data_buffer[i])
                    num_samples = len(new_data)

                    if buffer_size - num_samples >= 0:
                        # 缓冲区有足够空间，将新数据添加到右侧
                        self.data_buffer[i] = np.roll(self.data_buffer[i], -num_samples)
                        self.data_buffer[i][-num_samples:] = new_data
                    else:
                        # 缓冲区空间不足，移除左侧数据
                        self.data_buffer[i] = np.roll(self.data_buffer[i], -num_samples)
                        self.data_buffer[i][-num_samples:] = new_data
                        self.data_buffer[i] = self.data_buffer[i][-buffer_size:]

                self.update_plot_signal.emit()
        except Exception as e:
            print(f"add_data_to_buffer 方法中出现异常: {e}")

    def init_blitting(self):
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.line, = self.ax.plot([], [], label='通道 1')
        self.ax.legend(handles=[self.line], loc='upper right')

    def update_plot(self):
        try:
            if self.data_buffer is not None:
                buffer_size = int(self.period * self.sampling_rate)
                time_axis = np.linspace(0, self.period, buffer_size)

                y_data = self.data_buffer[self.current_channel]
                self.line.set_data(time_axis, y_data)

                min_val = np.min(y_data)
                max_val = np.max(y_data)

                if min_val == max_val:
                    min_val = min_val - 100
                    max_val = max_val + 100

                margin = 0.2 * (max_val - min_val)
                min_val -= margin
                max_val += margin
                self.ax.set_ylim(min_val, max_val)

                self.canvas.restore_region(self.background)
                self.ax.draw_artist(self.line)
                self.canvas.blit(self.ax.bbox)
                self.canvas.flush_events()
        except Exception as e:
            print(f"update_plot 方法中出现异常: {e}")

    def start_data_processing(self, data):
        task = DataProcessingTask(self, data)
        self.thread_pool.start(task)

    def change_period(self, period_text):
        self.period = PERIOD_OPTIONS[period_text]
        # 清空数据缓冲区
        self.data_buffer = None
        self.update_buffer_size()
        self.ax.clear()  # 清除坐标轴上的内容
        self.ax.set_xlim(0, self.period)
        self.ax.set_ylim(-1000, 1000)  # 恢复默认的 y 轴范围，可根据需要调整
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (uV)')
        self.ax.set_title('EEG Waveform (Real-time)')
        self.line, = self.ax.plot([], [], label=f'通道 {self.current_channel + 1}')
        self.ax.legend(handles=[self.line], loc='upper right')
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)

    def change_channel(self, index):
        self.current_channel = index
        self.data_buffer = None
        self.update_buffer_size()
        self.ax.clear()  # 清除坐标轴上的内容
        self.ax.set_xlim(0, self.period)
        self.ax.set_ylim(-1000, 1000)  # 恢复默认的 y 轴范围，可根据需要调整
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (uV)')
        self.ax.set_title('EEG Waveform (Real-time)')
        self.line, = self.ax.plot([], [], label=f'通道 {self.current_channel + 1}')
        self.ax.legend(handles=[self.line], loc='upper right')
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 重新绘制图形
        # self.canvas.draw()
        self.data_buffer = None
        self.update_buffer_size()
        self.ax.clear()  # 清除坐标轴上的内容
        self.ax.set_xlim(0, self.period)
        self.ax.set_ylim(-1000, 1000)  # 恢复默认的 y 轴范围，可根据需要调整
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (uV)')
        self.ax.set_title('EEG Waveform (Real-time)')
        self.line, = self.ax.plot([], [], label=f'通道 {self.current_channel + 1}')
        self.ax.legend(handles=[self.line], loc='upper right')
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)


if __name__ == '__main__':
    try:
        app = QtWidgets.QApplication(sys.argv)
        scanner = BluetoothDeviceScanner()

        def sigint_handler(signal, frame):
            app.quit()
            sys.exit(0)

        signal.signal(signal.SIGINT, sigint_handler)
        sys.exit(app.exec_())
    except Exception as e:
        print(f"应用程序出现未捕获的异常: {e}")
