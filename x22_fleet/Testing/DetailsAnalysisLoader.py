import pickle, re
import pandas as pd
from datetime import datetime

class DetailedAnalysisLoader:
    def __init__(self, pickle_file_path="cache/detailed_analysis.pkl"):
        self.pickle_file_path = pickle_file_path
        self.limited_columns = [
            "File Name", "Start Date", "Measurement Length", "total_samples", "missing_samples", 
            "average_current_mA", "average_voltage_mV", "AccFlat", "GyrFlat", "MagFlat"
        ]

    def load_and_display_analysis(self, limited_display=False):
        """Load the detailed analysis pickle file, calculate additional metrics, and display its contents."""
        try:
            # Load the pickle file
            with open(self.pickle_file_path, "rb") as f:
                all_detailed_analysis = pickle.load(f)

            # Store results for writing to text file
            detailed_analysis_results = []

            # Display detailed analysis for each session
            for session, df in all_detailed_analysis.items():
                # Calculate length of measurement in minutes:seconds
                df.insert(df.columns.get_loc("total_samples") + 1, "Measurement Length", 
                          df["total_samples"].apply(
                              lambda samples: f"{(samples // 200) // 60}:{(samples // 200) % 60:02d}"
                          ))

                # Add start date column in YY-MM-DD-HH:MM:SS format
                df.insert(df.columns.get_loc("File Name") + 1, "Start Date", 
                          df["File Name"].apply(
                              lambda name: datetime.utcfromtimestamp(
                                  int(re.search(r"-(\d+)_rec\.bd", name).group(1))
                              ).strftime("%y-%m-%d-%H:%M:%S")
                          ))

                # Rename and reposition flatness columns
                if "acc_low_std_dev_count" in df.columns:
                    df.rename(columns={"acc_low_std_dev_count": "AccFlat"}, inplace=True)
                if "gyr_low_std_dev_count" in df.columns:
                    df.rename(columns={"gyr_low_std_dev_count": "GyrFlat"}, inplace=True)
                if "mag_low_std_dev_count" in df.columns:
                    df.rename(columns={"mag_low_std_dev_count": "MagFlat"}, inplace=True)

                for col in ["AccFlat", "GyrFlat", "MagFlat"]:
                    if col in df.columns:
                        df.insert(df.columns.get_loc("average_current_mA") + 1, col, df.pop(col))

                # Display only limited columns if specified
                if limited_display:
                    df = df[self.limited_columns]

                detailed_analysis_results.append((session, df))

            # Write the detailed analysis results to a text file
            with open("detailed_analysis_output.txt", "w") as output_file:
                for session, df in detailed_analysis_results:
                    output_file.write(f"Detailed Analysis for Session {session}:\n")
                    output_file.write(df.to_string(index=False))
                    output_file.write("\n\n" + "-" * 80 + "\n\n")

            print("Detailed analysis results have been saved to 'detailed_analysis_output.txt'.")

        except FileNotFoundError:
            print(f"The file {self.pickle_file_path} does not exist.")
        except Exception as e:
            print(f"An error occurred while loading the pickle file: {e}")

if __name__ == "__main__":
    loader = DetailedAnalysisLoader()
    loader.load_and_display_analysis(limited_display=True)
