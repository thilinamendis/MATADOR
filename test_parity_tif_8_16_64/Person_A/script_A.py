import numpy as np
from hashlib import md5
from cryptography.fernet import Fernet
from PIL import Image, PngImagePlugin
import argparse
import json
import os
import time
from PIL import Image, TiffImagePlugin
import numpy as np
from tifffile import TiffWriter
from tifffile import TiffFile
from tqdm import tqdm

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

def verify_tiff_tags(image_path):
    with TiffFile(image_path) as tif:
        for page in tif.pages:
            for tag in page.tags.values():
                print(f"Tag {tag.name}: {tag.value}")

# Function to load an image and determine bit depth and format
def load_image_and_bit_depth(image_path):
    image = Image.open(image_path)
    image_format = image.format.lower()  # Get the image format (png, jpeg, tiff)
    
    if image.mode == 'L':  # Grayscale 8-bit images
        bit_depth = 8
    elif image.mode == 'I;16':  # 16-bit grayscale TIFF
        bit_depth = 16
    elif image.mode == 'I':  # 32-bit integer TIFF
        bit_depth = 32
    elif image.mode == 'F':  # 32-bit or 64-bit floating point TIFF
        bit_depth = 64
    else:
        raise ValueError(f"Unsupported image mode {image.mode}.")
    
    image = np.array(image)
    return image, bit_depth, image_format


# Modify convert_to_8bit to handle different bit depths
def convert_to_bit_string(pixel_value, bit_depth):
    return format(pixel_value, f'0{bit_depth}b')

# Ensure every pixel is represented in 8-bit binary
def convert_to_8bit(pixel_value):
    return format(pixel_value, '08b')

# Convert bit binary string to integer
def convert_to_int(binary_str):
    return int(binary_str, 2)

# Function to calculate an MD5 hash and a parity bit for a block using 5 MSBs
def calculate_md5_and_parity(block, magic_square, block_index, block_size):
    # Calculate the required number of bits for the hash based on the block size
    hash_bits = (block_size * block_size * 2) - 1  # Total bits required (n * n * 2 - 1)

    # Step 1: Generate the MSB block (upper 5 bits)
    msb_block = (block & 0xF8) >> 3  # Extract 5 MSBs from each pixel

    # Step 2: Multiply the block by the magic square and flatten it
    multiplied_block = msb_block * magic_square
    block_flattened = multiplied_block.flatten()

    # Step 3: Combine the block and the block index into a single string
    combined_string = ''.join(map(str, block_flattened)) + format(block_index, '08b')

    # Step 4: Generate the MD5 hash (128 bits)
    full_hash = md5(combined_string.encode('utf-8')).hexdigest()
    binary_full_hash = bin(int(full_hash, 16))[2:]  # Convert to binary

    # Step 5: Pad the hash with zeros if it's shorter than the required length
    binary_full_hash = binary_full_hash.zfill(128)  # Ensure it's at least 128 bits long
    while len(binary_full_hash) < hash_bits:
        binary_full_hash += '0'  # Pad with zeros until it's the required length

    # Step 6: Truncate or pad the hash to exactly 'hash_bits' length
    truncated_hash = binary_full_hash[:hash_bits]  # Get exactly the required number of bits

    # Step 7: Calculate the parity bit (the number of 1s in the binary string modulo 2)
    parity_bit = str(binary_full_hash.count('1') % 2)

    return truncated_hash, parity_bit



# Function to generate differential recovery data
def generate_recovery_data(original_block, magic_square, block_size):
    num_bits = block_size * block_size  # Dynamically calculate the number of bits based on block size
    msb_original_block = (original_block & 0xF8) >> 3  # Extract upper 5 bits
    transformed_block = msb_original_block * magic_square
    diff = msb_original_block - transformed_block
    diff_flattened = diff.flatten()
    recovery_bits = ''.join(format((pixel % 256), '08b') for pixel in diff_flattened)[:num_bits]
    return recovery_bits

# Function to clear 0th and 1st LSBs
# Modify the clear_lsb function to support any bit depth
def clear_lsb(block, block_size, bit_depth):
    mask = (1 << (bit_depth - 2)) - 1  # Create mask to clear the 0th and 1st LSBs
    for i in range(block_size):
        for j in range(block_size):
            block[i, j] = block[i, j] & mask  # Clear both 0th and 1st LSBs
    return block


# Modify the embedding function to support different bit depths
def embed_hash_in_lsb(block, hash_data, parity_bit, block_size, bit_depth):
    # Step 1: Clear all 0th and 1st LSBs before embedding
    block = clear_lsb(block, block_size, bit_depth)
    hash_index = 0
    total_bits = (block_size * block_size * 2) - 1

    # Embed the hash into the LSBs based on the bit depth
    # Step 2: Embed the hash into the 0th LSBs (hash_data[0:block_size * block_size - 1])
    for i in range(block_size):
        for j in range(block_size):
            if i == block_size - 1 and j == block_size - 1:
                continue
            block[i, j] = (block[i, j] & ~(1 << (bit_depth - 1))) | (int(hash_data[hash_index]) << (bit_depth - 1))
            hash_index += 1
    
    # Step 3: Embed the hash into the 1st LSBs (hash_data[block_size * block_size:])
    for i in range(block_size):
        for j in range(block_size):
            if hash_index < total_bits:
                block[i, j] = (block[i, j] & ~(1 << (bit_depth - 2))) | (int(hash_data[hash_index]) << (bit_depth - 2))
                hash_index += 1

    # Embed the parity bit
    block[-1, -1] = (block[-1, -1] & ~(1 << (bit_depth - 1))) | int(parity_bit)

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

# Function to embed encrypted data in image metadata or pixels
# Function to embed encrypted data in image metadata or TIFF tags
def embed_data_in_image(image, encrypted_data, output_image_path, image_format):
    encrypted_string = encrypted_data.decode('latin1')  # Convert binary data to a string

    if image_format == 'png':
        # For PNG, embed data in metadata using PngInfo
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("EncryptedConfig", encrypted_string)
        image.save(output_image_path, "PNG", pnginfo=metadata)
        print(f"PNG image saved with embedded config in metadata: {output_image_path}")

    elif image_format == 'jpeg' or image_format == 'jpg':
        # For JPEG, there's limited metadata support, but we can still use EXIF metadata for some info
        # JPEG metadata embedding logic (similar to PNG)
        image.save(output_image_path, "JPEG", quality=95, exif=image.info.get('exif', b''))
        print(f"JPEG image saved with embedded config in metadata: {output_image_path}")

    elif image_format in ['tiff', 'tif']:
        # For TIFF, embed data using custom TIFF tags (using TiffWriter from tifffile)
        np_image = np.array(image)  # Convert PIL image to NumPy array
        with TiffWriter(output_image_path) as tif:
            # Use a custom TIFF tag to store the encrypted data
            tif.write(np_image, metadata={'EncryptedConfig': encrypted_string})
        print(f"TIFF image saved with embedded config in tags: {output_image_path}")

    else:
        raise ValueError(f"Unsupported image format: {image_format}")

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

def extract_parity(block, block_size, bit_depth):
    return (block[-1, -1] >> (bit_depth - 1)) & 1

# Modify the extraction functions to handle bit depths
def extract_hash_from_lsb(block, block_size, bit_depth):
    extracted_hash = []

    # Extract the 0th LSB
    for i in range(block_size):
        for j in range(block_size):
            if i == block_size - 1 and j == block_size - 1:
                continue
            extracted_hash.append((block[i, j] >> (bit_depth - 1)) & 1)

    # Extract the 1st LSB
    for i in range(block_size):
        for j in range(block_size):
            extracted_hash.append((block[i, j] >> (bit_depth - 2)) & 1)

    return ''.join(map(str, extracted_hash))

# Main function to handle user inputs and process the images
def main():
    parser = argparse.ArgumentParser(description="Process images and generate block hashes.")
    parser.add_argument('images_path', type=str, help="Directory containing the input images or a single image file")
    args = parser.parse_args()
    images_path = args.images_path

    key_filename = "encryption_key.txt"
    key_path = os.path.join("key", key_filename)

    # Generate or load the encryption key
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as key_file:
            key_file.write(key)
    else:
        with open(key_path, "rb") as key_file:
            key = key_file.read()

    # Determine if it's a directory or a single file
    if os.path.isdir(images_path):
        image_files = [os.path.join(images_path, f) for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
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

        # Load the image and determine its bit depth and format
        image, bit_depth, image_format = load_image_and_bit_depth(image_path)

        print(f"Image bit depth: {bit_depth}")

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

        # Create the magic square based on the selected block size
        magic_square = create_magic_square(block_size, 1)
        
        # Print the magic square and config info
        print("Generated Magic Square:")
        print(magic_square)

        config = {"block_size": block_size, "magic_constant": int(sum(magic_square[0]))}
        print("Configuration Info:")
        print(json.dumps(config, indent=4))

        blocks, block_positions = divide_into_blocks(image, block_size)

        # Process each block with a progress bar
        for i, (block, position) in enumerate(tqdm(zip(blocks, block_positions), total=len(blocks), desc="Processing Blocks")):
            truncated_hash, parity_bit = calculate_md5_and_parity(block, magic_square, i, block_size)
            block = embed_hash_in_lsb(block, truncated_hash, parity_bit, block_size, bit_depth)
            recovery_data = generate_recovery_data(block, magic_square, block_size)
            block = embed_recovery_in_lsb(block, recovery_data)

        # Encrypt the configuration data
        encrypted_data = encrypt_config_data(config, key)

        # Save the image with the encrypted config data embedded in the metadata
        image_with_exif = Image.fromarray(image)
        output_image_filename = os.path.splitext(os.path.basename(image_filename))[0] + f".{image_format}"
        output_image_path = os.path.join(processed_dir, output_image_filename)

        # Save image in the same format as the input
        embed_data_in_image(image_with_exif, encrypted_data, output_image_path, image_format)

        # Only verify TIFF tags if the image is a TIFF
        if image_format in ['tiff', 'tif']:
            verify_tiff_tags(output_image_path)

    overall_end_time = time.time()
    print(f"\nTotal processing time: {overall_end_time - overall_start_time:.2f} seconds")

if __name__ == "__main__":
    main()
