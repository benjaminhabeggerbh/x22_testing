import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "MaterialDesign.js" as MD

ApplicationWindow {
    visible: true
    width: 640
    height: 480
    title: "Commander GUI"
    id: root

    signal refreshSensorData()

    property int nameColumnWidth: 200
    property int apColumnWidth: 200
    property int batComunWidth: 200
    property int timeValueColumnWidth: 100
    property int sessionsColumnWidth: 80
    property int flashFreeColumnWidth: 80
    property int uploadColumnWidth: 150
    property bool showAdvanced: false
    property bool showButtons: false
    property string currentStation: ""

    LogViewPopup {
        id: logPopup
    }

    Rectangle {
        id: headerBar
        width: parent.width
        height: 60
        color: commanderGui.statusListenerOnline ?  "lightblue" : "red"

        Row {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            Text {
                text: "Station Select: "
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            ComboBox {
                id: filterDropdown
                anchors.verticalCenter: parent.verticalCenter
                model: commanderGui.apList
                width: 200
                height: 50
                onCurrentIndexChanged: function(){
                    var station = model[currentIndex]
                    console.debug("station selected: " + station)
                    commanderGui.filter_changed(station)
                    root.currentStation = station
                }
            }

            Text {
                id: rowCountLabel
                text: "Sensors total: " + (commanderGui.sensorsTotal)
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                id: sensorsOnlineLabel
                text: "Sensors online: " + (commanderGui.sensorsOnline)
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
            CheckBox {
                id: chkShowOnlyOnline
                text: "Show only online: "
                onClicked: commanderGui.showOnlyOnline = checked
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }   
            Text{
                visible: !commanderGui.statusListenerOnline 
                text: "Disconnected from server ... "
                anchors.verticalCenter: parent.verticalCenter
            }       
        }
    }

    Rectangle {
        id: listHeader
        anchors.top: headerBar.bottom
        width: parent.width
        height: 40
        color: "lightgray"

        Row {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            Text {
                text: "Id,   Fw,   Age"
                font.bold: true
                width: nameColumnWidth
            }

            Text {
                text: "AP"
                font.bold: true
                width: apColumnWidth
            }

            Text {
                text: "Bat (V,   mA,   SOC)"
                font.bold: true
                width: batComunWidth
            }

            Text {
                text: "Time?"
                font.bold: true
                width: timeValueColumnWidth
            }

            Text {
                text: "Sessions"
                font.bold: true
                width: sessionsColumnWidth
            }

            Text {
                text: "Flash Free"
                font.bold: true
                width: flashFreeColumnWidth
            }

            Text {
                text: "Transfer"
                font.bold: true
                width: uploadColumnWidth
            }

        }
    }

    ListView {
        id: sensorListView
        anchors.top: listHeader.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        model: sensorListModel
        property int activeRow: -1

        function showButtonsForRow(rowIndex) {
            if (activeRow == rowIndex) {
                return
            }
            activeRow = rowIndex
            for (let i = 0; i < sensorListView.count; i++) {
                var item = sensorListView.itemAtIndex(i);
                if (item) {
                    item.rowActive = (i === rowIndex);
                }
            }
        }

        clip: true
        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AlwaysOn
        }

        delegate: Rectangle {
            id: rowRoot
            property bool rowActive: false
            property bool allSensorsRow: index == 0
            property string currentAP: allSensorsRow ? root.currentStation : model.AP
            property string currentFW: model.fw
            MouseArea {
                hoverEnabled: true
                anchors.fill: rowRoot
                onPositionChanged: {
                    sensorListView.showButtonsForRow(index)
                }
            }
            width: sensorListView.width
            height: rowActive || allSensorsRow ? 85 : 45
            color: model.index % 2 === 0 ? "#d0e7ff" : "#b0d4ff"
            border.color: "#90a4ae"
            border.width: 1
            radius: 2
            anchors.margins: 5

            Row {
                id: labelsRow
                width: sensorListView.width
                height: 40
                spacing: 10
                anchors.topMargin: 10
                anchors.top: rowRoot.top
                Text {
                    property string updatePending: model.fwPending === "1" ? "*" : ""
                    property string shortName: model.name.startsWith("X22_") ? model.name.substring(4) : model.name
                    property string displayString: allSensorsRow ? "AllSensors" : shortName + ",   " + model.fw + updatePending + ",   " + model.updateAge
                    text: displayString
                    font.pointSize: allSensorsRow ? 20 : 10
                    font.bold: true
                    width: nameColumnWidth
                }

                Text {
                    text: !allSensorsRow ? model.AP : root.currentStation
                    width: apColumnWidth
                }

                Text {
                    text: !allSensorsRow ? model.voltage + " mV,   " + model.current + " mA,   " + model.soc + "%" : ""
                    width: batComunWidth
                }

                Text {
                    text: !allSensorsRow ? model.timeVal : ""
                    width: timeValueColumnWidth
                }

                Text {
                    text: model.sessions
                    width: sessionsColumnWidth
                }

                Text {
                    text: !allSensorsRow ? model.flashFree : 0
                    width: flashFreeColumnWidth
                }

                Text {
                    text: !allSensorsRow ? model.upload + " MB  @ " + model.speed + " KB /s " : 0
                    width: uploadColumnWidth
                }

                Text {
                    text: "Generic Message:"
                    font.bold: true
                    MouseArea {
                        anchors.fill: parent
                        onClicked: logPopup.showLog(model.name, model.generic_message)
                    }

                }
                Text {
                    text: model.generic_message
                    MouseArea {
                        anchors.fill: parent
                        onClicked: logPopup.showLog(model.name, model.generic_message)
                    }
                }

            }

            Row {
                width: sensorListView.width
                height: 40
                spacing: 10
                visible: rowActive
                anchors.top: labelsRow.bottom
                // Using Standard Button Component
                StandardButton {
                    mdIcon: MD.icons.lightbulb_outline
                    text: "Identify"
                    onClicked: commanderGui.send_command(model.name, "identify")
                }
                StandardButton {
                    mdIcon: MD.icons.replay
                    onClicked: commanderGui.send_command(model.name, "reboot")
                    text: "Reboot"
                }
                StandardButton {
                    mdIcon: MD.icons.sync
                    text: "Sync"
                    onClicked: commanderGui.send_command(model.name, "sync")
                }
                StandardButton {
                    mdIcon: MD.icons.hotel
                    text: "Sleep"
                    onClicked: commanderGui.send_command(model.name, "wifi_sleep")
                }

                StandardButton {
                    mdIcon: MD.icons.settings
                    width: 40
                    text: ""
                    onClicked: root.showAdvanced = !root.showAdvanced
                    id: btnShowAdvanced
                }

                StandardButton {
                    visible: root.showAdvanced
                    mdIcon: MD.icons.delete_forever
                    text: "Erase"
                    onClicked: commanderGui.send_command(model.name, "erase_flash")
                }

                StandardButton {
                    visible: root.showAdvanced
                    mdIcon: MD.icons.mic
                    text: "Start Record"
                    width: 120
                    onClicked: commanderGui.send_command(model.name, "enable_force_record")
                }
                StandardButton {
                    visible: root.showAdvanced
                    mdIcon: MD.icons.mic_off
                    text: "Stop Record"
                    width: 120
                    onClicked: commanderGui.send_command(model.name, "disable_force_record")
                }

                StandardButton {
                    visible: root.showAdvanced
                    mdIcon: MD.icons.settings_power
                    text: "Battery Calibration"
                    width: 150
                    onClicked: commanderGui.send_command(model.name, "factory_reset")
                }
                StandardButton {
                    mdIcon: MD.icons.refresh
                    visible: root.showAdvanced
                    text: "FW-Update"
                    width: 150
                    onClicked: commanderGui.deploy_fw_update(model.name,stationDropdown.currentText, firmwareDropdown.currentText)
                }

                ComboBox {
                    id: stationDropdown
                    background: Rectangle {
                        color: stationDropdown.currentText == rowRoot.currentAP ? "lightgray" : "red"
                        border.color: "gray"
                        radius: 5
                    }
                    visible: root.showAdvanced                    
                    model: ["EvoStationMaintenance", "EvoStation1", "EvoStation2", "EvoStation3", "EvoStation4", "EvoStation5", "EvoStation6", "EvoStation7", "EvoStation8", "EvoStation9", "EvoStation10", "EvoStation11", "EvoStation12", "EvoStation13", "EvoStation14"]
                    width: 200
                    height: 50
                    currentIndex: model.indexOf(rowRoot.currentAP)
                    anchors.verticalCenter: btnShowAdvanced.verticalCenter
                }

                ComboBox {
                    id: firmwareDropdown
                    visible: root.showAdvanced                    
                    background: Rectangle {
                        color: "lightgray"
                        border.color: "gray"
                        radius: 5
                    }                    
                    model: ["1.92", "1.93", "1.94", "1.95"]
                    width: 100
                    height: 50
                    currentIndex: model.indexOf(rowRoot.currentFW)
                    anchors.verticalCenter: btnShowAdvanced.verticalCenter                    
                }
            }
        }
    }
}
