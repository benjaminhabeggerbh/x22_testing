import QtQuick 2.15
import QtQuick.Controls 2.15
import "MaterialDesign.js" as MD

Item{
    property alias mdIcon: fontIcon.text
    FontLoader {
        id: iconFont
        source: "MaterialIcons-Regular.ttf"
    }

    Text {  
        id: fontIcon
        font.family: iconFont.name
        font.pixelSize: 24
    }
}
