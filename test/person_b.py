#!/usr/bin/env python3

import numpy as np
from hashlib import sha256
from PIL import Image, ImageDraw
import argparse

# Function to calculate SHA-256 hash of a value
def calculate_sha256(value):
    return sha256(value.encode('utf-8')).hexdigest()

# Function to retrieve stored hashes
def retrieve_hashes(file_path="hashes_storage.txt"):
    with open(file_path, "r") as file:
        hashes = [line.strip() for line in file.readlines()]
    return hashes

# Function to calculate the pixel hash
def calculate_pixel_hash(x, y, value):
    return calculate_sha256(f"{x},{y},{value}")

# Main function to handle user inputs and verify the image
def main():
    parser = argparse.ArgumentParser(description="Verify an image against stored pixel hashes.")
    parser.add_argument('image_path', type=str, help="Path to the received image")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.image_path).convert('L')
    image_array = np.array(image)

    # Retrieve stored hashes
    stored_hashes = retrieve_hashes()

    tampered_pixels = []

    # Check each pixel and compare hashes
    for i in range(image_array.shape[0]):
        for j in range(image_array.shape[1]):
            current_value = str(image_array[i, j])
            current_hash = calculate_pixel_hash(i, j, current_value)
            expected_hash = stored_hashes[i * image_array.shape[1] + j]

            if current_hash != expected_hash:
                print(f"Mismatch at ({i}, {j}): Expected hash {expected_hash}, got {current_hash}")
                tampered_pixels.append((i, j, current_value))

    is_tampered = len(tampered_pixels) > 0
    print(f"Is tampered: {is_tampered}")
    #print(f"Tampered pixels: {tampered_pixels}")

    if tampered_pixels:
        # Highlight tampered pixels in the image
        tampered_image = Image.open(args.image_path).convert('RGB')
        draw = ImageDraw.Draw(tampered_image)
        for i, j, _ in tampered_pixels:
            draw.rectangle([j, i, j + 1, i + 1], outline="red")
        
        tampered_image.save("tampered_analysis.jpeg")
        print("Tampered areas highlighted and saved as tampered_analysis.jpeg")

    # Write tampered pixels to a file
    with open("tampered_analysis.txt", "w") as file:
        for i, j, value in tampered_pixels:
            file.write(f"Pixel tampered at ({i}, {j}) with value {value}\n")

if __name__ == "__main__":
    main()
