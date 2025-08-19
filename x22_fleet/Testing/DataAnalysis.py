import numpy as np

class DataAnalysis:
    def __init__(self, device_data):
        self.device_data = device_data
        self.workaroundFirstTwoBuffers = False

    def analyze(self):
        x_vals = self.device_data["x_vals"]
        bat_vals = self.device_data["y_vals_bat"]

        # Apply workaround: Ignore the first 128 samples if enabled
        if self.workaroundFirstTwoBuffers:
            x_vals = x_vals[128:]
            bat_vals = bat_vals[128:]

        total_samples = len(x_vals)
        d = np.diff(x_vals)

        # Log indexes and values where d is not 1
        # unexpected_d_indexes = np.where(d != 1)[0]
        # print("Unexpected d indexes and values:")
        # for idx in unexpected_d_indexes:
        #     print(f"Index: {idx}, Value: {d[idx]}")

        missing_samples = np.sum(d - 1)  # Sum of all differences minus one for each element

        # Calculate average current (in mA)
        average_current = np.mean(bat_vals[:, 1])  # Assuming column 1 holds current data in battery array

        # Calculate average voltage (in mV)
        average_voltage = np.mean(bat_vals[:, 2])  # Assuming column 2 holds voltage data in battery array

        # Analyze std deviation for y_vals_acc, y_vals_gyr, y_vals_mag
        def calculate_std_by_window(y_vals, window_size=10):
            std_devs = []
            for start_idx in range(0, len(y_vals), window_size):
                end_idx = min(start_idx + window_size, len(y_vals))
                window = y_vals[start_idx:end_idx]
                if len(window) > 0:
                    std_devs.append(np.std(window, axis=0))
            return np.array(std_devs)

        acc_std_devs = calculate_std_by_window(self.device_data["y_vals_acc"], window_size=10)
        gyr_std_devs = calculate_std_by_window(self.device_data["y_vals_gyr"], window_size=10)
        mag_std_devs = calculate_std_by_window(self.device_data["y_vals_mag"], window_size=10)

        def count_low_std_devs(std_devs, threshold=0.2):
            avg_std_dev = np.mean(std_devs)
            low_std_dev_count = np.sum(np.all(std_devs < (avg_std_dev * threshold), axis=1))
            return avg_std_dev, low_std_dev_count

        acc_avg_std_dev, acc_low_std_dev_count = count_low_std_devs(acc_std_devs)
        gyr_avg_std_dev, gyr_low_std_dev_count = count_low_std_devs(gyr_std_devs)
        mag_avg_std_dev, mag_low_std_dev_count = count_low_std_devs(mag_std_devs)

        return {
            "total_samples": total_samples,
            "missing_samples": missing_samples,
            "average_current_mA": average_current,
            "average_voltage_mV": average_voltage,
            "acc_avg_std_dev": acc_avg_std_dev,
            "acc_low_std_dev_count": acc_low_std_dev_count,
            "gyr_avg_std_dev": gyr_avg_std_dev,
            "gyr_low_std_dev_count": gyr_low_std_dev_count,
            "mag_avg_std_dev": mag_avg_std_dev,
            "mag_low_std_dev_count": mag_low_std_dev_count
        }
