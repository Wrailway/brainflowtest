import pytest
import asyncio
import time
from typing import List
from sensor import SensorController, SensorProfile, BLEDevice, DeviceStateEx, DataType

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 增加扫描时间
SCAN_DEVICE_PERIOD_IN_MS = 60000
ASYNC_SCAN_DEVICE_PERIOD_IN_MS = 2000
WAIT_SCAN_RESULT = SCAN_DEVICE_PERIOD_IN_MS / 1000 + 3
specified_mac = '24:71:89:EF:2F:B7'
MAX_SCAN_RETRIES = 3

# 同步扫描设备
def scan_devices_sync(controller, max_retries=MAX_SCAN_RETRIES):
    # print(f'\nscan_devices_sync,controller = {controller}\n')
    discovered_devices = []

    def device_found_callback(deviceList: List[BLEDevice]):
        nonlocal discovered_devices
        try:
            filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
            # filteredDevice = filter(lambda x: x.Address == specified_mac, deviceList)
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

# 异步扫描设备
async def scan_devices_async(controller, max_retries=MAX_SCAN_RETRIES):
    # print(f'\nscan_devices_async,controller = {controller}\n')
    discovered_devices = []

    def device_found_callback(deviceList: List[BLEDevice]):
        nonlocal discovered_devices
        try:
            filteredDevice = filter(lambda x: x.Name.startswith('OB') or x.Name.startswith('Sync'), deviceList)
            for device in filteredDevice:
                if device.Address not in [d.Address for d in discovered_devices]:
                    discovered_devices.append(device)
                    logger.info(f'device.Address = {device.Address }, device.RSSI = {device.RSSI}')
            logger.info(f'{len(discovered_devices)} Bluetooth devices found in total')
        except Exception as e:
            logger.error(f"Error in device_found_callback: {e}")

    for retry in range(max_retries):
        controller.onDeviceFoundCallback = device_found_callback
        # 假设这里的 startScan 是同步方法，需要在异步环境中处理
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, controller.startScan, SCAN_DEVICE_PERIOD_IN_MS)
        logger.info(f"Waiting for {WAIT_SCAN_RESULT} seconds to discover devices... (Retry {retry + 1})")
        await asyncio.sleep(WAIT_SCAN_RESULT)

        if discovered_devices:
            break

    return discovered_devices

def wait_for_state(profile, target_state, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if profile.deviceState == target_state:
            return True
        time.sleep(0.5)
    return False

# 同步测试部分
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

    @pytest.fixture(scope="class")
    def sensor_profile_sync(self, controller):
        discovered_devices = scan_devices_sync(controller)

        if not discovered_devices:
            pytest.skip("No devices discovered after multiple retries")

        device = discovered_devices[0]
        profile = controller.requireSensor(device)
        yield profile

        if profile.deviceState != DeviceStateEx.Disconnected:
            profile.disconnect()
        controller.stopScan()

    def test_start_scan(self, controller):
        logger.info('\nTesting startScan method')
        success = controller.startScan(SCAN_DEVICE_PERIOD_IN_MS)
        assert success is True
        assert controller.isScanning is True

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
        discovered_devices = scan_devices_sync(controller)
        if discovered_devices:
            device = discovered_devices[0]
            sensor_profile = controller.requireSensor(device)
            assert isinstance(sensor_profile, SensorProfile) or sensor_profile is None
        else:
            pytest.skip("No devices discovered after multiple retries")

    def test_get_sensor(self, controller):
        logger.info('\nTesting getSensor method')
        discovered_devices = scan_devices_sync(controller)
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

class TestSensorProfile:
    @pytest.fixture(scope="class")
    def controller(self):
        ctrl = SensorController()
        if not ctrl.isEnable:
            pytest.skip("Bluetooth is not enabled")
        yield ctrl
        if ctrl.isScanning:
            ctrl.stopScan()
        ctrl.onDeviceFoundCallback = None

    @pytest.fixture(scope="class")
    def sensor_profile_sync(self, controller):
        discovered_devices = scan_devices_sync(controller)

        if not discovered_devices:
            pytest.skip("No devices discovered after multiple retries")

        device = discovered_devices[0]
        profile = controller.requireSensor(device)
        yield profile

        if profile.deviceState != DeviceStateEx.Disconnected:
            profile.disconnect()
        controller.stopScan()

    def test_connect(self, sensor_profile_sync):
        logger.info('\nTesting connect method')
        success = sensor_profile_sync.connect()
        assert success is True
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_disconnect(self, sensor_profile_sync):
        logger.info('\nTesting disconnect method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        success = sensor_profile_sync.disconnect()
        assert success is True
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_get_device_status(self, sensor_profile_sync):
        logger.info('\nTesting deviceState property')
        device_state = sensor_profile_sync.deviceState
        assert isinstance(device_state, DeviceStateEx)

    def test_get_ble_device(self, sensor_profile_sync):
        logger.info('\nTesting BLEDevice property')
        ble_device = sensor_profile_sync.BLEDevice
        assert isinstance(ble_device, BLEDevice)

    def test_get_device_info(self, sensor_profile_sync):
        logger.info('\nTesting getDeviceInfo method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        device_info = sensor_profile_sync.getDeviceInfo()
        if device_info:
            assert isinstance(device_info, dict)
        else:
            assert device_info is None

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_init_data_transfer(self, sensor_profile_sync):
        logger.info('\nTesting init method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        success = sensor_profile_sync.init(5, 60 * 1000)
        assert success is True

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_check_init_data_transfer(self, sensor_profile_sync):
        logger.info('\nTesting hasInited property')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        sensor_profile_sync.init(5, 60 * 1000)
        has_inited = sensor_profile_sync.hasInited
        assert isinstance(has_inited, bool)

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_start_data_notification(self, sensor_profile_sync):
        logger.info('\nTesting startDataNotification method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        sensor_profile_sync.init(5, 60 * 1000)
        if sensor_profile_sync.hasInited:
            success = sensor_profile_sync.startDataNotification()
            assert success is True
            sensor_profile_sync.stopDataNotification()

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_stop_data_notification(self, sensor_profile_sync):
        logger.info('\nTesting stopDataNotification method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        sensor_profile_sync.init(5, 60 * 1000)
        if sensor_profile_sync.hasInited:
            sensor_profile_sync.startDataNotification()
            success = sensor_profile_sync.stopDataNotification()
            assert success is True

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_check_data_transfering(self, sensor_profile_sync):
        logger.info('\nTesting isDataTransfering property')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        sensor_profile_sync.init(5, 60 * 1000)
        if sensor_profile_sync.hasInited:
            sensor_profile_sync.startDataNotification()
            is_transfering = sensor_profile_sync.isDataTransfering
            assert isinstance(is_transfering, bool)
            sensor_profile_sync.stopDataNotification()

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_get_battery_level(self, sensor_profile_sync):
        logger.info('\nTesting getBatteryLevel method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        battery_power = sensor_profile_sync.getBatteryLevel()
        assert isinstance(battery_power, int)

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

    def test_set_param(self, sensor_profile_sync):
        logger.info('\nTesting setParam method')
        sensor_profile_sync.connect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Ready, 15) is True

        result = sensor_profile_sync.setParam("NTF_EMG", "ON")
        assert result == "OK"

        sensor_profile_sync.disconnect()
        assert wait_for_state(sensor_profile_sync, DeviceStateEx.Disconnected, 15) is True

# 异步测试部分
@pytest.mark.asyncio
class TestSensorControllerAsyncMethods:
    @pytest.fixture(scope="class")
    def controller(self):
        ctrl = SensorController()
        if not ctrl.isEnable:
            pytest.skip("Bluetooth is not enabled")
        # print(f'TestSensorControllerAsyncMethods,controller ={ctrl}')
        yield ctrl
        if ctrl.isScanning:
            ctrl.stopScan()
        ctrl.onDeviceFoundCallback = None

    @pytest.fixture(scope="class")
    async def sensor_profile_async(self, controller):
        discovered_devices = await scan_devices_async(controller)

        if not discovered_devices:
            pytest.skip("No devices discovered after multiple retries")

        device = discovered_devices[0]
        profile = controller.requireSensor(device)
        yield profile

        if profile.deviceState != DeviceStateEx.Disconnected:
            profile.disconnect()
        controller.stopScan()

    async def test_scan_once(self, controller):
        logger.info('\nTesting scan method')
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                loop = asyncio.get_running_loop()
                ble_devices = await loop.run_in_executor(None, controller.scan, 1000)
                if ble_devices is not None:
                    assert isinstance(ble_devices, list)
                    return
                logger.warning(f"Scan attempt {retries + 1} failed. Retrying...")
            except Exception as e:
                logger.error(f"Error in test_scan_once (attempt {retries + 1}): {e}")
            retries += 1
        pytest.fail("Failed to scan devices after multiple attempts.")

    async def test_asyncScan(self, controller):
        logger.info('\nTesting asyncScan method')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if isinstance(devices, list):
                if devices:
                    for device in devices:
                        assert isinstance(device, BLEDevice)
                    break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

    async def test_asyncConnectDisconnect(self, controller):
        logger.info('\nTesting asyncConnect/Disconnect')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
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
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

    async def test_asyncSetParam(self, controller):
        logger.info('\nTesting asyncSetParam method')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
                device = devices[0]
                sensor = controller.requireSensor(device)
                await sensor.asyncConnect()
                await asyncio.sleep(5)

                try:
                    set_result = await sensor.asyncSetParam("NTF_EMG", "ON")
                    assert set_result == "OK"
                finally:
                    await sensor.asyncDisconnect()
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

    async def test_asyncStartAndStopDataNotification(self, controller):
        logger.info('\nTesting asyncStart/Stop Data Notification')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
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
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

@pytest.mark.asyncio
class TestSensorProfileAsyncMethods:
    @pytest.fixture(scope="class")
    def controller(self):
        ctrl = SensorController()
        if not ctrl.isEnable:
            pytest.skip("Bluetooth is not enabled")
        yield ctrl
        if ctrl.isScanning:
            ctrl.stopScan()
        ctrl.onDeviceFoundCallback = None

    @pytest.fixture(scope="class")
    async def sensor_profile_async(self, controller):
        discovered_devices = await scan_devices_async(controller)

        if not discovered_devices:
            pytest.skip("No devices discovered after multiple retries")

        device = discovered_devices[0]
        profile = controller.requireSensor(device)
        yield profile

        if profile.deviceState != DeviceStateEx.Disconnected:
            profile.disconnect()
        controller.stopScan()

    async def test_asyncInit(self, controller):
        logger.info('\nTesting asyncInit method')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
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
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

    async def test_asyncGetBatteryLevel(self, controller):
        logger.info('\nTesting asyncGetBatteryLevel method')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
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
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")

    async def test_asyncGetDeviceInfo(self, controller):
        logger.info('\nTesting asyncGetDeviceInfo method')
        for retry in range(MAX_SCAN_RETRIES):
            devices = await controller.asyncScan(ASYNC_SCAN_DEVICE_PERIOD_IN_MS)
            if devices:
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
                break
            if retry == MAX_SCAN_RETRIES - 1:
                pytest.skip("No devices discovered after multiple retries")
    