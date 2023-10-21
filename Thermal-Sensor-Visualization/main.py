from typing import Tuple
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib import pyplot as plt
from scipy.ndimage import gaussian_filter


def load_temperatures_from_file(filename: str) -> np.ndarray:
    with open(filename, "r") as f:
        temperature_data = f.read()
    temperature_array = np.array(temperature_data.split(","), dtype=int)
    return temperature_array / 100.0


def convert_to_thermal_image(filename: str) -> np.ndarray:
    temperatures = load_temperatures_from_file(filename)
    return temperatures.reshape(24, 32)


def enhance_thermal_image(
    thermal_image: np.ndarray, upscale_factor: int = 10
) -> np.ndarray:
    # Upscale
    up_scaled_image = np.repeat(thermal_image, upscale_factor, axis=0)
    up_scaled_image = np.repeat(up_scaled_image, upscale_factor, axis=1)

    # Apply Gaussian filter
    return gaussian_filter(up_scaled_image, sigma=upscale_factor / 2)


def visualize_and_analyze_temperatures(
    thermal_image: np.ndarray, upscale_factor: int = 10, save_path: str = None
) -> Tuple[float, float]:
    # Find coldest and hottest points
    min_temperature = thermal_image.min()
    max_temperature = thermal_image.max()
    co_ords_coldest = np.unravel_index(thermal_image.argmin(), thermal_image.shape)
    co_ords_hottest = np.unravel_index(thermal_image.argmax(), thermal_image.shape)

    # Visualization
    plt.figure(figsize=(12, 9))
    plt.imshow(thermal_image, cmap="inferno", interpolation="bilinear")
    plt.colorbar(label="Temperature (°C)")

    # Mark coldest point
    plt.gca().add_patch(
        Rectangle(
            (co_ords_coldest[1] - upscale_factor, co_ords_coldest[0] - upscale_factor),
            2 * upscale_factor,
            2 * upscale_factor,
            linewidth=2,
            edgecolor="blue",
            facecolor="none",
        )
    )
    # Mark hottest point
    plt.gca().add_patch(
        Rectangle(
            (co_ords_hottest[1] - upscale_factor, co_ords_hottest[0] - upscale_factor),
            2 * upscale_factor,
            2 * upscale_factor,
            linewidth=2,
            edgecolor="red",
            facecolor="none",
        )
    )

    plt.title("Temperature Analysis on Enhanced Thermal Image")

    if save_path:
        plt.savefig(save_path, format="png", dpi=300, bbox_inches="tight")

    plt.show()
    return min_temperature, max_temperature


if __name__ == "__main__":
    file_name = "data4.txt"
    thermal_img = convert_to_thermal_image(f"input/{file_name}")
    enhanced_img = enhance_thermal_image(thermal_img)
    cold_temp, hot_temp = visualize_and_analyze_temperatures(
        enhanced_img, save_path=f"output/{file_name.split('.')[0]}.png"
    )
    print(f"Coldest Temperature: {cold_temp}°C, Hottest Temperature: {hot_temp}°C")
