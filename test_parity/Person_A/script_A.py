import numpy as np
from hashlib import md5
from cryptography.fernet import Fernet
from PIL import Image, PngImagePlugin
import argparse
import json
import os
import time

# Function to divide the image into blocks and keep track of block positions
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

# Ensure every pixel is represented in 8-bit binary
def convert_to_8bit(pixel_value):
    return format(pixel_value, '08b')

# Convert 8-bit binary string to integer
def convert_to_int(binary_str):
    return int(binary_str, 2)

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

# Function to generate differential recovery data
def generate_recovery_data(original_block, block_size):
    print(f"Block size: {block_size}, type: {type(block_size)}")  # Debugging output
    
    num_bits = block_size * block_size  # Total number of bits for the block

    msb_original_block = (original_block & 0xF8) >> 3  # Extract upper 5 bits
    diff = msb_original_block  # Placeholder for your recovery logic
    
    recovery_bits = ''.join(format(pixel, '01b') for pixel in diff.flatten())  # 1 bit per pixel

    return recovery_bits[:num_bits]  # Return exactly n*n bits


# Function to clear 0th and 1st LSBs
def clear_lsb(block, block_size):
    for i in range(block_size):
        for j in range(block_size):
            block[i, j] = block[i, j] & 0xFC  # Clears both 0th and 1st LSBs (set them to 0)
    return block

# Embed hash data while ensuring the 0th and 1st LSBs are cleared first
def embed_hash_in_lsb(block, hash_data, parity_bit, block_size):
    # Step 1: Clear all 0th and 1st LSBs before embedding
    block = clear_lsb(block, block_size)
    
    hash_index = 0
    total_bits = (block_size * block_size * 2) - 1  # Total bits for the hash (excluding parity)

    # Step 2: Embed the hash into the 0th LSBs (hash_data[0:block_size * block_size - 1])
    for i in range(block_size):
        for j in range(block_size):
            if i == block_size - 1 and j == block_size - 1:
                continue  # Skip the last pixel for parity
            if hash_index < len(hash_data):  # Ensure we don't go out of bounds
                block[i, j] = (block[i, j] & 0xFE) | int(hash_data[hash_index])  # Embed in the 0th LSB
                hash_index += 1

    # Step 3: Embed the hash into the 1st LSBs (hash_data[block_size * block_size:])
    for i in range(block_size):
        for j in range(block_size):
            if hash_index < len(hash_data):  # Ensure we don't go out of bounds
                block[i, j] = (block[i, j] & 0xFD) | (int(hash_data[hash_index]) << 1)  # Embed in the 1st LSB
                hash_index += 1

    # Step 4: Embed the parity bit in the last pixel's 0th LSB
    block[-1, -1] = (block[-1, -1] & 0xFE) | int(parity_bit)

    return block

# Function to embed recovery data in the 2nd LSB
def embed_recovery_in_lsb(block, recovery_data):
    flat_block = block.flatten()
    total_bits = len(recovery_data)
    for i in range(min(total_bits, len(flat_block))):
        flat_block[i] = (flat_block[i] & 0xF8) | (int(recovery_data[i]) << 2)  # Set only the 2nd LSB, preserve MSBs
    return flat_block.reshape(block.shape)

# Function to encrypt configuration data
def encrypt_config_data(config, key):
    config_json = json.dumps(config)
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(config_json.encode())  # Directly encrypt the JSON string
    return encrypted_data  # Return the encrypted binary data

# Function to embed encrypted data in PNG text chunks
def embed_data_in_png(image, encrypted_data, output_image_path):
    encrypted_string = encrypted_data.decode('latin1')  # Convert binary data to a string
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("EncryptedConfig", encrypted_string)
    image.save(output_image_path, "PNG", pnginfo=metadata)
    print(f"Image saved with embedded config in PNG text chunk: {output_image_path}")

# Function to suggest valid block sizes that do not require padding (limited to 3 to 10)
def suggest_valid_block_sizes(image):
    height, width = image.shape
    valid_block_sizes = []
    # A block size is valid if it divides both the width and height without remainder and is between 3 and 10
    for i in range(3, 11):  # Limiting the block size suggestions from 3 to 10
        if height % i == 0 and width % i == 0:
            valid_block_sizes.append(i)
    return valid_block_sizes

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

# Magic square generation functions
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

def generate_possible_magic_numbers(n, start_nums):
    magic_numbers = []
    for start_num in start_nums:
        magic_square = create_magic_square(n, start_num)
        magic_number = np.sum(magic_square[0])
        magic_numbers.append(magic_number)
    return magic_numbers

def get_positive_integer(prompt):
    while True:
        try:
            value = int(input(prompt))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Invalid input. Please enter a positive integer.")

# Function to convert NumPy data types to standard Python types
def convert_numpy_types(data):
    if isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()  # Convert NumPy arrays to lists
    elif isinstance(data, dict):
        return {key: convert_numpy_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_types(item) for item in data]
    return data

# Function to encrypt configuration data
def encrypt_config_data(config, key):
    # Convert NumPy types to native Python types before encryption
    config = convert_numpy_types(config)
    config_json = json.dumps(config)
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(config_json.encode())  # Directly encrypt the JSON string
    return encrypted_data  # Return the encrypted binary data

# Helper function: Extract 0th and 1st LSB for hash and parity extraction
def extract_0th_lsb(block):
    flat_block = block.flatten()
    return [flat_block[i] & 1 for i in range(flat_block.size)]

def extract_1st_lsb(block, block_size):
    extracted_hash_1st = []
    total_bits_needed = (block_size * block_size * 2) - 1  # Total bits for the hash (excluding parity)

    # Second half: Extract bits from 1st LSB
    print("Extracting 1st LSB:")
    for i in range(block_size):
        for j in range(block_size):
            if len(extracted_hash_1st) < total_bits_needed // 2:  # Second half from 1st LSB
                pixel = block[i, j]
                # Convert the pixel to a full 8-bit binary string
                full_pixel = convert_to_8bit(pixel)  
                bit_value = int(full_pixel[-2])  # Extract the 1st LSB, which is the second-to-last bit
                extracted_hash_1st.append(bit_value)
                print(f"Pixel ({i},{j}) - Original: {full_pixel}, 1st LSB: {bit_value}")
    
    return ''.join(map(str, extracted_hash_1st))

def extract_parity(block, block_size):
    flat_block = block.flatten()
    return flat_block[block_size * block_size - 1] & 1  # Extract parity bit from the last pixel

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

# Calculate the mean pixel value based on the MSBs (first 5 bits) only
def calculate_msb_mean(block):
    msb_block = (block & 0xF8) >> 3  # Extract the first 5 bits (MSB)
    mean_msb_value = np.mean(msb_block)  # Calculate the mean based on the MSBs
    return mean_msb_value

# Transformation function based on mean pixel value (similar to Script B)
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

# Main function to handle user inputs and process the images
def main():
    parser = argparse.ArgumentParser(description="Process images and generate block hashes.")
    parser.add_argument('images_path', type=str, help="Directory containing the input images or a single image file")
    args = parser.parse_args()
    images_path = args.images_path

    key_filename = "encryption_key.txt"
    key_path = os.path.join("key", key_filename)

    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as key_file:
            key_file.write(key)
    else:
        with open(key_path, "rb") as key_file:
            key = key_file.read()

    if os.path.isdir(images_path):
        image_files = [os.path.join(images_path, f) for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    else:
        image_files = [images_path]

    processed_dir = "processed_images"
    os.makedirs(processed_dir, exist_ok=True)

    total_images = 0
    overall_start_time = time.time()

    for image_filename in image_files:
        image_path = image_filename
        print(f"\nProcessing for the image --> {os.path.basename(image_filename)}.")
        total_images += 1
        total_start_time = time.time()
        image = Image.open(image_path).convert('L')
        image = np.array(image)

        # Suggest valid block sizes between 3 and 10
        valid_block_sizes = suggest_valid_block_sizes(image)
        print(f"Suggested block sizes for this image: {valid_block_sizes}")

        if not valid_block_sizes:
            print("No valid block sizes between 3 and 10 for this image.")
            continue

        while True:
            block_size = get_positive_integer("Enter the block size from the suggestions: ")
            if block_size in valid_block_sizes:
                break
            else:
                print(f"Invalid block size. Please choose from {valid_block_sizes}")

        magic_square = create_magic_square(block_size, 1)
        blocks, block_positions = divide_into_blocks(image, block_size)
        bits_per_layer = block_size * block_size

        config = {"block_size": block_size, "magic_constant": sum(magic_square[0])}

        for i, (block, position) in enumerate(zip(blocks, block_positions)):
            
            # Step 1: Calculate the mean pixel value from the MSBs
            mean_value = calculate_msb_mean(block)
            
            # Step 2: Transform the magic square based on the MSB mean value
            transformed_magic_square = transform_magic_square(magic_square, mean_value)
            
            # Step 3: Generate hash and parity using the transformed magic square
            truncated_hash, parity_bit = calculate_md5_and_parity(block, transformed_magic_square, i, block_size)
            
            # Debug: Print the generated hash and parity
            print(f"Person A - Block {i} - Generated Hash: {truncated_hash}, Parity: {parity_bit}")
            
            # Step 4: Embed the hash and parity into the block
            block = embed_hash_in_lsb(block, truncated_hash, parity_bit, block_size)
            
            # Debug: Print the embedded hash and parity (same as generated since we're embedding them)
            print(f"Person A - Block {i} - Embedded Hash: {truncated_hash}, Parity: {parity_bit}")
            
            # Step 5: Extract the hash and parity from the block (after embedding)
            embedded_hash = extract_hash_from_lsb(block, block_size)
            extracted_parity = extract_parity(block, block_size)
            
            # Debug: Print the extracted hash and parity
            print(f"Person A - Block {i} - Extracted Hash: {embedded_hash}, Parity: {extracted_parity}")

            # Step 6: Generate recovery data
            recovery_data = generate_recovery_data(block, block_size)

            # Debug: Print recovery data
            print(f"Person A - Block {i} - Generated Recovery Data: {recovery_data}")
            
            # Step 7: Embed the recovery data into the 2nd LSB
            block = embed_recovery_in_lsb(block, recovery_data)

            # Continue with the rest of the process...

        encrypted_data = encrypt_config_data(config, key)

        # Prepare output image path with the same filename but with a .png extension in the processed_images directory
        output_image_filename = os.path.splitext(os.path.basename(image_filename))[0] + ".png"
        output_image_path = os.path.join(processed_dir, output_image_filename)

        # Save the image with the encrypted config data embedded in the metadata
        image_with_exif = Image.fromarray(image)
        embed_data_in_png(image_with_exif, encrypted_data, output_image_path)

        total_end_time = time.time()

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
