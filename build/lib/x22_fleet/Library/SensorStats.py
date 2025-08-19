class SensorStats:
    def __init__(self, status_listener,StationName):
        self.status_listener = status_listener
        self.StationName = StationName

    def getFilteredDF(self):
        df = self.status_listener.get_dataframe()
        df = df[df["AP"] ==  self.StationName]
        return df
        
    def count_sensors(self):
        return len(self.getFilteredDF())

    def count_sensors_with_sessions(self):
        df = self.getFilteredDF()
        df = df[df['sessions'] > 0]
        return len(df)

    def count_sensors_charging(self):
        df = self.getFilteredDF()
        df = df[df['mA'] > 0]
        return len(df)