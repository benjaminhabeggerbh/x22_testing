from concurrent import futures
import pandas as pd
import grpc
from x22_fleet.Library.StatusListener import statuslistener_pb2_grpc
from x22_fleet.Library.StatusListener import statuslistener_pb2
import logging

class GrpcServer:
    def __init__(self, sensor_state_manager, host="[::]", port=50051):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self.sensor_state_manager = sensor_state_manager
        self.host = host
        self.port = port

        # Add the gRPC service to the server
        statuslistener_pb2_grpc.add_StatusListenerServicer_to_server(
            StatusListenerServicer(sensor_state_manager), self.server
        )

    def start(self):
        self.server.add_insecure_port(f"{self.host}:{self.port}")
        self.server.start()
        logging.info(f"gRPC server started on {self.host}:{self.port}")

    def wait_for_termination(self):
        try:
            self.server.wait_for_termination()
        except KeyboardInterrupt:
            logging.info("Shutting down gRPC server...")
            self.server.stop(0)


class StatusListenerServicer(statuslistener_pb2_grpc.StatusListenerServicer):
    def __init__(self, sensor_state_manager):
        self.sensor_state_manager = sensor_state_manager

    def GetDataFrame(self, request, context):
        try:
            # Get the DataFrame from the sensor state manager
            df = self.sensor_state_manager.get_dataframe()

            # Convert DataFrame to gRPC response
            data_rows = [
                statuslistener_pb2.DataRow(fields={
                    **{"index": str(index)},
                    **{str(k): str(v) for k, v in row.items() if pd.notna(v)}
                }) for index, row in df.iterrows()
            ]

            return statuslistener_pb2.DataFrameResponse(data=data_rows)
        except Exception as e:
            context.set_details(f"Failed to retrieve data: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return statuslistener_pb2.DataFrameResponse(data=[])
