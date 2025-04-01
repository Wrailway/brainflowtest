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
specified_mac = '24:71:89:EF:2F:B7'

def device_found_callback(deviceList: List[BLEDevice]):
    global discovered_devices
    filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
    # filteredDevice = filter(lambda x: x.Address == specified_mac, deviceList)
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
            if self.controller.isScanning:
                self.controller.stopScan()
            self.controller.onDeviceFoundCallback = None
            # self.controller.terminate()
            self.controller = None
            global discovered_devices
            discovered_devices = []
            logger.info('TestSensorController -> tear down successfully.\n')
        except Exception as e:
            logger.error(f'TestSensorController -> Error in tear down: {e}\n')

    def test_start_scan(self):
        logger.info('\nTesting startScan method')
        success = self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(success, True, "Failed to start scan.")
        self.assertEqual(self.controller.isScanning, True, "Scan did not start as expected.")

    def test_scan_once(self):
        logger.info('\nTesting scan method')
        ble_devices = self.controller.scan(SCAN_DEVICE_PERIOD_IN_MS)
        self.assertEqual(isinstance(ble_devices, list), True, "scan method should return a list.")
        
    def test_stop_scan(self):
        logger.info('\nTesting stopScan method')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        self.controller.stopScan()
        self.assertEqual(self.controller.isScanning, False, "Scan did not stop as expected.")

    def test_check_scanning(self):
        logger.info('\nTesting isScanning property')
        self.controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        self.assertEqual(self.controller.isScanning, True, "start scan,isScanning should return true.")
        self.controller.stopScan()
        self.assertEqual(self.controller.isScanning, False, "stop scan,isScanning should return false.")

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
            if self.controller.isScanning:
                self.controller.stopScan()
            # self.controller.terminate()
            self.controller = None
            global discovered_devices
            discovered_devices = []
            logger.info('TestSensorProfile -> tear down successfully.\n')
        except Exception as e:
             logger.error(f'TestSensorProfile -> Error in tear down: {e}\n')

    def test_connect(self):
        logger.info('\nTesting connect method')
        success = self.profile.connect()
        
        self.assertEqual(success, True, 'Failed to connect to device.')
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_disconnect(self):
        logger.info('\nTesting disconnect method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        success = self.profile.disconnect()
        self.assertEqual(success, True, 'Failed to disconnect from device.')
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
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
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        device_info = self.profile.getDeviceInfo()
        if device_info:
            self.assertEqual(isinstance(device_info, dict), True, 'getDeviceInfo should return a dict.')
        else:
            self.assertEqual(device_info, None, 'getDeviceInfo should return None if not connected.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_init_data_transfer(self):
        logger.info('\nTesting init method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        success = self.profile.init(5, 60 * 1000)
        self.assertEqual(success, True, 'Failed to initialize data transfer.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_check_init_data_transfer(self):
        logger.info('\nTesting hasInited property')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        has_inited = self.profile.hasInited
        self.assertEqual(isinstance(has_inited, bool), True, 'hasInited should return a boolean.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_start_data_notification(self):
        logger.info('\nTesting startDataNotification method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            success = self.profile.startDataNotification()
            self.assertEqual(success, True, 'Failed to start data notification.')
            self.profile.stopDataNotification()
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_stop_data_notification(self):
        logger.info('\nTesting stopDataNotification method')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            self.profile.startDataNotification()
            success = self.profile.stopDataNotification()
            self.assertEqual(success, True, 'Failed to stop data notification.')
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_check_data_transfering(self):
        logger.info('\nTesting isDataTransfering property...')
        self.profile.connect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        self.profile.init(5, 60 * 1000)
        if self.profile.hasInited:
            self.profile.startDataNotification()
            is_transfering = self.profile.isDataTransfering
            self.assertEqual(isinstance(is_transfering, bool), True, 'isDataTransfering should return a boolean.')
            self.profile.stopDataNotification()
            
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_get_battery_level(self):
        logger.info('\nTesting getBatteryLevel method')
        self.profile.connect()
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        battery_power = self.profile.getBatteryLevel()
        self.assertEqual(isinstance(battery_power, int), True, 'getBatteryLevel should return an integer.')
        self.profile.disconnect()
        
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')

    def test_set_param(self):
        logger.info('\nTesting setParam method')
        self.profile.connect()
        if not wait_for_state(self.profile, DeviceStateEx.Ready,timeout=15):
            self.fail('Device did not reach Ready state within timeout.')
            
        result = self.profile.setParam("NTF_EMG", "ON")
        print(f'result = {result}')
        self.assertEqual(result, "OK", 'Failed to set parameter.')
        
        self.profile.disconnect()
        if not wait_for_state(self.profile, DeviceStateEx.Disconnected,timeout=15):
            self.fail('Device did not reach Disconnected state within timeout.')
            
            
class TestSensorControllerAsyncMethods(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.controller = SensorController()
        self.period = 5000  # 扫描时长，单位毫秒

    async def scan_and_get_device(self):
        """扫描设备并获取第一个设备"""
        devices = await self.controller.asyncScan(self.period)
        if not devices:
            self.skipTest("未扫描到任何设备，跳过测试。")
        return devices[0]

    async def connect_device(self, sensor):
        """连接设备"""
        try:
            if sensor.deviceState != DeviceStateEx.Ready:
                await sensor.asyncConnect()
                await asyncio.sleep(5)  # 等待连接完成
                if sensor.deviceState != DeviceStateEx.Ready:
                    raise Exception("设备未成功连接")
        except Exception as e:
            self.fail(f"连接设备时出错: {str(e)}")

    async def disconnect_device(self, sensor):
        """断开设备连接"""
        try:
            await sensor.asyncDisconnect()
            await asyncio.sleep(2)  # 等待断开连接完成
            if sensor.deviceState != DeviceStateEx.Disconnected:
                raise Exception("设备未成功断开连接")
        except Exception as e:
            self.fail(f"断开设备连接时出错: {str(e)}")

    async def test_asyncScan(self):
        """测试 asyncScan 方法"""
        devices = await self.controller.asyncScan(self.period)
        self.assertEqual(isinstance(devices, list), True)
        if devices:
            print(f"扫描到的设备: {[device.Address for device in devices]}")
            # 检查扫描到的设备列表中的每个设备是否是 BLEDevice 类型
            for device in devices:
                self.assertEqual(isinstance(device, BLEDevice), True)
        else:
            print("未扫描到任何设备。")

    async def test_asyncStartAndStopDataNotification(self):
        """测试 asyncStartDataNotification 和 asyncStopDataNotification 方法"""
        device = await self.scan_and_get_device()
        sensor = self.controller.requireSensor(device)
        await self.connect_device(sensor)
        await asyncio.sleep(15)
        try:
            # 启动数据通知
            start_result = await sensor.asyncStartDataNotification()
            # self.assertEqual(start_result, True)
            print("数据通知已启动。")

            # 等待一段时间以接收数据
            await asyncio.sleep(15)

            # 检查数据是否正在传输
            self.assertEqual(isinstance(sensor.isDataTransfering, bool), True)

            # 停止数据通知
            stop_result = await sensor.asyncStopDataNotification()
            await asyncio.sleep(15)
            # self.assertEqual(stop_result, True)
            print("数据通知已停止。")

            # 再次检查数据是否停止传输
            self.assertEqual(sensor.isDataTransfering, False)
        finally:
            await self.disconnect_device(sensor)

    async def test_asyncSetParam(self):
        """测试 asyncSetParam 方法"""
        device = await self.scan_and_get_device()
        sensor = self.controller.requireSensor(device)
        await self.connect_device(sensor)

        try:
            param_key = "NTF_EMG"
            param_value = "ON"
            set_result = await sensor.asyncSetParam(param_key, param_value)
            self.assertEqual(set_result, "OK")
            print(f"参数 {param_key} 已设置为 {param_value}。")

        finally:
            await self.disconnect_device(sensor)

    async def test_asyncConnectDisconnect(self):
        """测试设备的异步连接和断开连接"""
        device = await self.scan_and_get_device()
        sensor = self.controller.requireSensor(device)

        try:
            # 连接设备
            connect_result = await sensor.asyncConnect()
            self.assertEqual(connect_result, True)
            await asyncio.sleep(15)
            self.assertEqual(sensor.deviceState, DeviceStateEx.Ready)

            # 断开设备
            disconnect_result = await sensor.asyncDisconnect()
            self.assertEqual(disconnect_result, True)
            await asyncio.sleep(15)
            self.assertEqual(sensor.deviceState, DeviceStateEx.Disconnected)
        except Exception as e:
            self.fail(f"连接或断开设备时出错: {str(e)}")


class TestSensorProfileAsyncMethods(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.controller = SensorController()
        self.period = 5000  # 扫描时长，单位毫秒
        devices = await self.controller.asyncScan(self.period)
        if not devices:
            self.skipTest("未扫描到任何设备，跳过测试。")
        device = devices[0]
        self.sensor = self.controller.requireSensor(device)

    async def test_asyncInit(self):
        """测试 asyncInit 方法"""
        await self.sensor.asyncConnect()
        await asyncio.sleep(5)
        try:
            if self.sensor.deviceState == DeviceStateEx.Ready:
                result = await self.sensor.asyncInit(5, 60 * 1000)
                self.assertEqual(result, True)
                print("数据采集初始化成功。")
        finally:
            await self.sensor.asyncDisconnect()

    async def test_asyncGetBatteryLevel(self):
        """测试 asyncGetBatteryLevel 方法"""
        await self.sensor.asyncConnect()
        await asyncio.sleep(5)
        try:
            if self.sensor.deviceState == DeviceStateEx.Ready:
                battery_level = self.sensor.getBatteryLevel()
                self.assertEqual(isinstance(battery_level, int), True)
                print(f"获取电池电量: {battery_level}")
        finally:
            await self.sensor.asyncDisconnect()

    async def test_asyncGetDeviceInfo(self):
        """测试 asyncGetDeviceInfo 方法"""
        await self.sensor.asyncConnect()
        await asyncio.sleep(5)
        try:
            if self.sensor.deviceState == DeviceStateEx.Ready:
                device_info = self.sensor.getDeviceInfo()
                if device_info:
                    self.assertEqual(isinstance(device_info, dict), True)
                    print(f"获取设备信息: {device_info}")
                else:
                    self.assertEqual(device_info, None)
                    print("未获取到设备信息")
        finally:
            await self.sensor.asyncDisconnect()

if __name__ == "__main__":
    unittest.main()
    # # 创建一个测试套件
    # suite = unittest.TestSuite()
    # # 向套件中添加指定的测试用例
    # suite.addTest(TestAdd("test_positive_numbers"))

    # # 创建一个测试运行器
    # runner = unittest.TextTestRunner()
    # # 运行测试套件
    # runner.run(suite)