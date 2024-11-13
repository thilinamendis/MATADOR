import cv2
import numpy as np
from time import time

def tamper_image(image_path):
    start_time = time()

    # Load the watermarked image
    watermarked_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    tampered_image = watermarked_image.copy()
    height, width = tampered_image.shape
    center_x, center_y = height // 2, width // 2
    tamper_size = 16

    # Apply LSB tampering by modifying only the least significant bit of the pixel values
    tampered_region = tampered_image[center_x - tamper_size // 2:center_x + tamper_size // 2, center_y - tamper_size // 2:center_y + tamper_size // 2]
    
    # Flip the LSB of each pixel in the region (toggle the last bit)
    tampered_region = tampered_region ^ 0x02  # XOR with 1 to flip the LSB

    # Replace the region in the original image with the LSB tampered region
    tampered_image[center_x - tamper_size // 2:center_x + tamper_size // 2, center_y - tamper_size // 2:center_y + tamper_size // 2] = tampered_region

    # Save the tampered image
    cv2.imwrite('tampered_image.png', tampered_image)

    print(f"LSB Tampered image created in {time() - start_time:.2f} seconds")

if __name__ == "__main__":
    tamper_image('test_image_Tge.png')
