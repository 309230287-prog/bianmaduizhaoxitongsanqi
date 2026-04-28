from threading import Event, Thread

from product_code_mapper.runs.state_machine import RunStateMachine, RunStatus


def test_created_to_running():
    sm = RunStateMachine()
    sm.start()
    assert sm.status == RunStatus.RUNNING


def test_running_to_paused_cycle():
    sm = RunStateMachine()
    sm.start()
    sm.request_pause()
    assert sm.status == RunStatus.PAUSING
    sm.confirm_paused()
    assert sm.status == RunStatus.PAUSED
    sm.resume()
    assert sm.status == RunStatus.RUNNING


def test_running_to_stopped():
    sm = RunStateMachine()
    sm.start()
    sm.request_stop()
    assert sm.status == RunStatus.STOPPING
    sm.confirm_stopped()
    assert sm.status == RunStatus.STOPPED


def test_only_completed_can_export():
    sm = RunStateMachine()
    assert not sm.can_export
    sm.start()
    assert not sm.can_export
    sm.mark_completed()
    assert sm.can_export


def test_stopped_cannot_export():
    sm = RunStateMachine()
    sm.start()
    sm.request_stop()
    sm.confirm_stopped()
    assert not sm.can_export
    assert sm.is_terminal


def test_paused_can_be_stopped():
    sm = RunStateMachine()
    sm.start()
    sm.request_pause()
    sm.confirm_paused()
    sm.request_stop()
    assert sm.status == RunStatus.STOPPING


def test_failed_cannot_export():
    sm = RunStateMachine()
    sm.start()
    sm.mark_failed()
    assert not sm.can_export
    assert sm.is_terminal


def test_wait_if_paused_blocks_until_resume():
    sm = RunStateMachine()
    sm.start()
    sm.request_pause()
    sm.confirm_paused()

    entered = Event()
    released = Event()

    def wait_for_resume():
        entered.set()
        sm.wait_if_paused(timeout=0.01)
        released.set()

    thread = Thread(target=wait_for_resume)
    thread.start()

    assert entered.wait(1)
    assert not released.wait(0.05)

    sm.resume()
    assert released.wait(1)
    thread.join(1)
