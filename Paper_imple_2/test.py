import cv2
import numpy as np
from math import log10, sqrt
from PIL import Image
import argparse
from skimage.metrics import structural_similarity as ssim

# Function to calculate the Mean Squared Error (MSE)
def calculate_mse(original, processed):
    return np.mean((original - processed) ** 2)

# Function to calculate PSNR
def calculate_psnr(original, processed):
    mse = calculate_mse(original, processed)
    if mse == 0:  # No noise in the images, they are identical
        return 100
    max_pixel = 255.0
    psnr = 20 * log10(max_pixel / sqrt(mse))
    return psnr

# Function to calculate Structural Similarity Index (SSIM)
def calculate_ssim(original, processed):
    ssim_value, _ = ssim(original, processed, full=True)
    return ssim_value

# Function to calculate Mean Absolute Error (MAE)
def calculate_mae(original, processed):
    return np.mean(np.abs(original - processed))

# Function to calculate Normalized Root Mean Squared Error (NRMSE)
def calculate_nrmse(original, processed):
    rmse = sqrt(np.mean((original - processed) ** 2))
    return rmse / (original.max() - original.min())

# Function to resize the processed image to match the original
def resize_image_to_match(original, processed):
    return np.array(Image.fromarray(processed).resize((original.shape[1], original.shape[0]), Image.BILINEAR))

# Load the images
def load_image(image_path):
    return np.array(Image.open(image_path).convert('L'))

def main():
    parser = argparse.ArgumentParser(description="Calculate image quality metrics between two images.")
    parser.add_argument('original_image', type=str, help="Path to the original image")
    parser.add_argument('processed_image', type=str, help="Path to the processed image")

    args = parser.parse_args()

    # Load the original and processed images
    original_image = load_image(args.original_image)
    processed_image = load_image(args.processed_image)

    # Resize the processed image to match the original dimensions if they differ
    if original_image.shape != processed_image.shape:
        print("Warning: Images do not have the same dimensions. Resizing processed image to match original.")
        processed_image = resize_image_to_match(original_image, processed_image)

    # Calculate metrics
    psnr_value = calculate_psnr(original_image, processed_image)
    mse_value = calculate_mse(original_image, processed_image)
    ssim_value = calculate_ssim(original_image, processed_image)
    mae_value = calculate_mae(original_image, processed_image)
    nrmse_value = calculate_nrmse(original_image, processed_image)

    # Print the results
    print(f"PSNR between the original and processed image: {psnr_value} dB")
    print(f"MSE between the original and processed image: {mse_value}")
    print(f"SSIM between the original and processed image: {ssim_value}")
    print(f"MAE between the original and processed image: {mae_value}")
    print(f"NRMSE between the original and processed image: {nrmse_value}")

if __name__ == "__main__":
    main()
