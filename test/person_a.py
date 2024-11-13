#!/usr/bin/env python3

import numpy as np
from hashlib import sha256
from PIL import Image
import argparse

# Function to calculate SHA-256 hash of a value
def calculate_sha256(value):
    return sha256(value.encode('utf-8')).hexdigest()

# Function to securely store the pixel hashes
def store_hashes(hashes, file_path="hashes_storage.txt"):
    with open(file_path, "w") as file:
        for hash_value in hashes:
            file.write(hash_value + "\n")
    print("Hashes stored successfully.")

# Function to calculate the pixel hash
def calculate_pixel_hash(x, y, value):
    return calculate_sha256(f"{x},{y},{value}")

# Main function to handle user inputs and generate pixel hashes
def main():
    parser = argparse.ArgumentParser(description="Generate and store pixel hashes for an image.")
    parser.add_argument('image_path', type=str, help="Path to the input image")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.image_path).convert('L')
    image_array = np.array(image)

    # Generate hashes for each pixel
    hashes = []
    for i in range(image_array.shape[0]):
        for j in range(image_array.shape[1]):
            pixel_value = image_array[i, j]
            pixel_hash = calculate_pixel_hash(i, j, str(pixel_value))
            hashes.append(pixel_hash)

    # Store the hashes
    store_hashes(hashes)

if __name__ == "__main__":
    main()
