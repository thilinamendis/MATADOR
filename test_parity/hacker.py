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

# Function to add salt-and-pepper noise
def add_salt_pepper_noise(image_array, noise_percentage):
    tampered_image = np.copy(image_array)
    total_pixels = tampered_image.size
    num_noise_pixels = int(noise_percentage * total_pixels)
    
    # Randomly select pixel locations to apply noise
    noisy_positions = random.sample(list(np.ndindex(tampered_image.shape)), num_noise_pixels)
    
    for position in noisy_positions:
        i, j = position
        
        # Randomly assign the pixel value to either 0 (black) or 255 (white)
        tampered_image[i, j] = 0 if random.random() < 0.5 else 255
    
    return tampered_image, noisy_positions

# Function to add Gaussian noise
def add_gaussian_noise(image_array, num_pixels, mean=0, sigma=10):
    tampered_image = np.copy(image_array)
    
    # Get the total number of pixels in the image
    height, width = tampered_image.shape
    total_pixels = height * width
    
    # Select 'num_pixels' random pixel locations to apply Gaussian noise
    noisy_positions = random.sample(list(np.ndindex(height, width)), num_pixels)
    
    # Apply Gaussian noise only to the selected pixels
    for position in noisy_positions:
        i, j = position
        
        # Generate Gaussian noise for the selected pixel
        noise = np.random.normal(mean, sigma)
        
        # Add the noise to the current pixel value
        tampered_image[i, j] = tampered_image[i, j] + noise
        
        # Ensure the pixel value stays in the valid range [0, 255]
        tampered_image[i, j] = np.clip(tampered_image[i, j], 0, 255).astype(np.uint8)

    print(f"Gaussian noise added to {num_pixels} pixels with a mean of {mean} and a standard deviation of {sigma}.")
    return tampered_image, noisy_positions


# Main function to tamper the image
def main():
    parser = argparse.ArgumentParser(description="Tamper an image.")
    parser.add_argument('image', type=str, help="Path to the processed image by Person A")
    
    # Tampering options
    parser.add_argument('--msb', type=int, help="Number of MSB bits to tamper")
    parser.add_argument('--locations', type=int, help="Number of random pixels to tamper")
    parser.add_argument('--salt_pepper', type=float, help="Percentage of salt-and-pepper noise to add (0.0 to 1.0)")
    parser.add_argument('--gaussian', action='store_true', help="Add Gaussian noise to the image")
    parser.add_argument('--gaussian_pixels', type=int, help="Number of pixels to add Gaussian noise")
    parser.add_argument('--output', type=str, default='tampered_image.png', help="Path to save the tampered image")
    
    args = parser.parse_args()

    # Load the processed image
    original_image = load_image(args.image)
    processed_image = np.array(original_image.convert('L'))  # Convert to grayscale

    tampered_image = processed_image  # Initialize tampered image as the original image
    tampered_positions = []  # List to store positions of tampered pixels for debugging

    # Apply MSB tampering if specified
    if args.msb and args.locations:
        tampered_image, tampered_positions = tamper_image(tampered_image, args.msb, args.locations)
        print(f"MSB tampered at positions: {tampered_positions}")

    # Apply salt-and-pepper noise if specified
    if args.salt_pepper:
        tampered_image, noisy_positions = add_salt_pepper_noise(tampered_image, args.salt_pepper)
        print(f"Salt-and-pepper noise added to {len(noisy_positions)} pixels.")

    # Apply Gaussian noise if specified
    # Apply Gaussian noise to a selected number of pixels if specified
    if args.gaussian and args.gaussian_pixels:
        tampered_image, noisy_positions = add_gaussian_noise(tampered_image, args.gaussian_pixels)
        print(f"Gaussian noise added to {len(noisy_positions)} pixels.")

    # Save the tampered image with the original metadata
    save_image(tampered_image, original_image, args.output)

if __name__ == "__main__":
    main()
