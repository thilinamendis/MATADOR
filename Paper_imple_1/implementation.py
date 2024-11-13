# import cv2
# import numpy as np
# import matplotlib.pyplot as plt
# from scipy.fftpack import dct, idct
# import os

# # Function to divide the image into macro blocks (24x24)
# def divide_into_macro_blocks(image, block_size=24):
#     macro_blocks = []
#     positions = []
#     height, width = image.shape
#     for i in range(0, height, block_size):
#         for j in range(0, width, block_size):
#             macro_block = image[i:i+block_size, j:j+block_size]
#             if macro_block.shape[0] == block_size and macro_block.shape[1] == block_size:
#                 macro_blocks.append(macro_block)
#                 positions.append((i, j))
#     return macro_blocks, positions

# # Perform DCT on each block
# def perform_dct(block):
#     return dct(dct(block.T, norm='ortho').T, norm='ortho')

# # Calculate relative difference between actual and estimated AC coefficients
# def calculate_relative_difference(actual_ac, estimated_ac):
#     alpha = 0.05  # Parameter for tuning tolerance
#     delta_0 = 150  # Parameter for tuning tolerance
#     rho = 0.005  # Parameter for adjacent block coupling


#     # Ensure this operation is element-wise
#     delta = (1 + np.round(alpha * (np.abs(actual_ac) + rho * np.abs(estimated_ac)))) * delta_0

#     relative_diff = np.abs(actual_ac - estimated_ac) / (np.abs(estimated_ac) + delta)

#     return relative_diff


# # Check if tampering has occurred by comparing the relative difference with the threshold
# def check_tampering(actual_ac, estimated_ac, threshold):
#     rel_diff = calculate_relative_difference(actual_ac, estimated_ac)
    
#     # Use np.any() to handle array comparisons correctly
#     return np.any(rel_diff > threshold)


# # Process macro blocks to detect tampering
# def process_macro_blocks(image, tampering_threshold=0.4):
#     macro_blocks, positions = divide_into_macro_blocks(image)
#     tampered_flags = []
    
#     for block in macro_blocks:
#         central_block = block[8:16, 8:16]  # Central 8x8 block of a 24x24 macro block
#         neighbors = []

#         # Handle boundary conditions by only adding valid neighbors
#         if block.shape == (24, 24):
#             neighbors = [
#                 block[:8, :8],   # Top-left
#                 block[:8, 8:],   # Top-right
#                 block[8:, :8],   # Bottom-left
#                 block[8:, 8:]    # Bottom-right
#             ]

#         # Perform DCT on central and neighboring blocks
#         dct_central = perform_dct(central_block)
#         dct_neighbors = [perform_dct(neighbor) for neighbor in neighbors if neighbor.shape == (8, 8)]
        
#         # Only compute mean if we have valid neighboring blocks
#         if dct_neighbors:
#             estimated_dct = np.mean(dct_neighbors, axis=0)
#         else:
#             estimated_dct = dct_central  # If no valid neighbors, fallback to the central DCT

#         # Check tampering for AC coefficients
#         tampering_flags = check_tampering(dct_central, estimated_dct, tampering_threshold)
#         tampered_flags.append(tampering_flags)
    
#     return tampered_flags, positions


# # Highlight tampered blocks
# def highlight_tampered_blocks(image, tampered_blocks, positions, block_size=24):
#     highlighted_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Convert to color to add colored borders
#     for i, tampered in enumerate(tampered_blocks):
#         if tampered:
#             x, y = positions[i]
#             cv2.rectangle(highlighted_image, (y, x), (y + block_size, x + block_size), (0, 255, 0), 2)  # Green border for tampered blocks
#     return highlighted_image

# # Main tamper detection function
# def tamper_detection(image_path, tampering_threshold=0.4):
#     # Load and preprocess the image
#     image = cv2.imread(image_path)
#     if image is None:
#         print(f"Error: Could not load image at {image_path}.")
#         return

#     print("Converting to YUV format...")
#     yuv_image = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
#     y_channel = yuv_image[:, :, 0]  # Extract Y channel

#     # Detect tampered blocks
#     tampered_blocks, positions = process_macro_blocks(y_channel, tampering_threshold)
#     print(f"Characteristic data generated for the image.")

#     # Highlight tampered blocks
#     highlighted_image = highlight_tampered_blocks(y_channel, tampered_blocks, positions)

#     # Save the highlighted image
#     highlighted_image_path = "highlighted_tampered_image.png"
#     cv2.imwrite(highlighted_image_path, highlighted_image)
#     print(f"Highlighted image saved as: {highlighted_image_path}")

# # Test with an image
# def main():
#     image_path = 'test12.jpg'  # Replace with your image path
#     if not os.path.exists(image_path):
#         print(f"Error: Image path '{image_path}' does not exist. Please check the path.")
#     else:
#         tamper_detection(image_path, tampering_threshold=0.4)

# if __name__ == "__main__":
#     main()


import cv2
import numpy as np
from scipy.fftpack import dct, idct
import os

# Function to divide the image into macro blocks (24x24)
def divide_into_macro_blocks(image, block_size=24):
    macro_blocks = []
    positions = []
    height, width = image.shape
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            macro_block = image[i:i + block_size, j:j + block_size]
            if macro_block.shape[0] == block_size and macro_block.shape[1] == block_size:
                macro_blocks.append(macro_block)
                positions.append((i, j))
    return macro_blocks, positions

# Perform DCT on each block
def perform_dct(block):
    return dct(dct(block.T, norm='ortho').T, norm='ortho')

# Calculate relative difference between actual and estimated AC coefficients
def calculate_relative_difference(actual_ac, estimated_ac, alpha=0.05, delta_0=150, rho=0.005):
    delta = (1 + np.round(alpha * (np.abs(actual_ac) + rho * np.abs(estimated_ac)))) * delta_0
    relative_diff = np.abs(actual_ac - estimated_ac) / (np.abs(estimated_ac) + delta)
    return relative_diff

# Check if tampering has occurred by comparing the relative difference with the threshold
def check_tampering(actual_ac, estimated_ac, threshold):
    rel_diff = calculate_relative_difference(actual_ac, estimated_ac)
    return np.any(rel_diff > threshold)

# Pad the image to ensure divisibility by the block size
def pad_image(image, block_size=4):
    height, width = image.shape
    pad_height = block_size - (height % block_size) if height % block_size != 0 else 0
    pad_width = block_size - (width % block_size) if width % block_size != 0 else 0
    return np.pad(image, ((0, pad_height), (0, pad_width)), mode='constant', constant_values=0)

# Process macro blocks to detect tampering
def process_macro_blocks(image, tampering_threshold=0.4):
    image = pad_image(image)  # Ensure image is divisible by block size
    macro_blocks, positions = divide_into_macro_blocks(image)
    tampered_flags = []
    
    for i, block in enumerate(macro_blocks):
        central_block = block[8:16, 8:16]  # Central 8x8 block of a 24x24 macro block
        neighbors = []

        # Collect all neighboring blocks (top-left, top-right, bottom-left, bottom-right)
        if block.shape == (24, 24):
            neighbors = [
                block[:8, :8],   # Top-left
                block[:8, 8:],   # Top-right
                block[16:, :8],  # Bottom-left
                block[16:, 8:]   # Bottom-right
            ]

        # Perform DCT on central and neighboring blocks
        dct_central = perform_dct(central_block)
        dct_neighbors = [perform_dct(neighbor) for neighbor in neighbors if neighbor.shape == (8, 8)]
        
        # Estimate DCT from neighbors (take the average)
        estimated_dct = np.mean(dct_neighbors, axis=0) if dct_neighbors else dct_central

        # Check tampering for AC coefficients
        tampering_flags = check_tampering(dct_central[1:, 1:], estimated_dct[1:, 1:], tampering_threshold)
        tampered_flags.append(tampering_flags)

        # Debugging: print tampering information
        if tampering_flags:
            print(f"Block {i} is flagged as tampered.")
    
    return tampered_flags, positions

# Highlight tampered blocks
def highlight_tampered_blocks(image, tampered_blocks, positions, block_size=24):
    highlighted_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Convert to color to add colored borders
    for i, tampered in enumerate(tampered_blocks):
        if tampered:
            x, y = positions[i]
            cv2.rectangle(highlighted_image, (y, x), (y + block_size, x + block_size), (0, 255, 0), 2)  # Green border for tampered blocks
    return highlighted_image

# Main tamper detection function
def tamper_detection(image_path, tampering_threshold=0.4):
    # Load and preprocess the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image at {image_path}.")
        return

    print("Converting to YUV format...")
    yuv_image = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    y_channel = yuv_image[:, :, 0]  # Extract Y channel

    # Detect tampered blocks
    tampered_blocks, positions = process_macro_blocks(y_channel, tampering_threshold)
    print(f"Characteristic data generated for the image.")

    # Highlight tampered blocks
    highlighted_image = highlight_tampered_blocks(y_channel, tampered_blocks, positions)

    # Save the highlighted image
    highlighted_image_path = "highlighted_tampered_image.png"
    cv2.imwrite(highlighted_image_path, highlighted_image)
    print(f"Highlighted image saved as: {highlighted_image_path}")

# Test with an image
def main():
    image_path = 'tampered_image.png'  # Replace with your image path Untitled_de_1.jpeg test_image_1.jpeg
    if not os.path.exists(image_path):
        print(f"Error: Image path '{image_path}' does not exist. Please check the path.")
    else:
        tamper_detection(image_path, tampering_threshold=0.1)  # Adjust threshold dynamically for better detection

if __name__ == "__main__":
    main()
