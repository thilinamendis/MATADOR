import numpy as np
import random
from PIL import Image, PngImagePlugin
import argparse
import os

# Function to load the image and convert it to a NumPy array
def load_image(image_path):
    return Image.open(image_path)

# Function to save the modified image with the original metadata
def save_image(image_array, original_image, output_path):
    tampered_image = Image.fromarray(image_array)
    
    # Copy metadata from the original image
    metadata = original_image.info
    
    # Create a new PngInfo object to store the metadata
    png_info = PngImagePlugin.PngInfo()
    if "EncryptedConfig" in metadata:
        png_info.add_text("EncryptedConfig", metadata["EncryptedConfig"])

    # Save the tampered image with the original metadata
    tampered_image.save(output_path, "PNG", pnginfo=png_info)
    print(f"Tampered image saved as: {output_path}")

# Function to add one or more 50x50 white noise boxes in the image
def add_noise_boxes(image_array, num_boxes):
    tampered_image = np.copy(image_array)
    height, width = tampered_image.shape
    box_size = 50  # 50x50 noise box size
    tampered_positions = []

    # Define Regions of Interest (ROI) and Non-Region of Interest (NROI)
    roi = (0, 0, width // 2, height // 2)  # ROI in the top-left corner
    nroi = (width // 2, height // 2, width, height)  # NROI in the bottom-right corner

    for _ in range(num_boxes):
        if len(tampered_positions) < 1:  # First box in ROI
            x_start = random.randint(roi[0], roi[2] - box_size)
            y_start = random.randint(roi[1], roi[3] - box_size)
            print(f"Adding white noise box in ROI at position: ({x_start}, {y_start})")
        else:  # Second or subsequent box in NROI
            x_start = random.randint(nroi[0], nroi[2] - box_size)
            y_start = random.randint(nroi[1], nroi[3] - box_size)
            print(f"Adding white noise box in NROI at position: ({x_start}, {y_start})")

        # Set the pixels within the 50x50 box to 255 (white)
        tampered_image[y_start:y_start + box_size, x_start:x_start + box_size] = 255
        tampered_positions.append((x_start, y_start, x_start + box_size, y_start + box_size))

    return tampered_image, tampered_positions

# Main function to tamper the image
def main():
    parser = argparse.ArgumentParser(description="Add 50x50 white noise boxes to an image.")
    parser.add_argument('image', type=str, help="Path to the input image")
    parser.add_argument('--boxes', type=int, help="Number of 50x50 noise boxes to add (1 or 2)")
    parser.add_argument('--output', type=str, default='tampered_image.png', help="Path to save the tampered image")
    
    args = parser.parse_args()

    # Load the input image
    original_image = load_image(args.image)
    processed_image = np.array(original_image.convert('L'))  # Convert to grayscale

    # Add 50x50 noise boxes if specified
    if args.boxes:
        if args.boxes < 1 or args.boxes > 2:
            print("Error: Please specify 1 or 2 boxes.")
            return
        tampered_image, box_positions = add_noise_boxes(processed_image, args.boxes)
        print(f"Added {args.boxes} white noise box(es) at positions: {box_positions}")
    else:
        print("Error: Please specify the number of boxes using --boxes (1 or 2).")
        return

    # Save the tampered image with the original metadata
    save_image(tampered_image, original_image, args.output)

if __name__ == "__main__":
    main()
