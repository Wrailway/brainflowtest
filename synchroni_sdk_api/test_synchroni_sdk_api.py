import time
from typing import List
import pytest
import asyncio
import pytest_asyncio
from sensor import DeviceInfo, SensorController, SensorProfile, BLEDevice, DeviceStateEx

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 增加扫描时间
SCAN_DEVICE_PERIOD_IN_MS = 60000
ASYNC_SCAN_DEVICE_PERIOD_IN_MS = 5000
WAIT_SCAN_RESULT = SCAN_DEVICE_PERIOD_IN_MS / 1000 + 3
specified_mac =  '24:71:89:EF:2B:E2'  # 'C4:64:E3:D8:ED:68'
MAX_SCAN_RETRIES = 1
TIMEOUT = 30

# 给startScan函数使用的回调
def scan_devices(controller, max_retries=MAX_SCAN_RETRIES):
    discovered_devices = []

    def device_found_callback(deviceList: List[BLEDevice]):
        nonlocal discovered_devices
        try:
            filteredDevice = filter(lambda x: x.Address == specified_mac, deviceList)
            for device in filteredDevice:
                if device.Address not in [d.Address for d in discovered_devices]:
                    discovered_devices.append(device)
                    logger.info(f'device.Address = {device.Address }, device.RSSI = {device.RSSI}')
            logger.info(f'{len(discovered_devices)} Bluetooth devices found in total')
        except Exception as e:
            logger.error(f"Error in device_found_callback: {e}")

    for retry in range(max_retries):
        controller.onDeviceFoundCallback = device_found_callback
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        logger.info(f"Waiting for {WAIT_SCAN_RESULT} seconds to discover devices... (Retry {retry + 1})")
        time.sleep(WAIT_SCAN_RESULT)

        if discovered_devices:
            break

    return discovered_devices

def wait_for_state(profile, target_state, timeout=TIMEOUT):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if profile.deviceState == target_state:
            return True
        time.sleep(0.5)
    return False

class TestSensorController:
    @pytest.fixture(scope="class")
    def controller(self):
        ctrl = SensorController()
        if not ctrl.isEnable:
            pytest.skip("Bluetooth is not enabled")
        yield ctrl
        if ctrl.isScanning:
            ctrl.stopScan()
        ctrl.onDeviceFoundCallback = None

    @pytest.fixture
    def sensor_profile(self, controller):
        discovered_devices = scan_devices(controller)
        if not discovered_devices:
            pytest.skip("No devices discovered after multiple retries")

        device = discovered_devices[0]
        profile = controller.requireSensor(device)

        if not profile:
            pytest.skip("Failed to create SensorProfile")

        # 保存 controller 以便后续使用
        profile._controller = controller

        yield profile

        if profile.deviceState != DeviceStateEx.Disconnected:
            profile.disconnect()
        controller.stopScan()

    def test_start_scan(self, controller):
        logger.info('\nTesting startScan method')
        success = controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        assert success is True
        assert controller.isScanning is True

    def test_scan_once(self, controller):
        logger.info('\nTesting scan method')
        try:
            devices = controller.scan(1000)
            if devices is not None:
                assert isinstance(devices, list)
        except Exception as e:
                logger.error(f"Error in test_scan_once : {e}")
                pytest.fail("Failed to scan devices.")

    def test_stop_scan(self, controller):
        logger.info('\nTesting stopScan method')
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        controller.stopScan()
        time.sleep(1)
        assert controller.isScanning is False

    def test_check_scanning(self, controller):
        logger.info('\nTesting isScanning property')
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        assert controller.isScanning is True
        controller.stopScan()
        assert controller.isScanning is False

    def test_check_bluetooth_enabled(self, controller):
        logger.info('\nTesting isEnable property')
        is_enabled = controller.isEnable
        assert isinstance(is_enabled, bool)

    def test_require_sensor(self, controller):
        logger.info('\nTesting requireSensor method')
        discovered_devices = scan_devices(controller)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = controller.requireSensor(device)
            assert isinstance(sensor_profile, SensorProfile) or sensor_profile is None
        else:
            pytest.skip("No devices discovered after multiple retries")

    def test_get_sensor(self, controller):
        logger.info('\nTesting getSensor method')
        discovered_devices = scan_devices(controller)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = controller.requireSensor(device)
            retrieved_sensor = controller.getSensor(device.Address)
            if sensor_profile:
                assert retrieved_sensor == sensor_profile
            else:
                assert retrieved_sensor is None
        else:
            pytest.skip("No devices discovered after multiple retries")

    def test_get_connected_sensors(self, controller):
        logger.info('\nTesting getConnectedSensors method')
        sensor_profiles = controller.getConnectedSensors()
        assert isinstance(sensor_profiles, list)

    def test_get_connected_devices(self, controller):
        logger.info('\nTesting getConnectedDevices method')
        ble_devices = controller.getConnectedDevices()
        assert isinstance(ble_devices, list)

    def test_connect(self, sensor_profile):
        logger.info('\nTesting connect method')
        success = sensor_profile.connect()
        assert success is True
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_disconnect(self, sensor_profile):
        logger.info('\nTesting disconnect method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        success = sensor_profile.disconnect()
        assert success is True
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_get_device_status(self, sensor_profile):
        logger.info('\nTesting deviceState property')
        device_state = sensor_profile.deviceState
        assert isinstance(device_state, DeviceStateEx)

    def test_get_ble_device(self, sensor_profile):
        logger.info('\nTesting BLEDevice property')
        ble_device = sensor_profile.BLEDevice
        assert isinstance(ble_device, BLEDevice)

    def test_get_device_info(self, sensor_profile):
        logger.info('\nTesting getDeviceInfo method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        device_info = sensor_profile.getDeviceInfo()
        if device_info:
            assert isinstance(device_info, dict)
        else:
            assert device_info is None

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_init_data_transfer(self, sensor_profile):
        logger.info('\nTesting init method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        success = sensor_profile.init(5, 60 * 1000)
        assert success is True

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_check_init_data_transfer(self, sensor_profile):
        logger.info('\nTesting hasInited property')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        sensor_profile.init(5, 60 * 1000)
        has_inited = sensor_profile.hasInited
        assert isinstance(has_inited, bool)

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_start_data_notification(self, sensor_profile):
        logger.info('\nTesting startDataNotification method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            success = sensor_profile.startDataNotification()
            assert success is True
            sensor_profile.stopDataNotification()

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_stop_data_notification(self, sensor_profile):
        logger.info('\nTesting stopDataNotification method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            sensor_profile.startDataNotification()
            success = sensor_profile.stopDataNotification()
            assert success is True

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_check_data_transfering(self, sensor_profile):
        logger.info('\nTesting isDataTransfering property')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            sensor_profile.startDataNotification()
            is_transfering = sensor_profile.isDataTransfering
            assert isinstance(is_transfering, bool)
            sensor_profile.stopDataNotification()

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_get_battery_level(self, sensor_profile):
        logger.info('\nTesting getBatteryLevel method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True
        sensor_profile.init(5, 60 * 1000)
        assert sensor_profile.hasInited is True
        battery_power = sensor_profile.getBatteryLevel()
        assert isinstance(battery_power, int)
        assert 0 <= battery_power <= 100

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

    def test_set_param(self, sensor_profile):
        logger.info('\nTesting setParam method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready) is True

        result = sensor_profile.setParam("NTF_EMG", "ON")
        assert result == "OK"

        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected) is True
        sensor_profile._controller.stopScan()

def find_device_by_mac(devices, mac):
    for device in devices:
        if device.Address == mac:
            return device
    return None

@pytest.mark.asyncio
class TestSensorControllerAsyncMethods:
    @pytest.fixture(scope="class")
    def controller(self):
        print('controller')
        ctrl = SensorController()
        if not ctrl.isEnable:
            pytest.skip("Bluetooth is not enabled")
        yield ctrl
        if ctrl.isScanning:
            ctrl.stopScan()
        ctrl.onDeviceFoundCallback = None

    @pytest.fixture
    async def sensor_profile_async(self, controller):
        print('sensor_profile_async')
        try:
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
                target_device = find_device_by_mac(devices, specified_mac)
                if target_device:
                    profile = controller.requireSensor(target_device)
                    try:
                        yield profile
                    finally:
                        if profile.deviceState != DeviceStateEx.Disconnected:
                            await profile.asyncDisconnect()
                        controller.stopScan()
        except Exception as e:
                logger.error(f"Error in sensor_profile_async: {e}")

    async def test_asyncScan(self, controller):
        logger.info('\nTesting asyncScan method')
        try:
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if isinstance(devices, list):
                if devices:
                    for device in devices:
                        assert isinstance(device, BLEDevice)
        except Exception as e:
            logger.error(f"Error in test_asyncScan: {e}")
            pytest.fail("Failed to async scan.")
           

    async def test_asyncConnect(self, sensor_profile_async):
        logger.info('\nTesting asyncConnect')
        sensor_profile = await anext(sensor_profile_async)
        try:
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncConnect: {e}")
            pytest.fail("Failed to connect to the device.")
    
        
    async def test_asyncDisconnect(self, sensor_profile_async):
        logger.info('\nTesting asyncDisconnect')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            disconnect_result = await sensor_profile.asyncDisconnect()
            assert disconnect_result is True
        except Exception as e:
            logger.error(f"Error in test_asyncDisconnect: {e}")
            pytest.fail("Failed to disconnect to the device.")
    
    async def test_asyncSetParam(self, sensor_profile_async):
        logger.info('\nTesting asyncSetParam method')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            set_result = await sensor_profile.asyncSetParam("NTF_EMG", "ON")
            assert set_result == "OK"
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncSetParam: {e}")
            pytest.fail("Failed to async SetParam.")

    async def test_asyncStartDataNotification(self, sensor_profile_async):
        logger.info('\nTesting asyncStart Data Notification')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            result = await sensor_profile.asyncInit(5, 60 * 1000)
            assert result is True
            start_result = await sensor_profile.asyncStartDataNotification()
            assert start_result is True
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncStartDataNotification: {e}")
            pytest.fail("Failed to async Start DataNotification.")

    async def test_asyncStopDataNotification(self, sensor_profile_async):
        logger.info('\nTesting asyncStop Data Notification')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
           
            result = await sensor_profile.asyncInit(5, 60 * 1000)
            assert result is True
            start_result = await sensor_profile.asyncStartDataNotification()
            assert start_result is True
            stop_result = await sensor_profile.asyncStopDataNotification()
            assert stop_result is True
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncStopDataNotification: {e}")
            pytest.fail("Failed to async stop DataNotification.")
            
    async def test_get_battery_level(self,sensor_profile_async):
        """
        测试获取电池电量功能
        """
        logger.info('\nTesting getBatteryLevel method')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            result = await sensor_profile.asyncInit(5, 60 * 1000)
            assert result is True
            battery_level = await sensor_profile.asyncGetBatteryLevel()
            assert isinstance(battery_level, int)
            assert 0 <= battery_level <= 100
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncGetBatteryLevel: {e}")
            pytest.fail("Failed to async Get Battery Level.")
            
    async def test_asyncInit(self, sensor_profile_async):
        logger.info('\nTesting asyncInit method')
        try:
            sensor_profile = await anext(sensor_profile_async)
            connect_result = await sensor_profile.asyncConnect()
            assert connect_result is True
            result = await sensor_profile.asyncInit(5, 60 * 1000)
            assert result is True
            await sensor_profile.asyncDisconnect()
        except Exception as e:
            logger.error(f"Error in test_asyncInit: {e}")
            pytest.fail("Failed to async Init.")
            


