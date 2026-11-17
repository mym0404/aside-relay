"""Regression tests for completion delivery and JSONL cursor continuity."""
from tests.backend import support

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import runner
import server
import sessions


SESSION_ID = support.SESSION_ID


class FakeSocket:
    def __init__(self, release: asyncio.Event | None = None) -> None:
        self.payloads: list[dict] = []
        self.started = asyncio.Event()
        self.release = release

    async def send_text(self, value: str) -> None:
        self.started.set()
        if self.release:
            await self.release.wait()
        self.payloads.append(json.loads(value))


async def wait_for_payloads(socket: FakeSocket, count: int) -> None:
    async with asyncio.timeout(2):
        while len(socket.payloads) < count:
            await asyncio.sleep(0.001)


class CompletionRegressionTests(support.IsolatedBackendTest):
    async def test_slow_websocket_does_not_delay_completion_notifications(self):
        hub = server.Hub()
        release = asyncio.Event()
        socket = FakeSocket(release)
        hub._subs[SESSION_ID] = {socket}
        ntfy_started = asyncio.Event()
        push_started = asyncio.Event()

        async def push_ntfy(*_args):
            ntfy_started.set()

        async def push_answer(*_args):
            push_started.set()

        run = SimpleNamespace(
            session_id=SESSION_ID, running=False, stream_id="run-1",
            exit_code=0, error=None, output="", is_aborted=False,
        )
        with patch.object(server.config, "JSONL_POLL_SEC", 0), \
                patch("server.push_ntfy", new=AsyncMock(side_effect=push_ntfy)), \
                patch.object(hub, "_push_answer", new=AsyncMock(side_effect=push_answer)):
            watching = asyncio.create_task(hub.watch_run(run))
            try:
                await asyncio.wait_for(socket.started.wait(), 1)
                await asyncio.wait_for(ntfy_started.wait(), 1)
                await asyncio.wait_for(push_started.wait(), 1)
                self.assertFalse(watching.done())
            finally:
                release.set()
                await watching

    async def test_failed_abort_preserves_the_run_without_marking_or_terminating_it(self):
        for finishes_during_stop in (False, True):
            with self.subTest(finishes_during_stop=finishes_during_stop):
                process = SimpleNamespace(pid=123, terminate=Mock())
                run = runner.Run(SESSION_ID, "prompt", process, -1, "stream.log")

                async def fail_stop(_session_id):
                    if finishes_during_stop:
                        run.finished_at = time.time()
                    return False

                stop = AsyncMock(side_effect=fail_stop)
                # create=True: Windows 에는 os.getpgid/killpg 가 없다.
                # 이 테스트는 stop 이 실패해서 kill 경로 자체를 안 탄다.
                with patch.dict(runner._runs, {SESSION_ID: run}, clear=True), \
                        patch("runner.stop_session", new=stop), \
                        patch("runner.os.getpgid", create=True) as getpgid, \
                        patch("runner.os.killpg", create=True) as killpg:
                    result = await runner.abort(SESSION_ID)

                    self.assertFalse(result)
                    self.assertIs(runner.get_run(SESSION_ID), run)
                    self.assertFalse(run.is_aborted)
                    getpgid.assert_not_called()
                    killpg.assert_not_called()
                    process.terminate.assert_not_called()

    async def test_filtered_trailer_keeps_rest_and_tail_sequences_equal(self):
        directory = self.root / "session"
        directory.mkdir()
        path = directory / "messages.jsonl"
        first = self._line("assistant", "first")
        metadata = json.dumps({"role": "user-message-metadata"}).encode() + b"\n"
        second = self._line("assistant", "second")
        path.write_bytes(first + metadata)

        with patch("sessions.session_dir", return_value=directory), \
                patch.object(sessions.config, "JSONL_POLL_SEC", 0.001):
            messages, offset = sessions.read_messages(SESSION_ID)
            next_seq = messages[-1]["seq"] + 1
            self.assertEqual(offset, len(first))
            path.write_bytes(first + metadata + second)

            stream = sessions.tail_messages(SESSION_ID, offset, next_seq)
            live = await asyncio.wait_for(anext(stream), 1)
            await stream.aclose()
            reloaded, _ = sessions.read_messages(SESSION_ID)

        self.assertEqual(live["seq"], 2)
        self.assertEqual(live["seq"], reloaded[-1]["seq"])

    async def test_second_subscriber_receives_rest_to_subscribe_gap(self):
        directory = self.root / "session"
        directory.mkdir()
        path = directory / "messages.jsonl"
        first = self._line("assistant", "first")
        second = self._line("assistant", "second")
        third = self._line("assistant", "third")
        path.write_bytes(first)
        hub = server.Hub()
        first_socket = FakeSocket()
        second_socket = FakeSocket()

        with patch("sessions.session_dir", return_value=directory), \
                patch.object(sessions.config, "JSONL_POLL_SEC", 0.001):
            snapshot, offset = sessions.read_messages(SESSION_ID)
            next_seq = snapshot[-1]["seq"] + 1
            await hub.subscribe(first_socket, SESSION_ID, next_seq, offset)
            path.write_bytes(first + second)
            await wait_for_payloads(first_socket, 1)

            await hub.subscribe(second_socket, SESSION_ID, next_seq, offset)
            path.write_bytes(first + second + third)
            await wait_for_payloads(first_socket, 2)
            await wait_for_payloads(second_socket, 2)

        self.assertEqual([item["message"]["seq"] for item in second_socket.payloads], [1, 2])
        hub.unsubscribe(first_socket, SESSION_ID)
        hub.unsubscribe(second_socket, SESSION_ID)
        await asyncio.sleep(0)
        self.assertNotIn(SESSION_ID, hub._subs)
        self.assertNotIn(SESSION_ID, hub._tasks)

    @staticmethod
    def _line(role: str, content: str) -> bytes:
        return json.dumps({"role": role, "content": content}).encode() + b"\n"


if __name__ == "__main__":
    import unittest
    unittest.main()
