import numpy as np
from hashlib import md5
from cryptography.fernet import Fernet
from PIL import Image, PngImagePlugin, ImageDraw
import json
import os
import argparse
from scipy.ndimage import median_filter
from scipy.ndimage import gaussian_filter
import time

# Helper function to extract metadata (encrypted JSON) from the image
def extract_metadata(image):
    metadata = image.info  # Access image metadata through the `.info` dictionary
    if "EncryptedConfig" in metadata:
        return metadata["EncryptedConfig"].encode('latin1')  # Return encoded binary data
    return None

# Function to decrypt the configuration data
def decrypt_config_data(encrypted_data, key):
    cipher_suite = Fernet(key)
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()  # Decrypt and convert to string
    config = json.loads(decrypted_data)  # Parse the JSON data
    return config

# Function to divide the image into blocks
def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0], block_size):
        for j in range(0, image.shape[1], block_size):
            block = image[i:i + block_size, j:j + block_size]
            if block.shape[0] == block_size and block.shape[1] == block_size:
                blocks.append(block)
                block_positions.append((i, j))
    return blocks, block_positions

# Function to calculate an MD5 hash and a parity bit for a block using 5 MSBs
def calculate_md5_and_parity(block, magic_square, block_index, block_size):
    hash_bits = (block_size * block_size * 2) - 1
    msb_block = (block & 0xF8) >> 3  # Get the MSB (5 bits)
    multiplied_block = msb_block * magic_square  # Multiply the block by the magic square
    block_flattened = multiplied_block.flatten()  # Flatten the block into 1D
    combined_string = ''.join(map(str, block_flattened)) + format(block_index, '08b')
    full_hash = md5(combined_string.encode('utf-8')).hexdigest()
    binary_full_hash = bin(int(full_hash, 16))[2:].zfill(128)  # Convert to binary and pad to 128 bits
    truncated_hash = binary_full_hash[:hash_bits]  # Get only the required number of bits
    parity_bit = str(binary_full_hash.count('1') % 2)
    return truncated_hash, parity_bit

# Helper function: Extract hash and parity from LSBs
def extract_hash_from_lsb(block, block_size):
    total_bits_needed = (block_size * block_size * 2) - 1  # Total bits for the hash (excluding parity)
    
    extracted_hash = []
    hash_index = 0

    # Extract 0th LSB for the first half
    for i in range(block_size):
        for j in range(block_size):
            if i == block_size - 1 and j == block_size - 1:
                continue  # Skip the last pixel (parity)
            extracted_hash.append((block[i, j] & 0x01))  # Extract 0th LSB
            hash_index += 1
            if hash_index >= total_bits_needed // 2:
                break

    # Extract 1st LSB for the second half
    for i in range(block_size):
        for j in range(block_size):
            extracted_hash.append((block[i, j] & 0x02) >> 1)  # Extract 1st LSB

    # Ensure the extracted hash is only 128 bits
    extracted_hash_str = ''.join(map(str, extracted_hash))

    # If the block size leads to more than 128 bits, trim to 128 bits
    if len(extracted_hash_str) > 128:
        extracted_hash_str = extracted_hash_str[:128]

    return extracted_hash_str

def extract_parity(block, block_size):
    return block[-1, -1] & 1  # Extract parity bit from the last pixel's 0th LSB

# Function to create a magic square
def create_magic_square(n, start_num=1):
    if n < 3:
        raise ValueError("Block size must be at least 3 to form a valid magic square.")
    if n % 2 == 1:
        return create_siamese_magic_square(n, start_num)
    elif n % 4 == 0:
        return create_doubly_even_magic_square(n, start_num)
    else:
        return create_singly_even_magic_square(n, start_num)

# Magic square generation functions (same as Person A)
def create_siamese_magic_square(n, start_num=1):
    magic_square = np.zeros((n, n), dtype=int)
    num = start_num
    i, j = 0, n // 2
    while num < start_num + n ** 2:
        magic_square[i, j] = num
        num += 1
        newi, newj = (i - 1) % n, (j + 1) % n
        if magic_square[newi, newj]:
            i += 1
        else:
            i, j = newi, newj
    return magic_square

def create_doubly_even_magic_square(n, start_num=1):
    magic_square = np.arange(start_num, start_num + n * n).reshape(n, n)
    indices = np.indices((n, n))
    r, c = indices[0], indices[1]
    mask = ((r % 4 == c % 4) | ((r % 4 + c % 4) == 3))
    magic_square[mask] = start_num + n * n - 1 - (magic_square[mask] - start_num)
    return magic_square

def create_singly_even_magic_square(n, start_num=1):
    half_n = n // 2
    half_magic_square = create_siamese_magic_square(half_n, start_num)
    magic_square = np.zeros((n, n), dtype=int)
    for i in range(4):
        r_offset = (i // 2) * half_n
        c_offset = (i % 2) * half_n
        if i == 0:
            magic_square[r_offset:r_offset + half_n, c_offset:c_offset + half_n] = half_magic_square
        elif i == 1:
            magic_square[r_offset:r_offset + half_n, c_offset:c_offset + half_n] = half_magic_square + 2 * half_n * half_n
        elif i == 2:
            magic_square[r_offset:r_offset + half_n, c_offset:c_offset + half_n] = half_magic_square + 3 * half_n * half_n
        elif i == 3:
            magic_square[r_offset:r_offset + half_n, c_offset:c_offset + half_n] = half_magic_square + half_n * half_n
    k = (n - 2) // 4
    for i in range(half_n):
        for j in range(k):
            if j == k - 1 and i == k:
                continue
            magic_square[i, j], magic_square[i + half_n, j] = magic_square[i + half_n, j], magic_square[i, j]
    for i in range(half_n):
        for j in range(n - k, n):
            magic_square[i, j], magic_square[i + half_n, j] = magic_square[i + half_n, j], magic_square[i, j]
    return magic_square

# Function to highlight tampered blocks by changing their pixel values
# def highlight_tampered_blocks(image, tampered_blocks, block_size):
#     highlight_block = 255  # Set the highlight color (e.g., white)
    
#     # Loop through each tampered block's position and highlight it
#     for position in tampered_blocks:
#         x, y = position  # Unpack the position tuple
#         # Highlight the block by setting its pixel values to the highlight color
#         image[x:x + block_size, y:y + block_size] = highlight_block
    
#     return image

# Function to highlight tampered blocks by changing their pixel values to green
def highlight_tampered_blocks(image, tampered_blocks, block_size):
    # Convert the grayscale image to RGB
    image_rgb = Image.fromarray(image).convert("RGB")
    image_array = np.array(image_rgb)

    highlight_color = [0, 255, 0]  # Green color (R, G, B)

    # Loop through each tampered block's position and highlight it with green
    for position in tampered_blocks:
        x, y = position  # Unpack the position tuple
        # Highlight the block by setting its pixel values to the highlight color
        image_array[x:x + block_size, y:y + block_size] = highlight_color

    return image_array


# Function to extract recovery data from the 2nd LSB
def extract_recovery_from_lsb(block):
    flat_block = block.flatten()
    recovery_bits = [(flat_block[i] & 0x04) >> 2 for i in range(flat_block.size)]  # Extract 2nd LSB
    block_size = block.shape[0]  # Assuming square blocks
    required_bits = block_size * block_size  # We need block_size^2 bits

    # Ensure we only return the necessary bits
    recovery_bits = recovery_bits[:required_bits]  # Trim or pad if needed

    recovery_data = ''.join(map(str, recovery_bits))  # Return as a string of bits
    return recovery_data

# Function to apply recovery data and restore tampered blocks
def apply_recovery_data(block, recovery_data, neighboring_blocks, tampered_flags, tamper_type):
    block_size = block.shape[0]  # Assuming the block is square
    recovered_block = block.copy()

    # Step 1: Use recovery bits if it's MSB tampering and recovery data is available
    if tamper_type == 'msb' and recovery_data is not None:
        recovery_bits = np.array([int(bit) for bit in recovery_data]).reshape(block_size, block_size)
        for i in range(block_size):
            for j in range(block_size):
                recovered_block[i, j] = (recovered_block[i, j] & 0xFB) | (recovery_bits[i, j] << 2)  # Restore 2nd LSB

    # Step 2: Recover tampered pixels using neighboring blocks with untampered-neighbor preference
    for i in range(1, block_size - 1):
        for j in range(1, block_size - 1):
            if tampered_flags[i, j]:  # If this pixel is flagged as tampered
                neighbors = []
                weights = []

                if neighboring_blocks['top'] is not None:
                    neighbors.append(neighboring_blocks['top'][-1, j])
                    weights.append(1 if not np.any(tampered_flags[0, :]) else 0.5)  # Prefer untampered top

                if neighboring_blocks['bottom'] is not None:
                    neighbors.append(neighboring_blocks['bottom'][0, j])
                    weights.append(1 if not np.any(tampered_flags[-1, :]) else 0.5)  # Prefer untampered bottom

                if neighboring_blocks['left'] is not None:
                    neighbors.append(neighboring_blocks['left'][i, -1])
                    weights.append(1 if not np.any(tampered_flags[:, 0]) else 0.5)  # Prefer untampered left

                if neighboring_blocks['right'] is not None:
                    neighbors.append(neighboring_blocks['right'][i, 0])
                    weights.append(1 if not np.any(tampered_flags[:, -1]) else 0.5)  # Prefer untampered right

                if neighbors:
                    # Perform weighted interpolation based on untampered neighbor preference
                    recovered_block[i, j] = np.average(neighbors, weights=weights)

    # Step 3: Recover edges using neighboring blocks if available
    if neighboring_blocks['top'] is not None:
        recovered_block[0, :] = neighboring_blocks['top'][-1, :]
    if neighboring_blocks['bottom'] is not None:
        recovered_block[-1, :] = neighboring_blocks['bottom'][0, :]
    if neighboring_blocks['left'] is not None:
        recovered_block[:, 0] = neighboring_blocks['left'][:, -1]
    if neighboring_blocks['right'] is not None:
        recovered_block[:, -1] = neighboring_blocks['right'][:, 0]

    return recovered_block

# Detect if the noise is Salt-and-Pepper based on the percentage of extreme pixel values (0 and 255)
def detect_salt_pepper_noise(tampered_image, threshold=0.004):  # Adjust threshold based on your tolerance
    pixel_counts = np.bincount(tampered_image.flatten(), minlength=256)
    total_pixels = tampered_image.size
    salt_pepper_pixels = pixel_counts[0] + pixel_counts[255]
    percentage_noise = (salt_pepper_pixels / total_pixels)
    return percentage_noise > threshold  # Returns True if salt-and-pepper noise is detected

# Detect if the noise is Gaussian based on the standard deviation of pixel differences
def detect_gaussian_noise(tampered_image, gaussian_threshold=5):  # Adjust based on your expected noise level
    pixel_std_dev = np.std(tampered_image)
    return pixel_std_dev > gaussian_threshold  # Returns True if Gaussian noise is detected based on pixel deviations

# Detect MSB tampering by comparing the higher bits (MSBs)
def detect_msb_tampering(block, extracted_hash, calculated_hash, extracted_parity, calculated_parity):
    return extracted_hash != calculated_hash or extracted_parity != calculated_parity

# Recover from salt-and-pepper noise using MSB recovery (ignore 2nd LSB)
def recover_salt_pepper(image, block_positions, block_size, blocks, block_positions_map):
    for position in block_positions:
        x, y = position
        block = image[x:x + block_size, y:y + block_size]

        # Step 1: Skip the median filter, directly use neighboring blocks for MSB recovery
        # No need for median_filter or recovery_data from 2nd LSBs in SnP recovery.

        # Step 2: Retrieve neighboring blocks if available
        neighboring_blocks = {
            'top': blocks[block_positions_map.get((x - block_size, y))] if block_positions_map.get((x - block_size, y)) else None,
            'bottom': blocks[block_positions_map.get((x + block_size, y))] if block_positions_map.get((x + block_size, y)) else None,
            'left': blocks[block_positions_map.get((x, y - block_size))] if block_positions_map.get((x, y - block_size)) else None,
            'right': blocks[block_positions_map.get((x, y + block_size))] if block_positions_map.get((x, y + block_size)) else None,
        }

        # Step 3: Apply MSB recovery using neighboring blocks without relying on 2nd LSB
        recovered_block = apply_recovery_data(block, None, neighboring_blocks)

        # Replace the original block with the recovered block
        image[x:x + block_size, y:y + block_size] = recovered_block

    return image

# Recover from Gaussian noise using MSB recovery (ignore 2nd LSB)
def recover_gaussian(image, block_positions, block_size, blocks, block_positions_map):
    for position in block_positions:
        x, y = position
        block = image[x:x + block_size, y:y + block_size]

        # Step 1: Skip the Gaussian filter, directly use neighboring blocks for MSB recovery

        # Step 2: Retrieve neighboring blocks if available
        neighboring_blocks = {
            'top': blocks[block_positions_map.get((x - block_size, y))] if block_positions_map.get((x - block_size, y)) else None,
            'bottom': blocks[block_positions_map.get((x + block_size, y))] if block_positions_map.get((x + block_size, y)) else None,
            'left': blocks[block_positions_map.get((x, y - block_size))] if block_positions_map.get((x, y - block_size)) else None,
            'right': blocks[block_positions_map.get((x, y + block_size))] if block_positions_map.get((x, y + block_size)) else None,
        }

        # Step 3: Apply MSB recovery using neighboring blocks without relying on 2nd LSB
        recovered_block = apply_recovery_data(block, None, neighboring_blocks)

        # Replace the original block with the recovered block
        image[x:x + block_size, y:y + block_size] = recovered_block

    return image

# Function to calculate the mean pixel value based on the MSBs (first 5 bits)
def calculate_msb_mean(block):
    msb_block = (block & 0xF8) >> 3  # Extract the first 5 bits (MSBs)
    mean_msb_value = np.mean(msb_block)  # Calculate the mean based on the MSBs
    return mean_msb_value

# Transformation function for Person B (same as Person A)
def transform_magic_square(original_magic_square, mean_value):
    # Define the transformations for each range of mean values
    if 0 <= mean_value < 32:
        # No transformation (Original)
        transformed_magic_square = np.copy(original_magic_square)
    elif 32 <= mean_value < 64:
        # Rotate 90 degrees
        transformed_magic_square = np.rot90(original_magic_square, k=-1)
    elif 64 <= mean_value < 96:
        # Rotate 180 degrees
        transformed_magic_square = np.rot90(original_magic_square, k=2)
    elif 96 <= mean_value < 128:
        # Rotate 270 degrees
        transformed_magic_square = np.rot90(original_magic_square, k=1)
    elif 128 <= mean_value < 160:
        # Horizontal reflection
        transformed_magic_square = np.fliplr(original_magic_square)
    elif 160 <= mean_value < 192:
        # Vertical reflection
        transformed_magic_square = np.flipud(original_magic_square)
    elif 192 <= mean_value < 224:
        # Diagonal reflection (Main Diagonal)
        transformed_magic_square = np.transpose(original_magic_square)
    elif 224 <= mean_value <= 255:
        # Diagonal reflection (Secondary Diagonal)
        transformed_magic_square = np.flipud(np.fliplr(np.transpose(original_magic_square)))
    else:
        # Default to original if out of range (should not happen)
        transformed_magic_square = np.copy(original_magic_square)

    return transformed_magic_square


# Main function for Person B
def main():
    parser = argparse.ArgumentParser(description="Verify the image integrity by comparing hashes and parity.")
    parser.add_argument('images_path', type=str, help="Path to the images directory")
    parser.add_argument('key_path', type=str, help="Path to the encryption key file")
    
    args = parser.parse_args()
    images_path = args.images_path
    key_path = args.key_path

    # Load the encryption key
    with open(key_path, "rb") as key_file:
        key = key_file.read()

    # Process all images in the images directory
    image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        print(f"No images found in {images_path}.")
        return
    
    # Initialize total image counter and the overall start time
    total_images = 0  # Counter for the number of processed images
    overall_start_time = time.time()  # Start the overall timer

    # Function to calculate the mean pixel value based on the MSBs (first 5 bits)
    def calculate_msb_mean(block):
        msb_block = (block & 0xF8) >> 3  # Extract the first 5 bits (MSBs)
        mean_msb_value = np.mean(msb_block)  # Calculate the mean based on the MSBs
        return mean_msb_value

    for image_file in image_files:
        image_path = os.path.join(images_path, image_file)
        print(f"\nProcessing {image_file}...")

        # Start the timer for this image
        total_start_time = time.time()  # Start timer for the current image

        # Load the processed image
        image = Image.open(image_path).convert('L')

        # Extract encrypted metadata from the image
        encrypted_data = extract_metadata(image)
        if not encrypted_data:
            print(f"No encrypted configuration data found in {image_file}. Skipping...")
            continue

        # Decrypt the configuration data
        config = decrypt_config_data(encrypted_data, key)

        block_size = config["block_size"]
        magic_constant = config["magic_constant"]

        # Recreate the magic square using the block size and magic constant
        magic_square = create_magic_square(block_size, start_num=1)  # Start num should match Person A's choice
        
        # Convert the image to NumPy array
        image = np.array(image)

        # Divide the image into blocks
        blocks, block_positions = divide_into_blocks(image, block_size)
        
        # Create a mapping for block positions
        block_positions_map = {(i, j): idx for idx, (i, j) in enumerate(block_positions)}

        # Initialize a list to store tampered blocks
        tampered_blocks = []
        tampered_types = []
        tampered_image = image.copy()  # Create a copy of the original image for tampering
        recovered_image = image.copy()  # Create a copy for recovery

        # Iterate over each block and verify hashes
        for i, (block, position) in enumerate(zip(blocks, block_positions)):
            # Step 1: Calculate the mean pixel value of the block based on the MSBs
            mean_value = calculate_msb_mean(block)
            print(f"Block {i} - Mean Pixel Value (MSBs): {mean_value}")

            # Step 2: Transform the magic square based on the MSB mean value
            transformed_magic_square = transform_magic_square(magic_square, mean_value)
            print(f"Block {i} - Transformed Magic Square:\n{transformed_magic_square}")

            # Step 3: Calculate the hash and parity using the transformed magic square
            calculated_hash, calculated_parity = calculate_md5_and_parity(block, transformed_magic_square, i, block_size)

            # Step 4: Extract the hash and parity from the block's LSBs
            extracted_hash = extract_hash_from_lsb(block, block_size)
            extracted_parity = extract_parity(block, block_size)

            # Compare the calculated hash and parity with the extracted ones
            if calculated_hash != extracted_hash or calculated_parity != str(extracted_parity):
                print(f"Calculated Hash: {calculated_hash}")
                print(f"Extracted Hash: {extracted_hash}")
                print(f"Calculated Parity: {calculated_parity}")
                print(f"Extracted Parity: {extracted_parity}")
                print(f"Block {i} at position {position} is tampered.")

                # Now detect what kind of tampering occurred: MSB, Salt-and-Pepper, or Gaussian
                if detect_msb_tampering(block, extracted_hash, calculated_hash, extracted_parity, calculated_parity):
                    print(f"MSB Tampering detected in block {i}.")
                    tampered_blocks.append(position)
                    tampered_types.append('msb')
                
                elif detect_salt_pepper_noise(block):
                    print(f"Salt-and-Pepper Noise detected in block {i}.")
                    tampered_blocks.append(position)
                    tampered_types.append('salt_pepper')
                
                elif detect_gaussian_noise(block):
                    print(f"Gaussian Noise detected in block {i}.")
                    tampered_blocks.append(position)
                    tampered_types.append('gaussian')

        # Highlight and save the tampered image
        if tampered_blocks:
            # Highlight the tampered blocks (just for visualization, not used for recovery)
            highlighted_image = highlight_tampered_blocks(tampered_image.copy(), tampered_blocks, block_size)
            
            # Save the highlighted image before recovery
            highlighted_image_pil = Image.fromarray(highlighted_image)
            highlighted_image_path = os.path.join(images_path, "highlighted_" + image_file)
            highlighted_image_pil.save(highlighted_image_path)
            print(f"Highlighted image saved as: highlighted_{image_file}")
            
            # Now ask the user if they want to recover the tampered blocks
            recover_choice = input("Do you want to attempt to recover the tampered blocks? (yes/no): ").lower()
            if recover_choice == 'yes':
                for position, tamper_type in zip(tampered_blocks, tampered_types):
                    x, y = position
                    block = blocks[block_positions.index(position)]  # Retrieve the tampered block

                    # Retrieve neighboring blocks (ensure they exist, otherwise handle edges properly)
                    neighboring_blocks = {
                        'top': blocks[block_positions_map.get((x - block_size, y))] if block_positions_map.get((x - block_size, y)) else None,
                        'bottom': blocks[block_positions_map.get((x + block_size, y))] if block_positions_map.get((x + block_size, y)) else None,
                        'left': blocks[block_positions_map.get((x, y - block_size))] if block_positions_map.get((x, y - block_size)) else None,
                        'right': blocks[block_positions_map.get((x, y + block_size))] if block_positions_map.get((x, y + block_size)) else None,
                    }

                    tampered_flags = np.ones((block_size, block_size), dtype=bool)  # All pixels flagged for simplicity

                    if tamper_type == 'msb':
                        # Extract recovery data from the 2nd LSB (for MSB tampering)
                        recovery_data = extract_recovery_from_lsb(block)
                        recovered_block = apply_recovery_data(block, recovery_data, neighboring_blocks, tampered_flags, 'msb')
                    else:
                        # For Salt-and-Pepper or Gaussian tampering, we skip 2nd LSB and use block-based recovery
                        recovered_block = apply_recovery_data(block, None, neighboring_blocks, tampered_flags, tamper_type)

                    recovered_image[x:x + block_size, y:y + block_size] = recovered_block

                # Save the recovered image
                recovered_image_pil = Image.fromarray(recovered_image)
                recovered_image_pil.save(os.path.join(images_path, "recovered_" + image_file))
                print(f"Recovered image saved as: recovered_{image_file}")

        else:
            print(f"{image_file} is not tampered. All blocks are intact.")

        # Finish processing this image and calculate time
        total_end_time = time.time()
        image_processing_time = total_end_time - total_start_time  # Time taken for the current image
        print(f"Time taken to process {image_file}: {image_processing_time:.6f} seconds")
        total_images += 1  # Increment the image counter

    # Overall time after all images processed
    overall_end_time = time.time()
    total_processing_time = overall_end_time - overall_start_time

    print(f"\nTotal time taken for processing all images is: {total_processing_time:.6f} seconds")
    print(f"Total number of images processed: {total_images}")
    if total_images > 0:
        print(f"Average processing time per image: {total_processing_time / total_images:.6f} seconds")
    else:
        print("No images were processed.")


if __name__ == "__main__":
    main()
