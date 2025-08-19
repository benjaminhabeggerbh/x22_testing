class SensorStats:
    def __init__(self, status_listener,StationName):
        self.status_listener = status_listener
        self.StationName = StationName
    
    def statusListenerOnline(self):
        df, online = self.status_listener.fetch_data()
        return online

    def getFilteredDF(self):
        df, online = self.status_listener.fetch_data()
        df = df[df["AP"] ==  self.StationName]
        return df
        
    def count_sensors(self):
        return len(self.getFilteredDF())

    def count_sensors_with_sessions(self):
        df = self.get_sensors_online()
        df = df[df['sessions'] > 0]
        return df.shape[0]

    def get_sensors_online(self):
        df = self.getFilteredDF()
        df = df[df['updateAge'] < 30]
        return df

    def count_sensors_online(self):
        df = self.get_sensors_online()
        return len(df)

    def count_sensors_charging(self):
        df = self.getFilteredDF()
        df = df[df['mA'] > 0]
        return len(df)