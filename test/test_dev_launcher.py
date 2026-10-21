"""Launcher regression tests without Docker, app config, models or child servers."""
import subprocess
import unittest
from unittest.mock import Mock, patch
from app.script import run_dev


class DevLauncherTest(unittest.TestCase):
    def test_plan_includes_both_transports_and_loopback(self):
        cmds = run_dev.commands("python", 8010)
        self.assertEqual(cmds[0], ["python", "-m", "app.grpc_server"])
        self.assertIn("127.0.0.1", cmds[1])

    @patch.object(run_dev.subprocess, "Popen")
    def test_dry_run_never_starts_children(self, popen):
        self.assertEqual(run_dev.supervise(["--dry-run"]), 0)
        popen.assert_not_called()

    @patch.object(run_dev.socket, "socket")
    @patch.object(run_dev.subprocess, "Popen")
    def test_busy_port_never_kills_or_starts_other_process(self, popen, socket):
        socket.return_value.__enter__.return_value.bind.side_effect = OSError("busy")
        self.assertEqual(run_dev.supervise([]), 1)
        popen.assert_not_called()

    def test_exit_before_readiness_is_failure(self):
        with self.assertRaisesRegex(RuntimeError, "exited"):
            run_dev.wait_ready([Mock(poll=lambda:1)], 8010, 50100, 1)

    def test_cleanup_kills_only_owned_child_that_does_not_exit(self):
        live = Mock(); live.poll.return_value = None
        live.wait.side_effect = [subprocess.TimeoutExpired("owned",5),0]
        dead = Mock(); dead.poll.return_value = 1
        run_dev.stop_children([live,dead])
        live.terminate.assert_called_once();live.kill.assert_called_once()
        dead.terminate.assert_not_called()

    @patch.object(run_dev.socket, "socket")
    @patch.object(run_dev, "wait_ready", side_effect=RuntimeError("not ready"))
    @patch.object(run_dev.subprocess, "Popen")
    def test_failure_stops_both_owned_children(self, popen, ready, socket):
        children=[Mock(),Mock()]
        for child in children:child.poll.return_value=None
        popen.side_effect=children
        self.assertEqual(run_dev.supervise([]),1)
        for child in children:child.terminate.assert_called_once()
        for call in popen.call_args_list:
            self.assertEqual(call.kwargs["env"]["AI_GRPC_BIND_HOST"],"127.0.0.1")
        self.assertEqual(len(popen.call_args_list),2)


if __name__ == "__main__":unittest.main()
