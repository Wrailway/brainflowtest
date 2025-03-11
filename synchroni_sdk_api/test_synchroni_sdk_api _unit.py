import unittest
import time
import signal
from typing import List
from sensor import SensorController, SensorProfile, BLEDevice, DeviceStateEx, DataType

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCAN_DEVICE_PERIOD_IN_MS = 6000
WAIT_SCAN_RESULT = SCAN_DEVICE_PERIOD_IN_MS/1000+3
discovered_devices = []


class TestSensorController(unittest.TestCase):
    def setUp(self):
        logger.info("Setting up sensor controller...")
        self.controller = SensorController()
        if self.controller is None:
            logger.error("create SensorController fail,Skipping tests.")
            self.skipTest("create SensorController fail.")
            
        if not self.controller.isEnable:
            logger.error("Bluetooth is not enabled. Skipping tests.")
            self.skipTest("Bluetooth is not enabled.")
            
        if not self.controller.hasDeviceFoundCallback:
            self.controller.onDeviceFoundCallback = self.device_found_callback
            logger.info("Device found callback set successfully.")

    def tearDown(self):
        logger.info("Tearing down sensor controller...")
        try:
            self.controller.onDeviceFoundCallback = None
            self.controller.terminate()
            self.controller = None
            discovered_devices.clear()
            logger.info("SDK terminated successfully.\n")
        except Exception as e:
            logger.error(f"Error terminating SDK: {e}\n")

    

    def test_start_scan(self):
        logger.info("Testing startScan method...")
        success = self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(success, True, "Failed to start scan.")
        self.assertEqual(self.controller.isScaning, True, "Scan did not start as expected.")
        time.sleep(WAIT_SCAN_RESULT) # print scan result

    def test_scan_once(self):
        logger.info("Testing scan method...")
        ble_devices = self.controller.scan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(isinstance(ble_devices, list), True, "scan method should return a list.")
        # time.sleep(WAIT_SCAN_RESULT) # print scan result

    def test_stop_scan(self):
        logger.info("Testing stopScan method...")
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)  # 等待扫描开始
        self.controller.stopScan()
        self.assertEqual(self.controller.isScaning, False, "Failed to stop scan.")
        time.sleep(WAIT_SCAN_RESULT)

    def test_check_scanning(self):
        logger.info("Testing isScanning property...")
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        is_scanning = self.controller.isScaning
        self.assertEqual(isinstance(is_scanning, bool), True, "isScanning should return a boolean.")
        self.controller.stopScan()
        time.sleep(WAIT_SCAN_RESULT)

    def test_check_bluetooth_enabled(self):
        logger.info("Testing isEnabled property...")
        is_enabled = self.controller.isEnable
        self.assertEqual(isinstance(is_enabled, bool), True, "isEnabled should return a boolean.")

    def test_require_sensor(self):
        logger.info("Testing requireSensor method...")
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT) #等待扫描结果
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = self.controller.requireSensor(device)
            self.assertEqual(isinstance(sensor_profile, SensorProfile) or sensor_profile is None, True,
                             "requireSensor should return a SensorProfile or None.")
        else:
            logger.warning("No devices were discovered. Skipping requireSensor test.")

    def test_get_sensor(self):
        logger.info("Testing getSensor method...")
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT) #等待扫描结果
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = self.controller.requireSensor(device)
            retrieved_sensor = self.controller.getSensor(device)
            if sensor_profile:
                self.assertEqual(retrieved_sensor, sensor_profile, "Failed to get the correct SensorProfile.")
            else:
                self.assertEqual(retrieved_sensor, None, "getSensor should return None when SensorProfile is not created.")
        else:
            logger.warning("No devices were discovered. Skipping getSensor test.")

    def test_get_connected_sensors(self):
        logger.info("Testing getConnectedSensors method...")
        sensor_profiles = self.controller.getConnectedSensors()
        self.assertEqual(isinstance(sensor_profiles, list), True, "getConnectedSensors should return a list.")

    def test_get_connected_devices(self):
        logger.info("Testing getConnectedDevices method...")
        ble_devices = self.controller.getConnectedDevices()
        self.assertEqual(isinstance(ble_devices, list), True, "getConnectedDevices should return a list.")

    def test_terminate(self):
        logger.info("Testing terminate method...")
        try:
            self.controller.terminate()
            # 可以添加更多验证逻辑，例如检查资源是否正确释放
            self.assertEqual(True, True, "Terminate method should execute without errors.")
        except Exception as e:
            self.fail(f"Terminate method raised an exception: {e}")


class TestSensorProfile(unittest.TestCase):
    def setUp(self):
        logger.info("Setting up sensor controller for SensorProfile tests...")
        self.controller = SensorController()
        if self.controller is None:
            logger.error("create SensorController fail,Skipping tests.")
            self.skipTest("create SensorController fail.")
            
        if not self.controller.isEnable:
            logger.error("Bluetooth is not enabled. Skipping tests.")
            self.skipTest("Bluetooth is not enabled.")
            
        if not self.controller.hasDeviceFoundCallback:
            self.controller.onDeviceFoundCallback = self.device_found_callback
            logger.info("Device found callback set successfully.")

        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT) # 等待测试结果
        if discovered_devices:
            device = discovered_devices[0]
            self.profile = self.controller.requireSensor(device)
            if self.profile is None:
                logger.error("Failed to create SensorProfile. Skipping tests.")
                self.skipTest("Failed to create SensorProfile.")

            # 注册回调
            def on_state_changed(sensor, newState):
                logger.info('device: ' + sensor.BLEDevice.Name + str(newState))

            def on_error_callback(sensor, reason):
                logger.info('device: ' + sensor.BLEDevice.Name + str(reason))

            def on_power_changed(sensor, power):
                logger.info('device: ' + sensor.BLEDevice.Name + str(power))

            def on_data_callback(sensor, data):
                logger.info('device: ' + sensor.BLEDevice.Name + str(data))

            self.profile.onStateChanged = on_state_changed
            self.profile.onErrorCallback = on_error_callback
            self.profile.onPowerChanged = on_power_changed
            self.profile.onDataCallback = on_data_callback
        else:
            logger.warning("No devices were discovered. Skipping SensorProfile tests.")
            self.skipTest("No devices were discovered.")
            
    def tearDown(self):
        logger.info("Tearing down SensorProfile...")
        try:
            if hasattr(self, 'profile'):
                self.profile.disconnect()
            self.controller.onDeviceFoundCallback = None
            self.controller.terminate()
            self.controller = None
            discovered_devices.clear()
            logger.info("SDK terminated successfully.\n")
        except Exception as e:
            logger.error(f"Error disconnecting SensorProfile: {e}")

    def device_found_callback(self, deviceList: List[BLEDevice]):
        global discovered_devices
        filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
        for device in filteredDevice:
            if device.Address not in [d.Address for d in discovered_devices]:
                discovered_devices.append(device)
                print(f'device.Address = {device.Address }, device.Address = {device.RSSI}, device.Address = {device.RSSI}\n')
        # discovered_devices = deviceList
        logger.info("Device found callback triggered.")
        logger.info(f"Discovered devices: {len(discovered_devices)}")

    def test_connect(self):
        logger.info("Testing connect method...")
        success = self.profile.connect()
        self.assertEqual(success, True, "Failed to connect to device.")
        time.sleep(2)  # 等待连接稳定
        self.assertEqual(self.profile.deviceState, DeviceStateEx.Ready, "Device is not in Ready state after connection.")

    def test_disconnect(self):
        logger.info("Testing disconnect method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        success = self.profile.disconnect()
        self.assertEqual(success, True, "Failed to disconnect from device.")
        self.assertEqual(self.profile.deviceState, DeviceStateEx.Disconnected,
                         "Device is not in Disconnected state after disconnection.")

    def test_get_device_status(self):
        logger.info("Testing deviceState property...")
        device_state = self.profile.deviceState
        self.assertEqual(isinstance(device_state, DeviceStateEx), True, "deviceState should return a DeviceStateEx enum.")

    def test_get_ble_device(self):
        logger.info("Testing BLEDevice property...")
        ble_device = self.profile.BLEDevice
        self.assertEqual(isinstance(ble_device, BLEDevice), True, "BLEDevice property should return a BLEDevice.")

    def test_get_device_info(self):
        logger.info("Testing getDeviceInfo method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            device_info = self.profile.getDeviceInfo()
            if device_info:
                self.assertEqual(isinstance(device_info, dict), True, "getDeviceInfo should return a dict.")
            else:
                self.assertEqual(device_info, None, "getDeviceInfo should return None if not connected.")
        else:
            logger.warning("Device is not in Ready state. Skipping getDeviceInfo test.")

    def test_init_data_transfer(self):
        logger.info("Testing init method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            success = self.profile.init(5, 60 * 1000)
            self.assertEqual(success, True, "Failed to initialize data transfer.")
        else:
            logger.warning("Device is not in Ready state. Skipping init data transfer test.")

    def test_check_init_data_transfer(self):
        logger.info("Testing hasInited property...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            self.profile.init(5, 60 * 1000)
            has_inited = self.profile.hasInited
            self.assertEqual(isinstance(has_inited, bool), True, "hasInited should return a boolean.")
        else:
            logger.warning("Device is not in Ready state. Skipping check init data transfer test.")

    def test_start_data_notification(self):
        logger.info("Testing startDataNotification method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            self.profile.init(5, 60 * 1000)
            if self.profile.hasInited:
                success = self.profile.startDataNotification()
                self.assertEqual(success, True, "Failed to start data notification.")
            else:
                logger.warning("Data transfer not initialized. Skipping startDataNotification test.")
        else:
            logger.warning("Device is not in Ready state. Skipping startDataNotification test.")

    def test_stop_data_notification(self):
        logger.info("Testing stopDataNotification method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            self.profile.init(5, 60 * 1000)
            if self.profile.hasInited:
                self.profile.startDataNotification()
                success = self.profile.stopDataNotification()
                self.assertEqual(success, True, "Failed to stop data notification.")
            else:
                logger.warning("Data transfer not initialized. Skipping stopDataNotification test.")
        else:
            logger.warning("Device is not in Ready state. Skipping stopDataNotification test.")

    def test_check_data_transfering(self):
        logger.info("Testing isDataTransfering property...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            self.profile.init(5, 60 * 1000)
            if self.profile.hasInited:
                self.profile.startDataNotification()
                is_transfering = self.profile.isDataTransfering
                self.assertEqual(isinstance(is_transfering, bool), True, "isDataTransfering should return a boolean.")
                self.profile.stopDataNotification()
            else:
                logger.warning("Data transfer not initialized. Skipping check data transfering test.")
        else:
            logger.warning("Device is not in Ready state. Skipping check data transfering test.")

    def test_get_battery_level(self):
        logger.info("Testing getBatteryLevel method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
            battery_power = self.profile.getBatteryLevel()
            self.assertEqual(isinstance(battery_power, int), True, "getBatteryLevel should return an integer.")
        else:
            logger.warning("Device is not in Ready state. Skipping getBatteryLevel test.")

    def test_set_param(self):
        logger.info("Testing setParam method...")
        self.profile.connect()
        time.sleep(2)  # 等待连接稳定
        if self.profile.deviceState == DeviceStateEx.Ready:
          
            result = self.profile.setParam("NTF_EMG", "ON")
            print(f'result = {result}')
            self.assertEqual(result, "OK", "Failed to set parameter.")
        else:
            logger.warning("Device is not in Ready state. Skipping setParam test.")




if __name__ == "__main__":
    unittest.main()