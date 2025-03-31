import pytest
import asyncio
import time
from typing import List
from sensor import SensorController, SensorProfile, BLEDevice, DeviceStateEx, DataType

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SCAN_DEVICE_PERIOD_IN_MS = 5000
WAIT_SCAN_RESULT = SCAN_DEVICE_PERIOD_IN_MS / 1000 + 3
specified_mac = '24:71:89:EF:2F:B7'
discovered_devices = []

@pytest.fixture(scope="module")
def controller():
    ctrl = SensorController()
    if not ctrl.isEnable:
        pytest.skip("Bluetooth is not enabled")
    yield ctrl
    if ctrl.isScanning:
        ctrl.stopScan()
    ctrl.onDeviceFoundCallback = None

@pytest.fixture(scope="module")
def device_found_callback():
    def _callback(deviceList: List[BLEDevice]):
        global discovered_devices
        filteredDevice = filter(lambda x: x.Address == specified_mac, deviceList)
        for device in filteredDevice:
            if device.Address not in [d.Address for d in discovered_devices]:
                discovered_devices.append(device)
                print(f'device.Address = {device.Address }, device.RSSI = {device.RSSI}')
        logger.info(f'{len(discovered_devices)} Bluetooth devices found in total')
    return _callback

@pytest.fixture(scope="module")
def sensor_profile(controller, device_found_callback):
    controller.onDeviceFoundCallback = device_found_callback
    controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
    time.sleep(WAIT_SCAN_RESULT)
    
    if not discovered_devices:
        pytest.skip("No devices discovered")
    
    device = discovered_devices[0]
    profile = controller.requireSensor(device)
    yield profile
    
    if profile.deviceState != DeviceStateEx.Disconnected:
        profile.disconnect()
    controller.stopScan()
    discovered_devices.clear()

def wait_for_state(profile, target_state, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if profile.deviceState == target_state:
            return True
        time.sleep(0.5)
    return False

# 同步测试部分
class TestSensorController:
    def test_start_scan(self, controller):
        logger.info('\nTesting startScan method')
        success = controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        assert success is True
        assert controller.isScanning is True

    def test_scan_once(self, controller):
        logger.info('\nTesting scan method')
        ble_devices = controller.scan(SCAN_DEVICE_PERIOD_IN_MS)
        assert isinstance(ble_devices, list)

    def test_stop_scan(self, controller):
        logger.info('\nTesting stopScan method')
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(1)
        controller.stopScan()
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
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = controller.requireSensor(device)
            assert isinstance(sensor_profile, SensorProfile) or sensor_profile is None
        else:
            pytest.skip("No devices discovered")

    def test_get_sensor(self, controller):
        logger.info('\nTesting getSensor method')
        controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        time.sleep(WAIT_SCAN_RESULT)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = controller.requireSensor(device)
            retrieved_sensor = controller.getSensor(device.Address)
            if sensor_profile:
                assert retrieved_sensor == sensor_profile
            else:
                assert retrieved_sensor is None
        else:
            pytest.skip("No devices discovered")

    def test_get_connected_sensors(self, controller):
        logger.info('\nTesting getConnectedSensors method')
        sensor_profiles = controller.getConnectedSensors()
        assert isinstance(sensor_profiles, list)

    def test_get_connected_devices(self, controller):
        logger.info('\nTesting getConnectedDevices method')
        ble_devices = controller.getConnectedDevices()
        assert isinstance(ble_devices, list)

class TestSensorProfile:
    def test_connect(self, sensor_profile):
        logger.info('\nTesting connect method')
        success = sensor_profile.connect()
        assert success is True
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_disconnect(self, sensor_profile):
        logger.info('\nTesting disconnect method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        success = sensor_profile.disconnect()
        assert success is True
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

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
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        device_info = sensor_profile.getDeviceInfo()
        if device_info:
            assert isinstance(device_info, dict)
        else:
            assert device_info is None
            
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_init_data_transfer(self, sensor_profile):
        logger.info('\nTesting init method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        success = sensor_profile.init(5, 60 * 1000)
        assert success is True
        
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_check_init_data_transfer(self, sensor_profile):
        logger.info('\nTesting hasInited property')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        sensor_profile.init(5, 60 * 1000)
        has_inited = sensor_profile.hasInited
        assert isinstance(has_inited, bool)
        
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_start_data_notification(self, sensor_profile):
        logger.info('\nTesting startDataNotification method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            success = sensor_profile.startDataNotification()
            assert success is True
            sensor_profile.stopDataNotification()
            
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_stop_data_notification(self, sensor_profile):
        logger.info('\nTesting stopDataNotification method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            sensor_profile.startDataNotification()
            success = sensor_profile.stopDataNotification()
            assert success is True
            
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_check_data_transfering(self, sensor_profile):
        logger.info('\nTesting isDataTransfering property')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        sensor_profile.init(5, 60 * 1000)
        if sensor_profile.hasInited:
            sensor_profile.startDataNotification()
            is_transfering = sensor_profile.isDataTransfering
            assert isinstance(is_transfering, bool)
            sensor_profile.stopDataNotification()
            
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_get_battery_level(self, sensor_profile):
        logger.info('\nTesting getBatteryLevel method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        battery_power = sensor_profile.getBatteryLevel()
        assert isinstance(battery_power, int)
        
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

    def test_set_param(self, sensor_profile):
        logger.info('\nTesting setParam method')
        sensor_profile.connect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Ready, 15) is True
        
        result = sensor_profile.setParam("NTF_EMG", "ON")
        assert result == "OK"
        
        sensor_profile.disconnect()
        assert wait_for_state(sensor_profile, DeviceStateEx.Disconnected, 15) is True

# 异步测试部分
@pytest.mark.asyncio
class TestSensorControllerAsyncMethods:
    async def test_asyncScan(self, controller):
        logger.info('\nTesting asyncScan method')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        assert isinstance(devices, list)
        if devices:
            for device in devices:
                assert isinstance(device, BLEDevice)
        else:
            pytest.skip("No devices discovered")

    async def test_asyncConnectDisconnect(self, controller):
        logger.info('\nTesting asyncConnect/Disconnect')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        
        connect_result = await sensor.asyncConnect()
        assert connect_result is True
        await asyncio.sleep(5)
        assert sensor.deviceState == DeviceStateEx.Ready
        
        disconnect_result = await sensor.asyncDisconnect()
        assert disconnect_result is True
        await asyncio.sleep(5)
        assert sensor.deviceState == DeviceStateEx.Disconnected

    async def test_asyncSetParam(self, controller):
        logger.info('\nTesting asyncSetParam method')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        await sensor.asyncConnect()
        await asyncio.sleep(5)
        
        try:
            set_result = await sensor.asyncSetParam("NTF_EMG", "ON")
            assert set_result == "OK"
        finally:
            await sensor.asyncDisconnect()

    async def test_asyncStartAndStopDataNotification(self, controller):
        logger.info('\nTesting asyncStart/Stop Data Notification')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        await sensor.asyncConnect()
        await asyncio.sleep(5)
        
        try:
            start_result = await sensor.asyncStartDataNotification()
            assert start_result is True
            await asyncio.sleep(5)
            assert sensor.isDataTransfering is True
            
            stop_result = await sensor.asyncStopDataNotification()
            assert stop_result is True
            await asyncio.sleep(5)
            assert sensor.isDataTransfering is False
        finally:
            await sensor.asyncDisconnect()

@pytest.mark.asyncio
class TestSensorProfileAsyncMethods:
    async def test_asyncInit(self, controller):
        logger.info('\nTesting asyncInit method')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        await sensor.asyncConnect()
        await asyncio.sleep(5)
        
        try:
            if sensor.deviceState == DeviceStateEx.Ready:
                result = await sensor.asyncInit(5, 60 * 1000)
                assert result is True
        finally:
            await sensor.asyncDisconnect()

    async def test_asyncGetBatteryLevel(self, controller):
        logger.info('\nTesting asyncGetBatteryLevel method')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        await sensor.asyncConnect()
        await asyncio.sleep(5)
        
        try:
            if sensor.deviceState == DeviceStateEx.Ready:
                battery_level = sensor.getBatteryLevel()
                assert isinstance(battery_level, int)
        finally:
            await sensor.asyncDisconnect()

    async def test_asyncGetDeviceInfo(self, controller):
        logger.info('\nTesting asyncGetDeviceInfo method')
        devices = await controller.asyncScan(SCAN_DEVICE_PERIOD_IN_MS)
        if not devices:
            pytest.skip("No devices discovered")
            
        device = devices[0]
        sensor = controller.requireSensor(device)
        await sensor.asyncConnect()
        await asyncio.sleep(5)
        
        try:
            if sensor.deviceState == DeviceStateEx.Ready:
                device_info = sensor.getDeviceInfo()
                if device_info:
                    assert isinstance(device_info, dict)
                else:
                    assert device_info is None
        finally:
            await sensor.asyncDisconnect()