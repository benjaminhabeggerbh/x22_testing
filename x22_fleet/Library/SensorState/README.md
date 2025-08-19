
# Sensor State Project

This project organizes and visualizes sensor states dynamically. Each sensor has its own folder containing the current state diagram and an HTML page for visualization.

## Structure

```
sensor_state_project/
│
├── sensors/          # Dynamic folder containing per-sensor data
│   ├── Sensor1/      # Folder for Sensor1
│   │   ├── current_state.png  # The latest state diagram for Sensor1
│   │   ├── index.html         # HTML page to visualize Sensor1 state
│   └── Sensor2/      # Folder for Sensor2 (similar structure)
│
├── templates/        # Static templates for HTML
│   ├── index.html    # Template used to initialize sensor folders
└── README.md         # Documentation for the project
```

## Usage

1. **Templates**: The `templates/index.html` is used to create individual sensor pages.
2. **Sensor Folders**: For each sensor, a folder is created dynamically with `current_state.png` and `index.html`.
3. **Visualization**: Open the `index.html` file in any browser to see the sensor's state. The page updates automatically every 3 seconds.
