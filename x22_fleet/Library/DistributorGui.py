from dash import Dash, dash_table, html, dcc
from dash.dependencies import Input, Output
import threading
from x22_fleet.Library.BaseLogger import BaseLogger

class DistributorGui:
    def __init__(self, distributors, port, logToConsole):
        self.distributors = distributors
        self.logger = BaseLogger(log_file_path=f"DistributorGui.log", log_to_console=logToConsole).get_logger()
        self.port = port
        self.app = Dash(__name__)
        self.setup_layout()

    def setup_layout(self):
        tabs = []
        for distributor in self.distributors:
            tabs.append(dcc.Tab(label=distributor.station_name, children=[
                dash_table.DataTable(
                    id=f'{distributor.station_name}-sensor-status-table',
                    columns=[
                        {"name": "Name", "id": "name"},
                        {"name": "State", "id": "state"},
                        {"name": "Progress", "id": "progress"},
                        {"name": "Speed", "id": "speed"}
                    ],
                    data=[],  # Initially empty
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'center',
                        'padding': '8px',
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6'
                    },
                    style_header={
                        'backgroundColor': '#343a40',
                        'color': 'white',
                        'fontWeight': 'bold'
                    }
                )
            ]))

        self.app.layout = html.Div([
            html.H1("Distributor Sensor Status", style={
                'textAlign': 'center',
                'backgroundColor': '#343a40',
                'color': 'white',
                'padding': '10px'
            }),
            dcc.Tabs(id='tabs', children=tabs),
            dcc.Interval(
                id='interval-component',
                interval=3000,  # in milliseconds
                n_intervals=0
            )
        ])

        for distributor in self.distributors:
            self.create_callbacks(distributor)

    def create_callbacks(self, distributor):
        @self.app.callback(
            [Output(f'{distributor.station_name}-sensor-status-table', 'data')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_table(n):
            try:
                sensors = distributor.get_sensors()  # Returns a list
                enriched_sensors = [
                    {**sensor, "progress": sensor.get("progress", 0), "speed": sensor.get("speed", 0)}
                    for sensor in sensors
                ]
                self.logger.info(f"Updated sensors for table {distributor.station_name}: {enriched_sensors}")
                return [enriched_sensors]
            except Exception as e:
                self.logger.error(f"Error updating table for {distributor.station_name}: {e}")
                return [[]]  # Return empty data on error

    def run(self):
        threading.Thread(target=self.app.run_server, kwargs={"debug": True, "use_reloader": False, "port": self.port, "host": "0.0.0.0"}, daemon=True).start()
