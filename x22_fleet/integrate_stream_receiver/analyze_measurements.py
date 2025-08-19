#!/usr/bin/env python3

import os
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def find_latest_data_dir():
    # Look for the data directory in the current working directory
    data_dir = "data"
    if not os.path.exists(data_dir):
        raise FileNotFoundError("Data directory not found")
    
    # List all subdirectories and sort by name (which contains timestamp)
    subdirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    if not subdirs:
        raise FileNotFoundError("No measurement directories found")
    
    # Sort by timestamp (directory name format: YYYYMMDD_HHMMSS)
    latest_dir = sorted(subdirs)[-1]
    return os.path.join(data_dir, latest_dir)

def load_sensor_data(data_dir):
    sensor_data = {}
    
    # Load each CSV file in the directory
    for filename in os.listdir(data_dir):
        if filename.endswith('.csv'):
            sensor_name = filename.replace('.csv', '')
            file_path = os.path.join(data_dir, filename)
            
            try:
                # Read CSV file
                df = pd.read_csv(file_path)
                
                # Calculate accelerometer vector magnitude
                df['acc_mag'] = np.sqrt(df['acc_x']**2 + df['acc_y']**2 + df['acc_z']**2)
                
                sensor_data[sensor_name] = df
                
            except Exception as e:
                print(f"Error loading data for sensor {sensor_name}: {e}")
    
    return sensor_data

def plot_data(sensor_data):
    # Create figure with secondary y-axis
    fig = make_subplots(rows=3, cols=1, 
                       subplot_titles=('Accelerometer Vector Magnitude', 'Raw Timestamps', 'Timestamp Differences'),
                       vertical_spacing=0.1)
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']  # Default plotly colors
    
    # Add traces for each sensor
    for idx, (sensor_name, df) in enumerate(sensor_data.items()):
        # Get timestamps
        timestamps = pd.to_numeric(df['timestamp'])
        sample_indices = np.arange(len(timestamps))
        color = colors[idx % len(colors)]
        
        # Calculate timestamp differences
        timestamp_diffs = np.diff(timestamps)
        diff_indices = np.arange(len(timestamp_diffs))
        
        # Plot 1: Accelerometer magnitude
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=df['acc_mag'],
                name=f"{sensor_name} - Acc Mag",
                mode='lines',
                line=dict(color=color),
                hovertemplate='Sample: %{x}<br>Magnitude: %{y:.3f}g<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Plot 2: Raw timestamps
        fig.add_trace(
            go.Scatter(
                x=sample_indices,
                y=timestamps,
                name=f"{sensor_name} - Timestamp",
                mode='lines',
                line=dict(color=color),
                hovertemplate='Sample: %{x}<br>Timestamp: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Plot 3: Timestamp differences
        fig.add_trace(
            go.Scatter(
                x=diff_indices,
                y=timestamp_diffs,
                name=f"{sensor_name} - Time Diff",
                mode='lines',
                line=dict(color=color),
                hovertemplate='Sample: %{x}<br>Time Diff: %{y:.2f}µs<extra></extra>'
            ),
            row=3, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=1200,  # Increase height for better visualization
        showlegend=True,
        template='plotly_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        hovermode='x unified'
    )
    
    # Update axes labels and grid
    fig.update_xaxes(title_text="Sample Number", showgrid=True, gridwidth=1, gridcolor='LightGray', row=1, col=1)
    fig.update_xaxes(title_text="Sample Number", showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=1)
    fig.update_xaxes(title_text="Sample Number", showgrid=True, gridwidth=1, gridcolor='LightGray', row=3, col=1)
    fig.update_yaxes(title_text="Accelerometer Magnitude (g)", showgrid=True, gridwidth=1, gridcolor='LightGray', row=1, col=1)
    fig.update_yaxes(title_text="Timestamp (µs)", showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=1)
    fig.update_yaxes(title_text="Time Difference (µs)", showgrid=True, gridwidth=1, gridcolor='LightGray', row=3, col=1)
    
    # Show the interactive plot in browser
    fig.show()

def main():
    try:
        # Find the latest data directory
        data_dir = find_latest_data_dir()
        print(f"Analyzing data from: {data_dir}")
        
        # Load sensor data and calculate magnitudes
        sensor_data = load_sensor_data(data_dir)
        print(f"Loaded data for {len(sensor_data)} sensors")
        
        # Create and show the interactive plot
        plot_data(sensor_data)
        print("Interactive plot opened in your default web browser")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 