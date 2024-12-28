import logging
import sys
import time
from time import sleep

from PyQt5 import QtCore, QtWidgets
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import brainflow
from brainflow.board_shim import BoardShim
from brainflow.data_filter import DataFilter, FilterTypes
from PyQt5.QtCore import QTimer

# 设置日志级别为INFO，获取日志记录器实例
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class EEGDataVisualizer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # 初始化self.fig和self.ax，确保在initUI方法使用之前已经存在
        self.fig = Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)

        self.timer = None
        self.timer_stopped = False
       
        # 新增data_buffer属性初始化，初始为None
        self.data_buffer = None
         # 新增buffer_index属性初始化，初始为0
        self.buffer_index = 0

        # 用于标记是否暂停数据采集和图形更新，初始化为False（未暂停）
        self.paused = False
        # 用于存储暂停时的数据缓冲区内容备份，初始为空
        self.paused_data_buffer = None
        # 用于存储暂停时的缓冲区索引备份，初始为0
        self.paused_buffer_index = 0
        # 停止获取数据
        self.stop = False
        self.period = 1
        
        # 存储通道复选框的列表
        self.channel_checkboxes = []
        self.eeg_channels = []  # 实际的脑电图通道列表，按实际初始化
        
        # 滤波器类型
        self.low_pass_filter = 'Low - Pass Filter'
        self.high_pass_filter = 'High - Pass Filter'
        self.band_pass_filter = 'Band - Pass Filter'
        self.band_stop_filter = 'Band - Stop Filter'
        self.current_filter = None
        self.current_cutoff_freq = 0.0
        self.current_low_cutoff_freq = 0.0
        self.current_high_cutoff_freq = 0.0
        # 滤波器复选框字典，存储每种滤波器的复选框和相关参数输入框等控件
        self.filter_checkboxes = {
            self.low_pass_filter: {"checkbox": None, "cutoff_edit": QtWidgets.QLineEdit()},
            self.high_pass_filter: {"checkbox": None, "cutoff_edit": QtWidgets.QLineEdit()},
            self.band_pass_filter: {"checkbox": None, "low_cutoff_edit": QtWidgets.QLineEdit(), "high_cutoff_edit": QtWidgets.QLineEdit()},
            self.band_stop_filter : {"checkbox": None, "low_cutoff_edit": QtWidgets.QLineEdit(), "high_cutoff_edit": QtWidgets.QLineEdit()}
        }
        # 低通滤波器默认截止频率
        self.lowpass_default_cutoff = 80.0
        
        # 高通滤波器默认截止频率
        self.highpass_default_cutoff = 0.5
        
        # 带通滤波器默认低频截止频率
        self.bandpass_default_low_cutoff = 0.5
        # 带通滤波器默认高频截止频率
        self.bandpass_default_high_cutoff = 45.0
        
        # 带阻滤波器默认低频截止频率
        self.bandstop_default_low_cutoff = 50.0
        # 带阻滤波器默认高频截止频率
        self.bandstop_default_high_cutoff = 60.0
        self.initUI()

    def initUI(self):
        main_layout = QtWidgets.QHBoxLayout()

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(20, 20, 20, 20)

        right_layout = QtWidgets.QVBoxLayout()

        # MAC 地址输入框
        mac_layout = QtWidgets.QHBoxLayout()
        self.mac_label = QtWidgets.QLabel('MAC address:') #C4:64:E3:D8:E6:D2
        self.mac_edit = QtWidgets.QLineEdit('60:77:71:74:E6:B7')  # 留空让用户输入真实MAC地址 84:27:12:17:BC:D8,,,60:77:71:74:E6:B7 84:27:12:14:C6:E5  84:BA:20:6E:3C:1E
        mac_layout.addWidget(self.mac_label, 0, alignment=QtCore.Qt.AlignLeft)
        mac_layout.addWidget(self.mac_edit, 0, alignment=QtCore.Qt.AlignLeft)
        left_layout.addLayout(mac_layout)

        # board_id 输入框
        id_layout = QtWidgets.QHBoxLayout()
        self.board_id_label = QtWidgets.QLabel('Board ID:')
        self.board_id_edit = QtWidgets.QLineEdit('58')  # 留空让用户输入真实Board ID
        id_layout.addWidget(self.board_id_label, 0, alignment=QtCore.Qt.AlignLeft)
        id_layout.addWidget(self.board_id_edit, 0, alignment=QtCore.Qt.AlignLeft)
        left_layout.addLayout(id_layout)

        # 创建连接设备按钮
        self.connect_button = QtWidgets.QPushButton('Connect the EEG device')
        self.connect_button.setFixedSize(330, 30)
        self.connect_button.setEnabled(True)
        self.connect_button.clicked.connect(self.connect_device)
        left_layout.addWidget(self.connect_button, 0, alignment=QtCore.Qt.AlignLeft)

        # 创建开始采集按钮
        self.start_button = QtWidgets.QPushButton('Start collecting EEG data')
        self.start_button.setFixedSize(330, 30)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_real_time_collection)
        left_layout.addWidget(self.start_button, 0, alignment=QtCore.Qt.AlignLeft)

        # 创建暂停按钮
        op_layout = QtWidgets.QHBoxLayout()
        op_layout.setSpacing(20)
        self.pause_button = QtWidgets.QPushButton('Pause')
        self.pause_button.setFixedSize(80, 30)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_real_time_collection)
        op_layout.addWidget(self.pause_button, 0, alignment=QtCore.Qt.AlignLeft)

        # 创建恢复按钮
        self.resume_button = QtWidgets.QPushButton('Resume')
        self.resume_button.setFixedSize(80, 30)
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.resume_real_time_collection)
        op_layout.addWidget(self.resume_button, 0, alignment=QtCore.Qt.AlignLeft)

        # 创建停止按钮
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.setFixedSize(80, 30)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_real_time_collection)
        op_layout.addWidget(self.stop_button, 0, alignment=QtCore.Qt.AlignLeft)

        # left_layout.addLayout(op_layout)
        
          # 创建布局

        # 创建下拉选择框
        self.period_combo_box = QtWidgets.QComboBox()
        # 添加下拉选项示例，这里你可以根据实际需求来设置具体有意义的选项
        self.period_combo_box.addItems(["1s", "5s", "10s"])
        self.period_combo_box.setFixedSize(80, 30)
        self.period_combo_box.setCurrentIndex(0)
        # 将下拉选择框的当前选项改变信号与对应的处理函数关联，假设处理函数名为handle_stop_selection
        self.period_combo_box.currentIndexChanged.connect(self.handle_period_selection)
        op_layout.addWidget(self.period_combo_box, 0, alignment=QtCore.Qt.AlignLeft)

        left_layout.addLayout(op_layout)

        # 创建滤波器复选框及相关输入框布局
        for filter_type in self.filter_checkboxes:
            checkbox = QtWidgets.QCheckBox(filter_type)
            checkbox.stateChanged.connect(self.apply_filter)
            self.filter_checkboxes[filter_type]["checkbox"] = checkbox
            left_layout.addWidget(checkbox, 0, alignment=QtCore.Qt.AlignLeft)
            if filter_type == self.low_pass_filter:
                cutoff_label = QtWidgets.QLabel('Cut - off Frequency(Hz):')
                cutoff_edit = self.filter_checkboxes[filter_type]["cutoff_edit"]
                cutoff_edit.setText(str(self.lowpass_default_cutoff))
                cutoff_layout = QtWidgets.QHBoxLayout()
                cutoff_layout.addWidget(cutoff_label)
                cutoff_layout.addWidget(cutoff_edit)
                left_layout.addLayout(cutoff_layout)
            elif filter_type == self.high_pass_filter:
                cutoff_label = QtWidgets.QLabel('Cut - off Frequency(Hz):')
                cutoff_edit = self.filter_checkboxes[filter_type]["cutoff_edit"]
                cutoff_edit.setText(str(self.highpass_default_cutoff))
                cutoff_layout = QtWidgets.QHBoxLayout()
                cutoff_layout.addWidget(cutoff_label)
                cutoff_layout.addWidget(cutoff_edit)
                left_layout.addLayout(cutoff_layout)
            elif filter_type == self.band_pass_filter:
                low_cutoff_label = QtWidgets.QLabel('Low Cut - off Frequency(Hz):')
                low_cutoff_edit = self.filter_checkboxes[filter_type]["low_cutoff_edit"]
                low_cutoff_edit.setText(str(self.bandpass_default_low_cutoff))
                high_cutoff_label = QtWidgets.QLabel('High Cut - off Frequency(Hz):')
                high_cutoff_edit = self.filter_checkboxes[filter_type]["high_cutoff_edit"]
                high_cutoff_edit.setText(str(self.bandpass_default_high_cutoff))
                low_cutoff_layout = QtWidgets.QHBoxLayout()
                low_cutoff_layout.addWidget(low_cutoff_label)
                low_cutoff_layout.addWidget(low_cutoff_edit)
                high_cutoff_layout = QtWidgets.QHBoxLayout()
                high_cutoff_layout.addWidget(high_cutoff_label)
                high_cutoff_layout.addWidget(high_cutoff_edit)
                bandpass_cutoff_layout = QtWidgets.QVBoxLayout()
                bandpass_cutoff_layout.addLayout(low_cutoff_layout)
                bandpass_cutoff_layout.addLayout(high_cutoff_layout)
                left_layout.addLayout(bandpass_cutoff_layout)
            elif filter_type == self.band_stop_filter:
                low_cutoff_label = QtWidgets.QLabel('Low Cut - off Frequency(Hz):')
                low_cutoff_edit = self.filter_checkboxes[filter_type]["low_cutoff_edit"]
                low_cutoff_edit.setText(str(self.bandstop_default_low_cutoff))
                high_cutoff_label = QtWidgets.QLabel('High Cut - off Frequency(Hz):')
                high_cutoff_edit = self.filter_checkboxes[filter_type]["high_cutoff_edit"]
                high_cutoff_edit.setText(str(self.bandstop_default_high_cutoff))
                low_cutoff_layout = QtWidgets.QHBoxLayout()
                low_cutoff_layout.addWidget(low_cutoff_label)
                low_cutoff_layout.addWidget(low_cutoff_edit)
                high_cutoff_layout = QtWidgets.QHBoxLayout()
                high_cutoff_layout.addWidget(high_cutoff_label)
                high_cutoff_layout.addWidget(high_cutoff_edit)
                bandstop_cutoff_layout = QtWidgets.QVBoxLayout()
                bandstop_cutoff_layout.addLayout(low_cutoff_layout)
                bandstop_cutoff_layout.addLayout(high_cutoff_layout)
                left_layout.addLayout(bandstop_cutoff_layout)

        self.set_all_checkboxes_enable(False)

        self.channel_layout = QtWidgets.QVBoxLayout()

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        right_layout.addWidget(self.toolbar, alignment=QtCore.Qt.AlignCenter)
        right_layout.addWidget(self.canvas)
        right_layout.addLayout(self.channel_layout)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 9)

        main_layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(main_layout)

        self.setWindowTitle('EEG Data Demonstration Interface')
        self.resize(1000, 600)
        self.show()

        # 初始化设备相关变量
        self.params = None
        self.board_shim = None
        self.lines = []
        self.eeg_channels = []
        
    def handle_period_selection(self):
        selected_text = self.period_combo_box.currentText()
        logger.info(f"周期: {selected_text}")
        # 在这里添加根据选择执行具体停止相关逻辑的代码，例如调用不同的停止函数等

        if selected_text == "1s":
            self.period = 1
        elif selected_text == "5s":
            self.period = 5
        elif selected_text == "10s":
            self.period = 10
        self.update_buffer_size()

    def update_buffer_size(self):
        # 根据选择的时间调整缓冲区大小
        sampling_rate = self.board_shim.get_sampling_rate(self.board_id)
        buffer_size = int(self.period * sampling_rate)
        if self.data_buffer is not None:
            # 保留现有数据并调整缓冲区大小
            current_data_size = min(self.data_buffer.shape[1], buffer_size)
            new_data_buffer = np.zeros((len(self.eeg_channels), buffer_size))
            new_data_buffer[:, -current_data_size:] = self.data_buffer[:, -current_data_size:]
            self.data_buffer = new_data_buffer
        else:
            self.data_buffer = np.zeros((len(self.eeg_channels), buffer_size))
        self.buffer_index = min(self.buffer_index, buffer_size)
            
    def set_all_checkboxes_enable(self, enabled):
        for filter_type in self.filter_checkboxes.keys():
            checkbox = self.filter_checkboxes[filter_type]["checkbox"]
            if checkbox:
                checkbox.setEnabled(enabled)
                
    def connect_device(self):
        # 获取用户输入的 MAC 地址和 board_id
        mac_address = self.mac_edit.text()
        board_id_text = self.board_id_edit.text()

        try:
            # 设置脑电设备相关参数
            self.board_id = int(board_id_text)
            self.params = brainflow.BrainFlowInputParams()
            self.params.timeout = 40
            if mac_address:
                self.params.mac_address = mac_address
            self.board_shim = BoardShim(self.board_id, self.params)
            # 准备会话并开始数据采集
            self.board_shim.prepare_session()
            # 获取脑电通道列表
            self.eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            # self.data_buffer = np.zeros((self.eeg_channels, 0))  # 明确初始化为各通道长度为0的数组
            # self.buffer_index = 0
            # 启用开始采集按钮
            self.start_button.setEnabled(True)
            self.connect_button.setEnabled(False)
            # 弹出连接成功提示框
            QtWidgets.QMessageBox.information(self, "Connected successfully", "The electroencephalogram (EEG) device has been successfully connected！")

            # 根据通道数量判断使用何种布局来放置通道复选框
            if len(self.eeg_channels) <= 6:
                self.create_channel_checkboxes_vertical()
            else:
                self.create_channel_checkboxes_grid()
            self.stop = False
            self.pause = False
        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Connection failed", f"The format of the entered Board ID is incorrect. Please enter the Board ID in integer type. Error message：{str(ve)}")
        except brainflow.BrainFlowError as bfe:
            QtWidgets.QMessageBox.critical(self, "Connection failed", f"There is an error in the connection of the electroencephalogram (EEG) device. Possible reasons may include that the device is not turned on, the MAC address is incorrect, or there are driver issues, etc. Error message：{str(bfe)}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Connection failed", f"The device connection failed due to an unknown error. Please check the relevant configurations and the device status. Error message：{str(e)}")

    def create_channel_checkboxes_vertical(self):
        for channel in self.eeg_channels:
            checkbox = QtWidgets.QCheckBox(f'Channel {channel}')
            checkbox.setChecked(True)  # 默认勾选所有通道
            checkbox.stateChanged.connect(self.update_channel_visibility)
            self.channel_checkboxes.append(checkbox)
            self.channel_layout.addWidget(checkbox)

    def create_channel_checkboxes_grid(self):
        grid_layout = QtWidgets.QGridLayout()
        row = 0
        col = 0
        max_columns = 4  # 最大列数设置为3，可根据需要调整
        for channel in self.eeg_channels:
            checkbox = QtWidgets.QCheckBox(f'Channel {channel}')
            if channel==1:
                checkbox.setChecked(True)  # 默认勾选所有通道
            else:
                checkbox.setChecked(False)
            checkbox.stateChanged.connect(self.update_channel_visibility)
            self.channel_checkboxes.append(checkbox)
            grid_layout.addWidget(checkbox, row, col)
            col += 1
            if col >= max_columns:
                col = 0
                row += 1
        self.channel_layout.addLayout(grid_layout)

    def start_real_time_collection(self):
        try:
            self.board_shim.start_stream()
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.connect_button.setEnabled(False)
            self.stop = False
            self.timer_stopped = False
            self.set_all_checkboxes_enable(True)

            # 开始实时更新图形
            # self.timer = self.startTimer(100)  # 每 100 毫秒更新一次
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.timerEvent)
            self.timer.start(100)
        except brainflow.BrainFlowError as bfe:
            QtWidgets.QMessageBox.critical(self, "Data acquisition failed to start", f"An error occurred while preparing the session or starting the data stream. Please check the device connection and other relevant conditions. Error message：{str(bfe)}")
        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Data buffer initialization failed", str(ve))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Unknown error", f"An unknown error occurred while starting the real-time data collection. Please check the relevant configurations and code logic. Error message：{str(e)}")

    def check_filter(self):
        sampling_rate = self.board_shim.get_sampling_rate(self.board_id)
        # logger.info(f'check_filter:self.current_filter= {self.current_filter}')
        if self.current_filter is not None: 
            if self.current_filter == self.low_pass_filter:
                self.apply_filter_to_data(sampling_rate, self.low_pass_filter, self.current_cutoff_freq)
            elif self.current_filter == self.high_pass_filter:
                self.apply_filter_to_data(sampling_rate, self.high_pass_filter, self.current_cutoff_freq)
            elif self.current_filter == self.band_pass_filter:
                self.apply_filter_to_data(sampling_rate, self.band_pass_filter, self.current_low_cutoff_freq,self.current_high_cutoff_freq)
            elif self.current_filter == self.band_stop_filter:
                self.apply_filter_to_data(sampling_rate, self.band_stop_filter, self.current_low_cutoff_freq, self.current_high_cutoff_freq)
                
        logger.info(f'check_filter,filter_type={self.current_filter}')
        
    def timerEvent(self):
        """
        定时器触发时执行的函数，用于从板子获取数据、处理数据并更新波形显示，确保坐标轴显示最近1秒的实时内容。
        """
        if self.paused or self.stop:
            return
        try:
            # 从板子获取数据（这里获取1秒的数据点）
            # sampling_rate = self.board_shim.get_sampling_rate(self.board_id)
            
            new_data = self.board_shim.get_board_data(250)
            new_data_channels = new_data[self.eeg_channels, :]
            # 数据缓冲区管理
            if self.data_buffer is None:
               self.data_buffer = new_data_channels
            else:
                # 移除旧数据，添加新数据
                self.data_buffer = np.hstack((self.data_buffer[:, new_data_channels.shape[1]:], new_data_channels))
            self.buffer_index = self.data_buffer.shape[1]
            self.check_filter()
            # 更新图形
            time_axis = np.linspace(0, int(self.period), self.buffer_index)  # 固定时间轴为1秒
            self.update_plot(time_axis)
        except brainflow.BrainFlowError as bfe:
            logging.error(f"从板子获取数据出错: {str(bfe)}")
        except Exception as e:
            logging.error(f"处理数据时出现未知错误: {str(e)}")

    def update_plot(self, time_axis):
        """
        根据当前数据缓冲区的数据更新图形绘制。
        """
        self.ax.clear()
        
        for channel in range(len(self.eeg_channels)):
            if self.channel_checkboxes[channel].isChecked():
                self.ax.plot(time_axis, self.data_buffer[channel, :self.buffer_index],
                             label=f'Channel {self.eeg_channels[channel]}')
        self.ax.set_xlim(0, int(self.period))  # 固定x轴范围为1秒
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude (uV)')
        self.ax.set_title('EEG Waveform (Real-time)')
        self.ax.legend(loc='upper right')
        self.fig.canvas.draw_idle()
        
    def pause_real_time_collection(self):
        """
        暂停实时数据采集，备份当前数据缓冲区状态及索引。
        """
        if not self.paused:
            self.paused = True
            self.paused_data_buffer = self.data_buffer.copy() if self.data_buffer is not None else None
            self.paused_buffer_index = self.buffer_index
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
            self.stop_button.setEnabled(True)

    def resume_real_time_collection(self):
        """
        恢复实时数据采集，恢复之前备份的数据缓冲区状态及索引。
        """
        if self.paused:
            self.paused = False
            self.data_buffer = self.paused_data_buffer
            self.buffer_index = self.paused_buffer_index
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            if not isinstance(self.timer, QTimer):
                self.timer = self.startTimer(100)
            elif not self.timer.isActive():
                self.timer.start(100)

    def stop_real_time_collection(self):
        """
        停止实时数据采集，释放板子资源，清空数据缓冲区及图形绘制内容，重置相关按钮状态。
        """
        if self.board_shim is not None:
            try:
                self.board_shim.stop_stream()
                self.board_shim.release_session()
                if self.timer is not None and self.timer.isActive():
                    self.timer.stop()
                    self.timer  = None
            except brainflow.BrainFlowError as bfe:
                logging.error(f"停止数据采集或释放资源出错: {str(bfe)}")
            self.stop = False
            self.paused = False
            self.connect_button.setEnabled(True)
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.data_buffer = None
            self.buffer_index = 0
            self.ax.clear()
            self.fig.canvas.draw_idle()

    def update_channel_visibility(self):
        """
        根据通道复选框的勾选状态更新图形中通道数据的显示。
        """
        sampling_rate = self.board_shim.get_sampling_rate(self.board_id)
        if self.buffer_index > 0:
            time_axis = np.arange(0, self.buffer_index) / sampling_rate
            self.ax.clear()
            for channel in range(len(self.eeg_channels)):
                if self.channel_checkboxes[channel].isChecked():
                    self.ax.plot(time_axis, self.data_buffer[channel, :self.buffer_index], label=f'Channel {self.eeg_channels[channel]}')
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Amplitude (uV)')
            self.ax.set_title('EEG Waveform (Real-time)')
            self.ax.legend(loc='upper right')
            self.fig.canvas.draw_idle()

    def apply_filter(self):
        """
        根据用户选择的滤波器类型及参数，对当前数据缓冲区的数据应用相应滤波器。
        """
        sampling_rate = self.board_shim.get_sampling_rate(self.board_id)
        for filter_type in self.filter_checkboxes:
            checkbox = self.filter_checkboxes[filter_type]["checkbox"]
            if checkbox.isChecked():
                cutoff_edits = self.filter_checkboxes[filter_type].get("cutoff_edit", [])
                if filter_type == self.low_pass_filter:
                    cutoff_frequency = float(cutoff_edits.text()) if cutoff_edits else self.lowpass_default_cutoff
                    self.apply_filter_to_data(sampling_rate, self.low_pass_filter, cutoff_frequency)
                    self.current_filter = filter_type
                    self.current_cutoff_freq = cutoff_frequency
                    break
                elif filter_type == self.high_pass_filter:
                    cutoff_frequency = float(cutoff_edits.text()) if cutoff_edits else self.highpass_default_cutoff
                    self.apply_filter_to_data(sampling_rate, self.high_pass_filter, cutoff_frequency)
                    self.current_filter = filter_type
                    self.current_cutoff_freq = cutoff_frequency
                    break
                elif filter_type == self.band_pass_filter:
                    low_cutoff_frequency = float(cutoff_edits[0].text()) if cutoff_edits else self.bandpass_default_low_cutoff
                    high_cutoff_frequency = float(cutoff_edits[1].text()) if cutoff_edits else self.bandpass_default_high_cutoff
                    self.apply_filter_to_data(sampling_rate, self.band_pass_filter, low_cutoff_frequency, high_cutoff_frequency)
                    self.current_filter = self.band_pass_filter
                    self.current_low_cutoff_freq = low_cutoff_frequency
                    self.current_high_cutoff_freq = high_cutoff_frequency
                    break
                elif filter_type == self.band_stop_filter:
                    low_cutoff_frequency = float(cutoff_edits[0].text()) if cutoff_edits else self.bandstop_default_low_cutoff
                    high_cutoff_frequency = float(cutoff_edits[1].text()) if cutoff_edits else self.bandstop_default_high_cutoff
                    self.apply_filter_to_data(sampling_rate, self.band_stop_filter, low_cutoff_frequency, high_cutoff_frequency)
                    self.current_filter = self.band_stop_filter
                    self.current_low_cutoff_freq = low_cutoff_frequency
                    self.current_high_cutoff_freq = high_cutoff_frequency
                    break
            else:
                self.current_filter = None
                self.current_cutoff_freq = 0.0
                self.current_low_cutoff_freq = 0.0
                self.current_high_cutoff_freq =0.0
                
        # logger.info(f'apply_filter,filter_type={self.current_filter}')
     
    def apply_filter_to_data(self, sampling_rate, filter_type, *cutoff_frequencies):
        """
        具体执行对数据应用指定滤波器的操作。

        参数:
        sampling_rate (int): 采样率。
        filter_type (str): 滤波器类型，如'Low - Pass Filter'等。
        cutoff_frequencies (tuple): 滤波器相关截止频率参数（不同滤波器参数个数不同）。
        """
        # logger.info(f'apply_filter_to_data,filter_type={filter_type}')
        for channel in range(self.data_buffer.shape[0]):
            channel_data = self.data_buffer[channel, :].flatten()
            if filter_type == self.low_pass_filter:
                DataFilter.perform_lowpass(channel_data, sampling_rate, cutoff_frequencies[0], 2, FilterTypes.BUTTERWORTH.value, 0)
            elif filter_type == self.high_pass_filter:
                DataFilter.perform_highpass(channel_data, sampling_rate, cutoff_frequencies[0], 2, FilterTypes.BUTTERWORTH.value, 0)
            elif filter_type == self.band_pass_filter:
                DataFilter.perform_bandpass(channel_data, sampling_rate, cutoff_frequencies[0], cutoff_frequencies[1], 2, FilterTypes.BUTTERWORTH.value, 0)
            elif filter_type == self.band_stop_filter:
                DataFilter.perform_bandstop(channel_data, sampling_rate, cutoff_frequencies[0], cutoff_frequencies[1], 2, FilterTypes.BUTTERWORTH.value, 0)
            self.data_buffer[channel, :] = channel_data.reshape(1, -1)
                
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = EEGDataVisualizer()
    sys.exit(app.exec_())