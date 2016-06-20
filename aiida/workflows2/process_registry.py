
import plum.persistence.pickle_persistence
import plum.process_registry
import plum.process
import aiida.common.exceptions as exceptions
from aiida.common.lang import override
from aiida.workflows2.util import ProcessStack


class ProcessRegistry(plum.process_registry.ProcessRegistry,
                      plum.process.ProcessListener):
    def __init__(self, persistence_engine=None):
        self._running_processes = {}
        self._finished = {}
        self._persistence_engine = persistence_engine

    @property
    def current_pid(self):
        return ProcessStack.top().pid

    @property
    def current_calc_node(self):
        return ProcessStack.top().calc

    def get_running_pids(self):
        return self._running_processes.viewkeys()

    @override
    def register_running_process(self, process):
        self._running_processes[process.pid] = process
        process.add_process_listener(self)
        if self._persistence_engine:
            self._persistence_engine.persist_process(process)

    @override
    def get_running_process(self, pid):
        return self._running_processes[pid]

    @override
    def is_finished(self, pid):
        import aiida.orm

        # Is it finished?
        if pid in self._finished:
            return True

        # Is it running?
        if pid in self._running_processes:
            return False

        try:
            return aiida.orm.load_node(pid).is_finished()
        except exceptions.NotExistent:
            pass

        raise ValueError("Could not find a Process with id '{}'".format(pid))

    @override
    def get_output(self, pid, port):
        return self.get_outputs()[port]

    @override
    def get_outputs(self, pid):
        import aiida.orm

        if pid in self._finished:
            return self._finished[pid]
        else:
            try:
                aiida.orm.load_node(pid).get_outputs_dict()
            except exceptions.NotExistent:
                pass
        raise ValueError("Could not find a Process with id '{}'".format(pid))

    # Process messages
    @override
    def on_process_finish(self, process, retval):
        process.remove_process_listener(self)
        del self._running_processes[process.pid]
        self._finished[process.pid] = process.get_last_outputs()

    def load_all_checkpoints(self):
        if self._persistence_engine:
            return self._persistence_engine.load_all_checkpoints()
        return []

