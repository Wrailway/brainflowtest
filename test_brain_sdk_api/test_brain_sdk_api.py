import pytest
import brainflow
import time
import numpy as np
import logging

# 假设 logger 已经正确配置
logger = logging.getLogger(__name__)


class TestSDKApi:
    @pytest.fixture(autouse=True)
    def init_paras(self):
        # 初始化参数
        self.board_id = 57
        self.board_id2 = 58
        self.mac_address = 'C4:64:E3:D8:E6:D2'
        self.mac_address2 = 'C4:64:E3:D8:E3:EE'
        self.timeout = 10
        # 以下为测试常数定义部分
        self.CHANNEL_NUM = 2  # 不同产品的通道数目有区分，这里假设真实值是7
        self.CHANNEL_NUM2 = 7
        self.SAMPLING_RATE = 250  # 根据产品定义的实际采样率，假设真实值是250
        self.SAMPLING_RATE2 = 250
        yield

    @pytest.fixture(autouse=True)
    def setup_teardown_session(self):
        # 初始化操作
        logger.info('setUp')
        self.board_shim = self.init_board_shim(self.board_id, self.mac_address)
        if self.is_skip_concurrent():
            self.board_shim2 = self.init_board_shim(self.board_id2, self.mac_address2)
        yield
        # 销毁操作
        logger.info('tearDown')
        self.board_shim = None
        if self.is_skip_concurrent():
            self.board_shim2 = None

    @classmethod
    def is_skip_concurrent(cls):
        return True

    def init_board_shim(self, board_id, mac_address):
        """
        初始化BoardShim对象的公共方法
        """
        params = brainflow.BrainFlowInputParams()
        params.mac_address = mac_address
        params.timeout = self.timeout
        return brainflow.BoardShim(board_id, params)

    def test_prepare_session(self):
        logger.info('test_prepare_session')
        try:
            self.board_shim.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            assert len(eeg_channels) >= self.CHANNEL_NUM
            assert self.board_shim.is_prepared()
            logger.info("test_prepare_session: 会话准备成功，脑电通道数量及其他验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_prepare_session", e)
        except Exception as e:
            self.handle_general_exception("test_prepare_session", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_start_stream(self):
        logger.info('test_start_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            data = self.board_shim.get_board_data()
            assert len(data) == self.board_shim.get_num_rows(board_id=self.board_id)
            logger.info("test_start_stream: 流启动成功，数据验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_start_stream", e)
        except Exception as e:
            self.handle_general_exception("test_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

    def test_get_sampling_rate(self):
        logger.info('test_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            assert sampling_rate == self.SAMPLING_RATE
            logger.info(f"test_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_get_sampling_rate", e)
        except Exception as e:
            self.handle_general_exception("test_get_sampling_rate", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_get_board_data(self):
        logger.info('test_get_board_data')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            time.sleep(1)
            data = self.board_shim.get_board_data()
            assert len(data) == self.board_shim.get_num_rows(board_id=self.board_id)
            logger.info("test_get_board_data: 获取板卡数据成功")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_get_board_data", e)
        except Exception as e:
            self.handle_general_exception("test_get_board_data", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

    def test_stop_stream(self):
        logger.info('test_stop_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            data = self.board_shim.get_board_data()
            assert len(data) != self.board_shim.get_num_rows(board_id=self.board_id)
            logger.info("test_stop_stream: 流停止成功，资源释放验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_stop_stream", e)
        except Exception as e:
            self.handle_general_exception("test_stop_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_release_session(self):
        logger.info('test_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            assert not self.board_shim.is_prepared()
            logger.info("test_release_session: 会话释放成功")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_release_session", e)
        except Exception as e:
            self.handle_general_exception("test_release_session", e)

    def test_invalid_mac_address(self):
        logger.info('test_invalid_mac_address')
        invalid_mac = "invalid_mac_address"
        try:
            params = brainflow.BrainFlowInputParams()
            params.mac_address = invalid_mac
            params.timeout = self.timeout
            board_shim = brainflow.BoardShim(self.board_id, params)
            board_shim.prepare_session()
            pytest.fail("使用无效MAC地址时应抛出异常，但未抛出")
        except brainflow.BrainFlowError as e:
            assert e.exit_code == brainflow.BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR
            logger.info("test_invalid_mac_address: 无效MAC地址异常验证通过")
        except Exception as e:
            self.handle_general_exception("test_invalid_mac_address", e)

    def test_timeout_scenario(self):
        logger.info('test_timeout_scenario')
        params = brainflow.BrainFlowInputParams()
        params.timeout = 1  # 设置一个很短的超时时间，容易触发超时情况
        params.mac_address = self.mac_address
        board_shim = brainflow.BoardShim(self.board_id, params)
        try:
            board_shim.prepare_session()
            pytest.fail("应出现超时异常，但未出现")
        except brainflow.BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.BOARD_NOT_READY_ERROR:
                logger.info("test_timeout_scenario: 超时异常验证通过")
            else:
                self.handle_brainflow_error("test_timeout_scenario", e)
        except Exception as e:
            self.handle_general_exception("test_timeout_scenario", e)
        finally:
            pass

    def test_data_format_verification(self):
        logger.info('test_data_format_verification')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            data = self.board_shim.get_board_data()
            # 假设数据应该是二维数组，进行格式验证
            assert len(data.shape) == 2
            # 假设数据类型应该是float32，进行数据类型验证（根据实际情况调整）
            assert data.dtype == np.float64
            logger.info("test_data_format_verification: 数据格式验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_data_format_verification", e)
        except Exception as e:
            self.handle_general_exception("test_data_format_verification", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()

    def test_get_data_without_start_stream(self):
        logger.info('test_get_data_without_start_stream')
        try:
            self.board_shim.prepare_session()
            data = self.board_shim.get_board_data()
            pytest.fail('stream is not started or no preset, cannot get data')
        except brainflow.BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.INVALID_ARGUMENTS_ERROR:
                logger.info('test_get_data_without_start_stream: 未开启流，无法获取数据验证通过')
            else:
                self.handle_brainflow_error("test_get_data_without_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    def test_operation_order_change(self):
        logger.info('test_operation_order_change')
        try:
            self.board_shim.start_stream()
            self.board_shim.prepare_session()
        except brainflow.BrainFlowError as e:
            if e.exit_code == brainflow.BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR:
                logger.info("test_operation_order_change: 并发操作顺序变化验证通过")
            else:
                self.handle_brainflow_error("test_operation_order_change", e)
        except Exception as e:
            self.handle_general_exception("test_operation_order_change", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()

    @pytest.mark.skipif(lambda: TestSDKApi.is_skip_concurrent(), reason='just skip concurrent')
    def test_concurrent_prepare_session(self):
        logger.info('test_concurrent_prepare_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim2.prepare_session()
            eeg_channels = self.board_shim.get_eeg_channels(self.board_id)
            assert len(eeg_channels) >= self.CHANNEL_NUM
            assert self.board_shim.is_prepared()
            eeg_channels2 = self.board_shim2.get_eeg_channels(self.board_id2)
            assert len(eeg_channels2) >= self.CHANNEL_NUM2
            assert self.board_shim2.is_prepared()
            logger.info("test_concurrent_prepare_session: 会话准备成功，脑电通道数量及其他验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_prepare_session", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_prepare_session", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()

    @pytest.mark.skipif(lambda: TestSDKApi.is_skip_concurrent(), reason='just skip concurrent')
    def test_concurrent_release_session(self):
        logger.info('test_concurrent_release_session')
        try:
            self.board_shim.prepare_session()
            self.board_shim.release_session()
            self.board_shim2.prepare_session()
            self.board_shim2.release_session()
            assert not self.board_shim.is_prepared()
            assert not self.board_shim2.is_prepared()
            logger.info("test_concurrent_release_session: 会话释放成功")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_release_session", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_release_session", e)

    @pytest.mark.skipif(lambda: TestSDKApi.is_skip_concurrent(), reason='just skip concurrent')
    def test_concurrent_start_stream(self):
        logger.info('test_concurrent_start_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim2.prepare_session()
            self.board_shim2.start_stream()
            data = self.board_shim.get_board_data()
            assert len(data) == self.board_shim.get_num_rows(board_id=self.board_id)
            data2 = self.board_shim2.get_board_data()
            assert len(data2) == self.board_shim2.get_num_rows(board_id=self.board_id2)
            logger.info("test_concurrent_start_stream: 流启动成功，数据验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_start_stream", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_start_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.stop_stream()
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.stop_stream()
                self.board_shim2.release_session()

    @pytest.mark.skipif(lambda: TestSDKApi.is_skip_concurrent(), reason='just skip concurrent')
    def test_concurrent_stop_stream(self):
        logger.info('test_concurrent_stop_stream')
        try:
            self.board_shim.prepare_session()
            self.board_shim.start_stream()
            self.board_shim.stop_stream()
            self.board_shim2.prepare_session()
            self.board_shim2.start_stream()
            self.board_shim2.stop_stream()
            data = self.board_shim.get_board_data()
            assert len(data) != self.board_shim.get_num_rows(board_id=self.board_id)
            data2 = self.board_shim2.get_board_data()
            assert len(data2) != self.board_shim2.get_num_rows(board_id=self.board_id2)
            logger.info("test_concurrent_stop_stream: 流停止成功，资源释放验证通过")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_stop_stream", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_stop_stream", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()

    @pytest.mark.skipif(lambda: TestSDKApi.is_skip_concurrent(), reason='just skip concurrent')
    def test_concurrent_get_sampling_rate(self):
        logger.info('test_concurrent_get_sampling_rate')
        try:
            self.board_shim.prepare_session()
            sampling_rate = self.board_shim.get_sampling_rate(board_id=self.board_id)
            assert sampling_rate == self.SAMPLING_RATE
            self.board_shim2.prepare_session()
            sampling_rate2 = self.board_shim2.get_sampling_rate(board_id=self.board_id2)
            assert sampling_rate2 == self.SAMPLING_RATE2
            logger.info(f"test_concurrent_get_sampling_rate: 获取采样率成功，采样率为 {sampling_rate}")
        except brainflow.BrainFlowError as e:
            self.handle_brainflow_error("test_concurrent_get_sampling_rate", e)
        except Exception as e:
            self.handle_general_exception("test_concurrent_get_sampling_rate", e)
        finally:
            if self.board_shim.is_prepared():
                self.board_shim.release_session()
            if self.board_shim2.is_prepared():
                self.board_shim2.release_session()

    def handle_brainflow_error(self, test_method_name, error):
        """
        处理BrainFlowError异常的公共方法，可根据需要进一步细化错误处理逻辑
        """
        logger.error(f"{test_method_name}: 脑flow业务异常,信息: {error}")
        pytest.fail(f"在{test_method_name}中出现脑flow业务异常: {error}")

    def handle_general_exception(self, test_method_name, error):
        """
        处理其他通用异常的公共方法，可根据需要进一步细化错误处理逻辑
        """
        logger.error(f"{test_method_name}: 其他运行时异常，信息: {error}")
        pytest.fail(f"在{test_method_name}中出现其他运行时异常: {error}")