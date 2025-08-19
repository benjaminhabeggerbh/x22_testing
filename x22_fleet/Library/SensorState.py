from enum import Enum, auto
import time
import graphviz

class SensorState(Enum):
    IDLE = auto()
    READY_TO_SYNC = auto()
    SYNC_ORDERED = auto()
    SYNCING = auto()
    STUCK = auto()
    OFFLINE = auto()

class SensorStateMachine:
    def __init__(self, sensor_name, logger):
        self.sensor_name = sensor_name
        self.state = SensorState.IDLE
        self.logger = logger

    def transition(self, event):
        """
        Handle state transitions based on the given event.

        Args:
            event (str): The event triggering the transition.

        Returns:
            None
        """
        previous_state = self.state

        if self.state == SensorState.IDLE:
            if event == "update_ready":
                self.state = SensorState.READY_TO_SYNC
                self.logger.info(f"{self.sensor_name}: Transitioned to READY_TO_SYNC")

        elif self.state == SensorState.READY_TO_SYNC:
            if event == "sync_command_issued":
                self.state = SensorState.SYNC_ORDERED
                self.logger.info(f"{self.sensor_name}: Transitioned to SYNC_ORDERED")
            elif event == "no_longer_ready":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensor_name}: Transitioned to IDLE")

        elif self.state == SensorState.SYNC_ORDERED:
            if event == "sync_started":
                self.state = SensorState.SYNCING
                self.logger.info(f"{self.sensor_name}: Transitioned to SYNCING")

        elif self.state == SensorState.SYNCING:
            if event == "sync_completed":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensor_name}: Transitioned to IDLE")
            elif event == "sync_failed":
                self.state = SensorState.READY_TO_SYNC
                self.logger.info(f"{self.sensor_name}: Transitioned to READY_TO_SYNC")

        if event == "offline":
            self.state = SensorState.OFFLINE
            self.logger.info(f"{self.sensor_name}: Transitioned to OFFLINE")

        elif event == "stuck":
            self.state = SensorState.STUCK
            self.logger.warning(f"{self.sensor_name}: Transitioned to STUCK")

        elif event == "online" and self.state == SensorState.OFFLINE:
            self.state = SensorState.IDLE
            self.logger.info(f"{self.sensor_name}: Transitioned to IDLE (from OFFLINE)")

        if self.state != previous_state:
            self.logger.debug(f"{self.sensor_name}: State changed from {previous_state.name} to {self.state.name}")

    def get_state(self):
        """
        Returns the current state of the sensor.

        Returns:
            SensorState: The current state of the sensor.
        """
        return self.state

    def visualize_state(self):
        """
        Visualizes the current state as a diagram using graphviz.

        Returns:
            graphviz.Digraph: The state machine diagram with the current state highlighted.
        """
        dot = graphviz.Digraph(format='png')
        dot.attr(rankdir='LR')

        # Add nodes
        for state in SensorState:
            if state == self.state:
                dot.node(state.name, shape='doublecircle', style='filled', color='lightblue')
            else:
                dot.node(state.name, shape='circle')

        # Add edges
        dot.edge("IDLE", "READY_TO_SYNC", label="update_ready")
        dot.edge("READY_TO_SYNC", "SYNC_ORDERED", label="sync_command_issued")
        dot.edge("SYNC_ORDERED", "SYNCING", label="sync_started")
        dot.edge("SYNCING", "IDLE", label="sync_completed")
        dot.edge("SYNCING", "READY_TO_SYNC", label="sync_failed")
        dot.edge("READY_TO_SYNC", "IDLE", label="no_longer_ready")
        dot.edge("*", "OFFLINE", label="offline")
        dot.edge("OFFLINE", "IDLE", label="online")
        dot.edge("SYNCING", "STUCK", label="stuck")

        return dot

# Unit test to cycle through states and visualize
def unit_test():
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SensorStateMachineTest")

    sensor_sm = SensorStateMachine("TestSensor", logger)

    # Define a sequence of events
    events = ["update_ready", "sync_command_issued", "sync_started", "sync_completed", "offline", "online", "stuck", "online"]

    for event in events:
        sensor_sm.transition(event)
        dot = sensor_sm.visualize_state()
        dot.render(f"sensor_state_{sensor_sm.get_state().name}", cleanup=True)
        print(f"Current state: {sensor_sm.get_state().name}")
        time.sleep(1)

if __name__ == "__main__":
    unit_test()
