from DumpFileParser import *
import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    parser = DumpFileParser()
    devData = parser.find_and_parse_files()
    x = np.array(devData["test_device"]["x_vals"])
    d = np.diff(x)

    # Calculate the total range of x values
    total = max(x) - min(x)

    # Count correct and wrong samples
    correctsamples = np.count_nonzero(x == 1)
    wrongsamples = np.sum(x > 1)
    percentWrong = (100 / total) * wrongsamples
    
    # Count missing samples where the difference is not zero
    missing_samples = np.count_nonzero(d != 0)

    # Plotting the differences
    plt.plot(d)
    plt.title("Difference Plot")
    plt.xlabel("Sample index")
    plt.ylabel("Difference value")
    plt.show()

    print(f"Total Range: {total}")
    print(f"Correct Samples: {correctsamples}")
    print(f"Wrong Samples: {wrongsamples}")
    print(f"Percent Wrong: {percentWrong:.2f}%")
    print(f"Missing Samples: {missing_samples}")
