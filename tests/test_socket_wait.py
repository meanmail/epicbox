import unittest
from unittest.mock import MagicMock, patch

from epicbox import utils


class SocketWaitTests(unittest.TestCase):
    def test_closed_stdin_waits_for_output_without_sleeping(self):
        sock = MagicMock()
        client = MagicMock()
        client.api.attach_socket.return_value = sock

        with patch.object(utils, 'get_docker_client', return_value=client), \
                patch.object(utils.select, 'select', side_effect=[
                    ([], [], []), ([sock], [], [])]) as wait, \
                patch.object(utils, '_socket_read', return_value=None), \
                patch.object(utils.time, 'sleep') as sleep:
            self.assertEqual(utils.docker_communicate(MagicMock()), (b'', b''))
        for call in wait.call_args_list:
            self.assertEqual(call[0][0], [sock])
            self.assertEqual(call[0][1], [])
        self.assertFalse(sleep.called)

    def test_write_interest_ends_when_input_is_sent(self):
        sock = MagicMock()
        client = MagicMock()
        client.api.attach_socket.return_value = sock
        with patch.object(utils, 'get_docker_client', return_value=client), \
                patch.object(utils.select, 'select', side_effect=[
                    ([], [sock], []), ([], [sock], []), ([sock], [], [])]) as wait, \
                patch.object(utils, '_socket_write', side_effect=[1, 1]), \
                patch.object(utils, '_socket_read', return_value=None):
            utils.docker_communicate(MagicMock(), stdin=b'ab')
        self.assertEqual([call[0][1] for call in wait.call_args_list],
                         [[sock], [sock], []])
        sock._sock.shutdown.assert_called_once_with(utils.socket.SHUT_WR)

    def test_select_wait_is_bounded_by_remaining_timeout(self):
        sock = MagicMock()
        client = MagicMock()
        client.api.attach_socket.return_value = sock
        with patch.object(utils, 'get_docker_client', return_value=client), \
                patch.object(utils.time, 'monotonic',
                             side_effect=[0, 0.75, 1]), \
                patch.object(utils.select, 'select',
                             return_value=([], [], [])) as wait, \
                patch.object(utils.time, 'sleep') as sleep:
            with self.assertRaises(TimeoutError):
                utils.docker_communicate(MagicMock(), timeout=1)
        self.assertEqual(wait.call_args[0][3], 0.25)
        self.assertFalse(sleep.called)
        sock.close.assert_called_once_with()
