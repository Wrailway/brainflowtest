import time
import pytest
import logging
# 假设 sensor 模块已定义，这里省略其具体实现
from sensor import *


# 设置日志级别为INFO，获取日志记录器实例
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# # 创建一个文件处理器，用于将日志写入文件
# file_handler = logging.FileHandler('test_can_bus_protocol_log.txt')
# file_handler.setLevel(logging.DEBUG)

# # 创建一个日志格式
# log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(log_format)

# # 将文件处理器添加到日志记录器
# logger.addHandler(file_handler)
console_handler = logging.StreamHandler()

# 设置处理程序的日志级别为 INFO
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

SCAN_DEVICE_PERIOD_IN_MS = 3000

class TestSynchroniSdkApi:
            
    @pytest.fixture(autouse=True)
    def enter_and_exit(self):
        """
        pytest 夹具，用于初始化 sensor controller,并在测试结束后释放掉
        """
        self.SensorControllerInstance = SensorController()
        if self.SensorControllerInstance is None or not self.SensorControllerInstance.isEnable:
            logger.error("Could not create sensor controller or Please check whether Bluetooth is turned on. Skipping tests.")
            pytest.skip("Could not create sensor controller or Please check whether Bluetooth is turned on. Skipping tests.")
        logger.info("\nBluetooth is turned on.\n")
        
        yield
        try:
            self.SensorControllerInstance.terminate()
            logger.info("\nBluetooth is turned off.\n")
        except Exception as e:
            logger.error(f"Error closing sensor controller: {e}")
        
            
    def test_startScan(self):
        print(f'test bluetooth start Scan api.\n')
        assert self.SensorControllerInstance.startScan(SCAN_DEVICE_PERIOD_IN_MS), f'Can not start the scan.'
        assert self.SensorControllerInstance.isScaning,f'Can not start the scan.'
        
    def test_stopScan(self):
        print(f'test bluetooth stop Scan api.\n')
        self.SensorControllerInstance.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        self.SensorControllerInstance.stopScan()
        assert not self.SensorControllerInstance.isScaning, f'Can not stop the scan.'