import numpy as np
import random
from PIL import Image, PngImagePlugin
import argparse
import os

# python3 hacker.py Person_A/processed_images/30x30_random_image.png key/encryption_key.txt --msb 4 --locations 10 --output tampered_image.png

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

# Function to tamper X MSBs in Y random locations
def tamper_image(image_array, X, Y):
    tampered_image = np.copy(image_array)
    height, width = tampered_image.shape
    
    # Select Y random pixel locations
    tampered_positions = random.sample(list(np.ndindex(height, width)), Y)
    
    for position in tampered_positions:
        i, j = position
        
        # Get current pixel value and tamper its MSB by flipping X bits
        current_pixel = tampered_image[i, j]
        
        # Generate a mask to tamper the X MSBs
        msb_mask = (1 << X) - 1
        msb_mask <<= (8 - X)
        
        # Apply XOR to flip the X MSBs
        tampered_pixel = current_pixel ^ msb_mask
        tampered_image[i, j] = tampered_pixel
    
    return tampered_image, tampered_positions

# Main function to tamper the image and run Person B's script
def main():
    parser = argparse.ArgumentParser(description="Tamper an image and test Person B's detection.")
    parser.add_argument('image', type=str, help="Path to the processed image by Person A")
    parser.add_argument('key', type=str, help="Path to the encryption key for Person B")
    parser.add_argument('--msb', type=int, default=2, help="Number of MSB bits to tamper (default: 2)")
    parser.add_argument('--locations', type=int, default=5, help="Number of random pixels to tamper (default: 5)")
    parser.add_argument('--output', type=str, default='tampered_image.png', help="Path to save the tampered image")
    
    args = parser.parse_args()

    # Load the processed image from Person A
    original_image = load_image(args.image)
    processed_image = np.array(original_image.convert('L'))

    # Tamper the image by flipping X MSBs in Y locations
    tampered_image, tampered_positions = tamper_image(processed_image, args.msb, args.locations)

    # Save the tampered image with the original metadata
    save_image(tampered_image, original_image, args.output)

    # Print tampered positions for debugging purposes
    print(f"Tampered positions: {tampered_positions}")

if __name__ == "__main__":
    main()
