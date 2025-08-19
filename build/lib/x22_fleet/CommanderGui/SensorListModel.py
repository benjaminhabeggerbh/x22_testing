from PySide6.QtCore import QObject, Slot, Signal, Qt, QAbstractListModel, QModelIndex, Property

class SensorListModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    APRole = Qt.UserRole + 2
    VoltageRole = Qt.UserRole + 3
    CurrentRole = Qt.UserRole + 4
    SOCRole = Qt.UserRole + 5
    TimeValueRole = Qt.UserRole + 6
    SessionsRole = Qt.UserRole + 7
    FlashFreeRole = Qt.UserRole + 8
    GenericMessageRole = Qt.UserRole + 9
    FirmwareRole = Qt.UserRole + 10
    UpdateAgeRole = Qt.UserRole + 11
    UpdloadProgressRole = Qt.UserRole + 12
    SpeedRole = Qt.UserRole + 13
    FwPendingRole = Qt.UserRole + 14

    def __init__(self, parent=None):
        super(SensorListModel, self).__init__(parent)
        self._data = []


    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        sensor = self._data[index.row()]

        if role == SensorListModel.NameRole:
            return sensor.get("name", "Unknown")
        elif role == SensorListModel.APRole:
            return sensor.get("AP", "N/A")
        elif role == SensorListModel.VoltageRole:
            return sensor.get("v", "N/A")
        elif role == SensorListModel.CurrentRole:
            return sensor.get("mA", "N/A")
        elif role == SensorListModel.SOCRole:
            return sensor.get("soc", "N/A")
        elif role == SensorListModel.TimeValueRole:
            return sensor.get("timeVal", "N/A")
        elif role == SensorListModel.SessionsRole:
            return sensor.get("sessions", "N/A")
        elif role == SensorListModel.FlashFreeRole:
            return sensor.get("flashFree", "N/A")
        elif role == SensorListModel.GenericMessageRole:
            return sensor.get("generic_message", "N/A")
        elif role == SensorListModel.FirmwareRole:
            return sensor.get("fw", "N/A")
        elif role == SensorListModel.UpdateAgeRole:
            return sensor.get("updateAge", "N/A")
        elif role == SensorListModel.SpeedRole:
            return sensor.get("speed", "N/A")
        elif role == SensorListModel.FwPendingRole:
            return sensor.get("fwPending", "N/A")

            
        elif role == SensorListModel.UpdloadProgressRole:
            progress = "0/0"
            try:
                sync = int(sensor.get("sync", 0))
                total = round(int(sensor.get("total",0)) / (1024 * 1024),1)
                sent = round(int(sensor.get("sent",0)) / (1024 * 1024),1)
                progress = "0"
                if sync == 1:
                    progress = f"{sent}/{total}"
            except Exception as ax:
                pass            
            return progress

    def roleNames(self):
        roles = dict()
        roles[SensorListModel.NameRole] = b"name"
        roles[SensorListModel.APRole] = b"AP"
        roles[SensorListModel.VoltageRole] = b"voltage"
        roles[SensorListModel.CurrentRole] = b"current"
        roles[SensorListModel.SOCRole] = b"soc"
        roles[SensorListModel.TimeValueRole] = b"timeVal"
        roles[SensorListModel.SessionsRole] = b"sessions"
        roles[SensorListModel.FlashFreeRole] = b"flashFree"
        roles[SensorListModel.GenericMessageRole] = b"generic_message"
        roles[SensorListModel.FirmwareRole] = b"fw"
        roles[SensorListModel.UpdateAgeRole] = b"updateAge"     
        roles[SensorListModel.UpdloadProgressRole] = b"upload"     
        roles[SensorListModel.SpeedRole] = b"speed"          
        roles[SensorListModel.FwPendingRole] = b"fwPending"   

        
        return roles

    @Slot(list)
    def updateData(self, new_data):
        to_add = []
        to_update = []
        to_remove = []
        new_data_names = [sensor.get("name") for sensor in new_data]

        # Find sensors to remove
        for i, sensor in enumerate(self._data):
            if sensor.get("name") not in new_data_names:
                to_remove.append(i)

        # Remove rows that are no longer in the filtered data
        if to_remove:
            for row in sorted(to_remove, reverse=True):
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._data[row]
                self.endRemoveRows()

        # Find sensors to update or add
        existing_data_names = [sensor.get("name") for sensor in self._data]
        for new_sensor in new_data:
            if new_sensor.get("name") in existing_data_names:
                # Update existing sensor
                index = existing_data_names.index(new_sensor.get("name"))
                if self._data[index] != new_sensor:
                    self._data[index] = new_sensor
                    to_update.append(index)
            else:
                # Add new sensor
                to_add.append(new_sensor)

        # Add new sensors
        if to_add:
            self.beginInsertRows(QModelIndex(), len(self._data), len(self._data) + len(to_add) - 1)
            self._data.extend(to_add)
            self.endInsertRows()

        # Emit dataChanged signal for updated rows
        for row in to_update:
            if 0 <= row < len(self._data):
                index = self.index(row, 0)
                self.dataChanged.emit(index, index)
