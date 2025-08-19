import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: logViewPopup
    visible: false
    anchors.fill: parent
    z: 10

    property string logSensorName: ""
    property string logContent: ""
    property int logOffset: 0 // Added property to track offset
    property int numLines: 100 // Added property to track offset

    Rectangle {
        id: overlay
        color: "#00000099"
        anchors.fill: parent
    }

    Rectangle {
        id: popupContainer
        width: parent ? parent.width * 0.8 : 640
        height: parent ? parent.height * 0.8 : 480
        color: "white"
        radius: 10
        anchors.centerIn: parent
        border.color: "#ccc"
        border.width: 2

        Column {
            width: parent.width
            height: parent.height
            anchors.margins: 10

            Rectangle {
                id: header
                height: 40
                width: parent.width
                color: "lightblue"

                Row {
                    width: parent.width
                    height: parent.height
                    spacing: 10
                    anchors.margins: 10

                    Text {
                        id: title
                        text: "Log View"
                        font.bold: true
                        font.pointSize: 16
                        verticalAlignment: Text.AlignVCenter
                    }

                    Text {
                        id: sensorNameDisplay
                        text: logSensorName
                        font.pointSize: 14
                        verticalAlignment: Text.AlignVCenter
                    }

                    Text {
                        id: pagination
                        text: logOffset + " - " + (logOffset + numLines)
                        font.pointSize: 14
                        verticalAlignment: Text.AlignVCenter
                    }

                    Button {
                        text: "Previous"
                        onClicked: logViewPopup.requestPreviousPage()
                        width: 100
                    }

                    Button {
                        id: nextButton
                        text: "Next"
                        onClicked: logViewPopup.requestNextPage()
                        width: 100
                    }

                    Button {
                        id: closeButton
                        text: "Close"
                        onClicked: logViewPopup.visible = false
                        width: 100
                    }
                }
            }

            ScrollView {
                id: scrollArea
                width: parent.width
                height: parent.height - header.height - 20

                TextArea {
                    id: logTextArea
                    text: logContent
                    readOnly: true
                    wrapMode: TextArea.Wrap
                    font.pointSize: 14
                }
            }
        }
    }

    function showLog(sensorName) {
        if (sensorName === undefined) {
            console.error("Invalid parameters passed to showLog: sensorName=" + sensorName );
            return;
        }
        logSensorName = sensorName || "Unknown Sensor";
        logContent = "";
        logOffset = 0; // Reset offset when showing a new log
        logViewPopup.visible = true;
        requestPage();
    }

    function requestPreviousPage() {
        logOffset = Math.max(logOffset - 100, 0); // Ensure offset doesn't go negative
        requestPage();
    }

    function requestNextPage() {
        logOffset += 100;
        requestPage();
    }

    function requestPage() {
        if (logSensorName) {
            logContent = commanderGui.fetch_log_file(logSensorName, 100, logOffset);
        }
    }
}
