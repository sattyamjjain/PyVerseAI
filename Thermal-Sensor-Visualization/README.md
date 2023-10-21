
# Thermal Sensor Visualization: Real-time Thermal Imaging and Analysis

Turn raw sensor data into meaningful and interactive thermal images, providing insights into temperature distributions and anomalies.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Contribution](#contribution)

---

## Features

- **Image Generation**: Convert flat sensor data into structured 2D thermal images.
- **Real-time Visualization**: Display thermal images with color scales representing temperature ranges.
- **Image Enhancement**: Upscale and apply Gaussian filters for clearer visualization.
- **Temperature Analysis**: Automatically pinpoint and mark the coldest and hottest regions in the images.

---

## Requirements

- Python 3.7+
- Required libraries: numpy, matplotlib, scipy
- Sensor data in the prescribed format

---

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/sattyamjjain/PyVerseAI.git
   ```

2. Navigate to the project directory:
   ```
   cd Thermal-Sensor-Visualization
   ```

3. Install the required libraries:
   ```
   pip install numpy matplotlib scipy
   ```

---

## Usage

1. Launch the application (assuming a `main.py` entry point):
   ```
   python main.py
   ```

2. Follow the on-screen prompts to load sensor data, generate and enhance images, and perform temperature analysis.

---

## Design Rationale

- **Numpy**: Used for efficient data manipulation and image generation.
- **Matplotlib**: Provides robust tools for visualization and image enhancement.
- **Scipy's Gaussian Filter**: Helps in enhancing the image clarity, making it easier to identify temperature variations.

---

## Challenges and Solutions

- **Challenge**: Converting flat sensor data into meaningful 2D images.
  - **Solution**: Reshape the data array to match the sensor's 2D layout and display as an image.
  
- **Challenge**: Enhancing low-resolution thermal images for better clarity.
  - **Solution**: Utilized upscaling followed by Gaussian smoothing to improve image quality without distorting the temperature data.

---

## Contribution

We appreciate your interest in improving Thermal Sensor Visualization! Feel free to fork the project, make changes, and submit pull requests. All contributions are welcome!

---