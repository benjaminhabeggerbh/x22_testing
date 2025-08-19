import argparse
import json
import time
import grpc
import pandas as pd

from x22_fleet.Library.StatusListener import statuslistener_pb2, statuslistener_pb2_grpc
from x22_fleet.Library.BaseLogger import BaseLogger

class StatusListenerClient:
    def __init__(self, broker_address):
        self.broker_address = broker_address
        self.df = pd.DataFrame()
        self.is_online = False
    def fetch_data(self):
        try:
            with grpc.insecure_channel(f"{self.broker_address}:50051") as channel:
                stub = statuslistener_pb2_grpc.StatusListenerStub(channel)
                response = stub.GetDataFrame(statuslistener_pb2.DataFrameRequest())
                rows = []
                for row in response.data:
                    row_dict = {key: value for key, value in row.fields.items()}
                    rows.append(row_dict)

            self.df = pd.DataFrame(rows)
            if 'index' in self.df.columns:
                self.df.set_index('index', inplace=True)

            numeric_fields_as_int = ['v', 'mA', 'soc', 'timeVal', 'sessions', 'sync', 'sent', 'total', 'rec', 'fwPending', 'updateAge']
            for field in numeric_fields_as_int:
                if field in self.df.columns:
                    self.df[field] = pd.to_numeric(self.df[field], errors='coerce').fillna(0).astype(int)

            # Ensure specific fields are treated as floats
            numeric_fields_as_float = ['progress', 'speed']
            for field in numeric_fields_as_float:
                if field in self.df.columns:
                    self.df[field] = pd.to_numeric(self.df[field], errors='coerce').fillna(0.0).astype(float)
                    
            self.is_online = True
            
        except grpc.RpcError as e:
            print(f"Failed to fetch data: {e}")
            self.is_online = False

        return self.df, self.is_online

