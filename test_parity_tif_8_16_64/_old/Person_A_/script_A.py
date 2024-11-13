import numpy as np
from hashlib import md5
from cryptography.fernet import Fernet
from PIL import Image, PngImagePlugin
import argparse
import json
import os
import time
import random

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

# Function to calculate an MD5 hash and a parity bit for a block using 5 MSBs
def calculate_md5_and_parity(block, magic_square, block_index, hash_bits):
    # Use the top 5 bits (4 MSBs + 5th bit) of each pixel for the hash calculation
    msb_block = (block & 0xF8) >> 3  # Extract the upper 5 bits (MSBs and 5th bit)
    multiplied_block = msb_block * magic_square
    block_flattened = multiplied_block.flatten()

    # Combine block data and block index for hashing
    combined_string = ''.join(map(str, block_flattened)) + format(block_index, '08b')

    # Generate the full MD5 hash
    full_hash = md5(combined_string.encode('utf-8')).hexdigest()

    # Convert to binary and truncate to the desired number of bits
    binary_full_hash = bin(int(full_hash, 16))[2:].zfill(128)
    truncated_hash = binary_full_hash[:hash_bits]

    # Calculate parity bit by counting '1's in the binary hash
    parity_bit = str(binary_full_hash.count('1') % 2)

    return truncated_hash, parity_bit


# Function to generate differential recovery data
def generate_recovery_data(original_block, magic_square, num_bits):
    msb_original_block = (original_block & 0xF8) >> 3  # Extract the upper 5 bits (MSBs + 5th bit)
    transformed_block = msb_original_block * magic_square
    diff = msb_original_block - transformed_block
    diff_flattened = diff.flatten()

    # Encode each difference as signed 8-bit binary
    recovery_bits = ''.join(format((pixel % 256), '08b') for pixel in diff_flattened)[:num_bits]
    return recovery_bits

# Embed hash data while preserving the parity bit location
def embed_hash_in_lsb(block, hash_data, parity_bit, block_size):
    total_lsb_bits = block_size * block_size  # Total pixels in the block
    hash_index = 0

    # Embed the first 8 bits of the hash into the 0th LSB
    for i in range(8):  # First 8 bits into 0th LSB
        block[i // block_size, i % block_size] = (block[i // block_size, i % block_size] & 0xFE) | int(hash_data[hash_index])
        hash_index += 1

    # Embed the remaining 9 bits into the 1st LSB
    for i in range(9):  # Next 9 bits into 1st LSB
        block[i // block_size, i % block_size] = (block[i // block_size, i % block_size] & 0xFD) | (int(hash_data[hash_index]) << 1)
        hash_index += 1

    # Set the parity bit in the last pixel
    block[-1, -1] = (block[-1, -1] & 0xFE) | int(parity_bit)

    return block



def embed_recovery_in_lsb(block, recovery_data):
    flat_block = block.flatten()
    total_bits = len(recovery_data)

    # Embed recovery data in the 2nd LSB
    for i in range(min(total_bits, len(flat_block))):
        flat_block[i] = (flat_block[i] & 0xF8) | (int(recovery_data[i]) << 2)  # Set only the 2nd LSB, preserve MSBs
    return flat_block.reshape(block.shape)

# Function to set a single bit in the LSB of the last pixel for parity or metadata
def set_single_lsb(block, bit, layer, index):
    flat_block = block.flatten()
    flat_block[index] = (flat_block[index] & ~(1 << layer)) | (int(bit) << layer)
    return flat_block.reshape(block.shape)

# Function to encrypt configuration data
def encrypt_config_data(config, key):
    config_json = json.dumps(config)
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(config_json.encode())  # Directly encrypt the JSON string
    return encrypted_data  # Return the encrypted binary data

# Function to embed encrypted data in PNG text chunks
def embed_data_in_png(image, encrypted_data, output_image_path):
    # Convert encrypted binary data to string format (we'll store it in PNG text chunks)
    encrypted_string = encrypted_data.decode('latin1')  # Convert binary data to a string

    # Create a PNG metadata object and add the encrypted config data as a tEXt chunk
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("EncryptedConfig", encrypted_string)

    # Save the image with the new metadata in the provided output path
    image.save(output_image_path, "PNG", pnginfo=metadata)
    print(f"Image saved with embedded config in PNG text chunk: {output_image_path}")

# Function to add padding to the image if its dimensions are not multiples of the block size
def add_padding(image, block_size):
    h, w = image.shape
    new_h = (h + block_size - 1) // block_size * block_size
    new_w = (w + block_size - 1) // block_size * block_size
    padded_image = np.zeros((new_h, new_w), dtype=image.dtype)
    padded_image[:h, :w] = image
    return padded_image

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

# Magic square generation functions remain the same as before
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

    # Position smaller squares in quadrants
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

    # Swap values to make it magic
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


# Helper function: Extract 0th LSB from a block
def extract_0th_lsb(block):
    flat_block = block.flatten()
    return [flat_block[i] & 1 for i in range(flat_block.size)]

# Helper function: Extract 1st LSB from a block
def extract_1st_lsb(block):
    flat_block = block.flatten()
    return [(flat_block[i] & 2) >> 1 for i in range(flat_block.size)]

# Helper function: Extract hash from LSBs of the block
def extract_hash_from_lsb(block, block_size):
    flat_block = block.flatten()
    extracted_hash = []

    # Step 1: Extract the first 8 bits from the 0th LSB
    for i in range(8):
        extracted_hash.append((flat_block[i] & 1))  # Extract 0th LSB
        print(f"Extracted bit from pixel {i} (0th LSB): {(flat_block[i] & 1)}")

    # Step 2: Extract the next 9 bits from the 1st LSB
    for i in range(9):
        extracted_hash.append((flat_block[i] & 2) >> 1)  # Extract 1st LSB
        print(f"Extracted bit from pixel {i} (1st LSB): {(flat_block[i] & 2) >> 1}")

    return ''.join(map(str, extracted_hash))  # Return all 17 bits


# Main function to handle user inputs and process the images
def main():
    parser = argparse.ArgumentParser(description="Process images and generate block hashes.")
    parser.add_argument('images_path', type=str, help="Directory containing the input images or a single image file")

    args = parser.parse_args()
    images_path = args.images_path

    while True:
        block_size = get_positive_integer("Enter the block size (positive integer, at least 3): ")
        if block_size >= 3:
            break

    start_nums = list(range(1, 12))
    possible_magic_numbers = generate_possible_magic_numbers(block_size, start_nums)
    print(f"Suggested magic numbers for a {block_size}x{block_size} grid: {possible_magic_numbers}")

    while True:
        try:
            magic_number = get_positive_integer("Enter the magic number: ")
            if magic_number not in possible_magic_numbers:
                raise ValueError(f"Magic number must be one of: {possible_magic_numbers}")
            break
        except ValueError as e:
            print(f"Error: {e}")

    start_num_index = possible_magic_numbers.index(magic_number)
    start_num = start_nums[start_num_index]

    config = {"block_size": block_size, "magic_constant": magic_number, "start_num": start_num}

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

    # Specify the directory for saving processed images
    processed_dir = "processed_images"
    os.makedirs(processed_dir, exist_ok=True)

    total_images = 0
    overall_start_time = time.time()

    num_debug_blocks = 5  # Number of blocks to debug

    for image_filename in image_files:
        image_path = image_filename

        print("\n" + "=" * 50)
        print(f"\nProcessing for the image --> {os.path.basename(image_filename)}.")
        print("\n" + "=" * 50)
        total_images += 1
        total_start_time = time.time()
        start_time = time.time()
        image = Image.open(image_path).convert('L')
        image = np.array(image)
        if image.shape[0] % block_size != 0 or image.shape[1] % block_size != 0:
            print(f"Image dimensions of {os.path.basename(image_filename)} are not multiples of the block size. Adding padding...")
            image = add_padding(image, block_size)
        end_time = time.time()

        print(f"Image dimensions: {image.shape}")
        print(f"Block size: {block_size}")
        print(f"Time taken to load and pad image: {end_time - start_time:.6f} seconds")

        start_time = time.time()
        magic_square = create_magic_square(block_size, start_num)
        end_time = time.time()
        print(f"\nMagic Square:\n{magic_square}")
        print(f"Time taken to create magic square: {end_time - start_time:.6f} seconds")

        start_time = time.time()
        blocks, block_positions = divide_into_blocks(image, block_size)
        end_time = time.time()
        print(f"\nNumber of blocks: {len(blocks)}")
        print(f"Time taken to divide image into blocks: {end_time - start_time:.6f} seconds")

        bits_per_layer = block_size * block_size

        # Inside the main loop for blocks (in Script A):
        # Example inside the main loop for blocks (in Script A):
        debug_blocks = [41, 3, 25,12,56]  # Blocks to debug

        # Inside the main loop for blocks (in Script A)
        for i, (block, position) in enumerate(zip(blocks, block_positions)):
            if i in debug_blocks:
                print(f"\n--- Debugging Block {i} at Position {position} ---")

                # Step 1: MSB Preservation Debugging
                msb_before_embedding = block & 0xF8  # Keep only MSBs (first 5 bits)
                print(f"MSBs before embedding for Block {i}: \n{msb_before_embedding}")

                # Generate the truncated hash and parity bit
                hash_bits_needed = 17  # For 3x3 block
                truncated_hash, parity_bit = calculate_md5_and_parity(block, magic_square, i, hash_bits_needed)
                print(f"Truncated hash: {truncated_hash}, Parity bit: {parity_bit}")

                # 0th LSB before embedding
                zero_lsb_before_embedding = extract_0th_lsb(block)
                print(f"0th LSB values BEFORE embedding for Block {i}: {zero_lsb_before_embedding}")

                # Before embedding the hash
                print(f"0th LSB values BEFORE embedding hash for Block {i}: {extract_0th_lsb(block)}")

                # After embedding the hash but before parity
                print(f"0th LSB values AFTER embedding hash and BEFORE parity for Block {i}: {extract_0th_lsb(block)}")

                # After embedding parity
                print(f"0th LSB values AFTER embedding parity for Block {i}: {extract_0th_lsb(block)}")


                # Embed hash and parity in the LSBs
                block = embed_hash_in_lsb(block, truncated_hash, parity_bit, block_size)

                # 0th LSB after embedding
                zero_lsb_after_embedding = extract_0th_lsb(block)
                print(f"0th LSB values AFTER embedding for Block {i}: {zero_lsb_after_embedding}")

                # 1st LSB after embedding
                first_lsb_after_embedding = extract_1st_lsb(block)
                print(f"1st LSB values AFTER embedding for Block {i}: {first_lsb_after_embedding}")

                # MSBs after embedding
                msb_after_embedding = block & 0xF8
                print(f"MSBs after embedding for Block {i}: \n{msb_after_embedding}")
                if np.array_equal(msb_before_embedding, msb_after_embedding):
                    print(f"MSBs are preserved for Block {i}.")
                else:
                    print(f"MSBs have changed for Block {i}. There may be an issue.")

                # Extract hash from LSBs
                extracted_hash = extract_hash_from_lsb(block, block_size)
                print(f"Extracted hash from LSBs for Block {i}: {extracted_hash}")
                print(f"Original truncated hash for Block {i}: {truncated_hash}")


                # Step 4: Parity Extraction and Comparison
                def extract_parity(block, block_size):
                    flat_block = block.flatten()
                    # Parity is the nth bit (last bit) of the 0th LSB
                    return flat_block[block_size * block_size - 1] & 1  # Extract parity bit

                extracted_parity = extract_parity(block, block_size)
                print(f"Extracted parity bit for Block {i}: {extracted_parity}")
                print(f"Original parity bit for Block {i}: {parity_bit}")

                # Continue with embedding the recovery data in the 2nd LSB (if needed)
                recovery_data = generate_recovery_data(block, magic_square, bits_per_layer)
                block = embed_recovery_in_lsb(block, recovery_data)

                # Update the image with the modified block
                image[position[0]:position[0] + block_size, position[1]:position[1] + block_size] = block

        end_time = time.time()
        print(f"\nTime taken to process and embed data into blocks: {end_time - start_time:.6f} seconds")

        # Encrypt configuration data
        #encrypted_data = encrypt_config_data(config, key)

        # Save the configuration data to a JSON file instead of embedding it in the image
        config_filename = "config_data.json"
        config_path = os.path.join("processed_images", config_filename)

        with open(config_path, "w") as config_file:
            json.dump(config, config_file)
        print(f"Configuration data saved to {config_path}")

        # Prepare output image path with the same filename but with a .png extension in the processed_images directory
        output_image_filename = os.path.splitext(os.path.basename(image_filename))[0] + ".png"
        output_image_path = os.path.join(processed_dir, output_image_filename)

        # Save the image with the embedded data
        image_with_exif = Image.fromarray(image)
        # embed_data_in_png(image_with_exif, encrypted_data, output_image_path)
        image_with_exif.save(output_image_path, "PNG")
        print(f"Image saved WITHOUT embedded config in PNG text chunk: {output_image_path}")

        total_end_time = time.time()
        print(f"\nTotal time taken for processing image {os.path.basename(image_filename)} is: {total_end_time - total_start_time:.6f} seconds")
        print("\n" + "*" * 100)

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
