import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    width: 100
    height: 30
    property string text: ""
    property alias mdIcon: btnIcon.mdIcon
    signal clicked

    Rectangle {
        id: background
        anchors.fill: parent
        color: "lightgray"
        border.color: "gray"
        radius: 5

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            onClicked: {
                root.clicked()
            }
            hoverEnabled: true
            onEntered: background.color = "darkgray"
            onExited: background.color = "lightgray"
        }
    }

    Icon {
        id: btnIcon
        anchors.verticalCenter: btnLabel.verticalCenter
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.leftMargin: 5
        anchors.topMargin: 3
    }

    Text {
        id: btnLabel
        text: parent.text
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: btnIcon.right
        anchors.leftMargin: 30
    }
}
