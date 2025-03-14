import asyncio
import unittest
import time
import signal
from typing import List
from sensor import SensorController, SensorProfile, BLEDevice, DeviceStateEx, DataType

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCAN_DEVICE_PERIOD_IN_MS = 5000
WAIT_SCAN_RESULT = SCAN_DEVICE_PERIOD_IN_MS / 1000 + 3
discovered_devices = []

def device_found_callback(deviceList: List[BLEDevice]):
    global discovered_devices
    filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
    for device in filteredDevice:
        if device.Address not in [d.Address for d in discovered_devices]:
            discovered_devices.append(device)
            print(f'device.Address = {device.Address }, device.RSSI = {device.RSSI}, device.RSSI = {device.RSSI}.\n')
    # logger.info("Device found callback triggered.")
    logger.info(f'{len(discovered_devices)} Bluetooth devices found in total.\n')

def wait_for_state(profile, target_state, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if profile.deviceState == target_state:
            return True
        time.sleep(0.5)
    return False

class TestSensorController(unittest.TestCase):
    def setUp(self):
        logger.info("TestSensorController -> set up")
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        self.controller = SensorController()
        if self.controller is None:
            logger.error("create SensorController fail,Skipping tests.\n")
            self.skipTest("create SensorController fail.")
            
        if not self.controller.isEnable:
            logger.error("Bluetooth is not enabled. Skipping tests.\n")
            self.skipTest("Bluetooth is not enabled.")
            
        if not self.controller.hasDeviceFoundCallback:
            self.controller.onDeviceFoundCallback = device_found_callback
            logger.info("Device found callback set successfully.\n")

    def tearDown(self):
        logger.info('TestSensorController -> tear down')
        try:
            self.controller.onDeviceFoundCallback = None
            # self.controller.terminate()
            self.controller = None
            global discovered_devices
            discovered_devices = []
            # self.loop.close()
            logger.info('TestSensorController -> tear down successfully.\n')
        except Exception as e:
            logger.error(f'TestSensorController -> Error in tear down: {e}\n')

    def test_start_scan(self):
        logger.info('\nTesting startScan method')
        success = self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(success, True, "Failed to start scan.")
        self.assertEqual(self.controller.isScanning, True, "Scan did not start as expected.")
        time.sleep(WAIT_SCAN_RESULT)

    def test_scan_once(self):
        logger.info('\nTesting scan method')
        ble_devices = self.controller.scan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(isinstance(ble_devices, list), True, "scan method should return a list.")
        
    async def test_asyncScan(self):
        logger.info('\nTesting asyncScan method')
        deviceList = await self.controller.asyncScan(3000)
        self.assertEqual(isinstance(deviceList, list), True, "scan method should return a list.")

    def test_stop_scan(self):
        logger.info('\nTesting stopScan method')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        self.controller.stopScan()
        self.assertEqual(self.controller.isScanning, False, "Failed to stop scan.")

    def test_check_scanning(self):
        logger.info('\nTesting isScanning property')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        is_scanning = self.controller.isScanning
        self.assertEqual(isinstance(is_scanning, bool), True, "isScanning should return a boolean.")
        self.controller.stopScan()

    def test_check_bluetooth_enabled(self):
        logger.info('\nTesting isEnable property')
        is_enabled = self.controller.isEnable
        self.assertEqual(isinstance(is_enabled, bool), True, "isEnable should return a boolean.")

    def test_require_sensor(self):
        logger.info('\nTesting requireSensor method')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = self.controller.requireSensor(device)
            self.assertEqual(isinstance(sensor_profile, SensorProfile) or sensor_profile is None, True,
                             "requireSensor should return a SensorProfile or None.")
        else:
            logger.warning("No devices were discovered. Skipping requireSensor test.")

    def test_get_sensor(self):
        logger.info('\nTesting getSensor method')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = self.controller.requireSensor(device)
            retrieved_sensor = self.controller.getSensor(device.Address)
            if sensor_profile:
                self.assertEqual(retrieved_sensor, sensor_profile, "Failed to get the correct SensorProfile.")
            else:
                self.assertEqual(retrieved_sensor, None, "getSensor should return None when SensorProfile is not created.")
        else:
            logger.warning("No devices were discovered. Skipping getSensor test.")

    def test_get_connected_sensors(self):
        logger.info('\nTesting getConnectedSensors method')
        sensor_profiles = self.controller.getConnectedSensors()
        self.assertEqual(isinstance(sensor_profiles, list), True, "getConnectedSensors should return a list.")

    def test_get_connected_devices(self):
        logger.info('\nTesting getConnectedDevices method')
        ble_devices = self.controller.getConnectedDevices()
        self.assertEqual(isinstance(ble_devices, list), True, "getConnectedDevices should return a list.")
        
    @unittest.skip('terminate method call only once in app life cycle, just skip it.')
    def test_terminate(self):
        logger.info('\nTesting terminate method')
        try:
            self.controller.terminate()
            self.assertEqual(True, True, "Terminate method should execute without errors.")
        except Exception as e:
            self.fail(f"Terminate method raised an exception: {e}")

class TestSensorProfile(unittest.TestCase):
    def setUp(self):
        logger.info("TestSensorProfile -> set up")
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        self.controller = SensorController()
        if self.controller is None:
            logger.error('create SensorController fail, Skipping tests.\n')
            self.skipTest('create SensorController fail.')
            
        if not self.controller.isEnable:
            logger.error('Bluetooth is not enabled. Skipping tests.\n')
            self.skipTest('Bluetooth is not enabled.')
            
        if not self.controller.hasDeviceFoundCallback:
            self.controller.onDeviceFoundCallback = device_found_callback
            logger.info('Device found callback set successfully.\n')

        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT)
        global discovered_devices
        if discovered_devices:
            device = discovered_devices[0]
            self.profile = self.controller.requireSensor(device)
            if self.profile is None:
                logger.error('Failed to create SensorProfile. Skipping tests.\n')
                self.skipTest('Failed to create SensorProfile.')

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
            logger.warning('No devices were discovered. Skipping SensorProfile tests.\n')
            self.skipTest('No devices were discovered.')

    def tearDown(self):
        logger.info("TestSensorProfile -> tear down")
        try:
            if hasattr(self, 'profile'):
                self.profile.disconnect()
            self.controller.onDeviceFoundCallback = None
            # self.controller.terminate()
            self.controller = None
            global discovered_devices
            discovered_devices = []
            # self.loop.close()
            logger.info('TestSensorProfile -> tear down successfully.\n')
        except Exception as e:
             logger.error(f'TestSensorProfile -> Error in tear down: {e}\n')

    def test_connect(self):
        logger.info('\nTesting connect method')
        success = self.profile.connect()
        
        self.assertEqual(success, True, 'Failed to connect to device.')
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_disconnect(self):
        logger.info('\nTesting disconnect method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        success = self.profile.disconnect()
        self.assertEqual(success, True, 'Failed to disconnect from device.')
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_get_device_status(self):
        logger.info('\nTesting deviceState property')
        device_state = self.profile.deviceState
        self.assertEqual(isinstance(device_state, DeviceStateEx), True, 'deviceState should return a DeviceStateEx enum.')

    def test_get_ble_device(self):
        logger.info('\nTesting BLEDevice property')
        ble_device = self.profile.BLEDevice
        self.assertEqual(isinstance(ble_device, BLEDevice), True, 'BLEDevice property should return a BLEDevice.')

    def test_get_device_info(self):
        logger.info('\nTesting getDeviceInfo method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
        device_info = self.profile.getDeviceInfo()
        
        if device_info:
            self.assertEqual(isinstance(device_info, dict), True, 'getDeviceInfo should return a dict.')
        else:
            self.assertEqual(device_info, None, 'getDeviceInfo should return None if not connected.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_init_data_transfer(self):
        logger.info('\nTesting init method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        success = self.profile.init(5, 60 * 1000)
        self.assertEqual(success, True, 'Failed to initialize data transfer.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_check_init_data_transfer(self):
        logger.info('\nTesting hasInited property')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        has_inited = self.profile.hasInited
        self.assertEqual(isinstance(has_inited, bool), True, 'hasInited should return a boolean.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_start_data_notification(self):
        logger.info('\nTesting startDataNotification method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            success = self.profile.startDataNotification()
            self.assertEqual(success, True, 'Failed to start data notification.')
            self.profile.stopDataNotification()
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_stop_data_notification(self):
        logger.info('\nTesting stopDataNotification method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            self.profile.startDataNotification()
            success = self.profile.stopDataNotification()
            self.assertEqual(success, True, 'Failed to stop data notification.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_check_data_transfering(self):
        logger.info('\nTesting isDataTransfering property...')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            self.profile.startDataNotification()
            is_transfering = self.profile.isDataTransfering
            self.assertEqual(isinstance(is_transfering, bool), True, 'isDataTransfering should return a boolean.')
            self.profile.stopDataNotification()
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_get_battery_level(self):
        logger.info('\nTesting getBatteryLevel method')
        self.profile.connect()
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        battery_power = self.profile.getBatteryLevel()
        self.assertEqual(isinstance(battery_power, int), True, 'getBatteryLevel should return an integer.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_set_param(self):
        logger.info('\nTesting setParam method')
        self.profile.connect()
        if not wait_for_state(self.profile, DeviceStateEx.Ready):
            self.fail('Device did not reach Ready state within timeout.')
            
        result = self.profile.setParam("NTF_EMG", "ON")
        print(f'result = {result}')
        self.assertEqual(result, "OK", 'Failed to set parameter.')
        
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected):
            self.fail('Device did not reach Disconnected state within timeout.')


if __name__ == "__main__":
    unittest.main()