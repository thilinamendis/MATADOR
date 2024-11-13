import numpy as np
from hashlib import md5
from cryptography.fernet import Fernet
from PIL import Image, PngImagePlugin, TiffImagePlugin
import json
import os
import argparse
from tifffile import TiffFile
from tqdm import tqdm

Image.MAX_IMAGE_PIXELS = None

# Helper function to extract metadata (encrypted JSON) from the image
def extract_metadata(image):
    metadata = image.info  # Access image metadata through the `.info` dictionary
    print(f"Metadata in {image.filename}: {metadata}")  # Print all available metadata for debugging
    if "EncryptedConfig" in metadata:
        return metadata["EncryptedConfig"].encode('latin1')  # Return encoded binary data
    return None

# Function to extract encrypted data from TIFF image pixel data
def extract_data_from_tiff(image):
    np_image = np.array(image)
    bits = []
    
    # Extract the LSBs from the pixel data
    for i in range(np_image.shape[0]):
        for j in range(np_image.shape[1]):
            bits.append(np_image[i, j] & 1)  # Extract the LSB of the pixel value
    
    # Convert bits back to bytes
    bit_string = ''.join(map(str, bits))
    encrypted_data = int(bit_string, 2).to_bytes(len(bit_string) // 8, byteorder='big')
    
    return encrypted_data

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

# Function to calculate an MD5 hash and a parity bit for a block using 5 MSBs
def calculate_md5_and_parity(block, magic_square, block_index, block_size):
    # Calculate the required number of bits for the hash based on the block size
    hash_bits = (block_size * block_size * 2) - 1  # Total bits required

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

    # Step 5: Ensure the hash is padded to match the required length
    binary_full_hash = binary_full_hash.zfill(128)  # Ensure it's at least 128 bits long
    while len(binary_full_hash) < hash_bits:
        binary_full_hash += '0'  # Pad with zeros until it's the required length

    # Step 6: Truncate or pad the hash to exactly 'hash_bits' length
    truncated_hash = binary_full_hash[:hash_bits]  # Get exactly the required number of bits

    # Step 7: Calculate the parity bit (the number of 1s in the binary string modulo 2)
    parity_bit = str(binary_full_hash.count('1') % 2)

    return truncated_hash, parity_bit


# Function to extract hash from LSBs (modified for varying bit depths)
def extract_hash_from_lsb(block, block_size, bit_depth):
    # Dynamically calculate the total number of bits needed based on the block size
    total_bits_needed = (block_size * block_size * 2) - 1  # n * n * 2 - 1

    extracted_hash = []
    hash_index = 0

    # Extract 0th LSB for the first half of the hash
    for i in range(block_size):
        for j in range(block_size):
            if i == block_size - 1 and j == block_size - 1:
                continue  # Skip the last pixel for the parity bit
            extracted_hash.append((block[i, j] >> (bit_depth - 1)) & 1)
            hash_index += 1
            if hash_index >= total_bits_needed // 2:
                break

    # Extract 1st LSB for the remaining hash
    for i in range(block_size):
        for j in range(block_size):
            if hash_index < total_bits_needed:
                extracted_hash.append((block[i, j] >> (bit_depth - 2)) & 1)
                hash_index += 1

    # Ensure the extracted hash length is exactly the required length
    if len(extracted_hash) != total_bits_needed:
        print(f"Warning: Extracted hash length {len(extracted_hash)} does not match expected length {total_bits_needed}")

    return ''.join(map(str, extracted_hash))  # Return as a string of bits


# Function to extract the parity bit
def extract_parity(block, block_size, bit_depth):
    return (block[-1, -1] >> (bit_depth - 1)) & 1  # Extract parity bit from the last pixel's 0th LSB

# Function to create a magic square (same as in Person A)
def create_magic_square(n, start_num=1):
    if n < 3:
        raise ValueError("Block size must be at least 3 to form a valid magic square.")
    if n % 2 == 1:
        return create_siamese_magic_square(n, start_num)
    elif n % 4 == 0:
        return create_doubly_even_magic_square(n, start_num)
    else:
        return create_singly_even_magic_square(n, start_num)

# Magic square generation functions (same as in Person A)
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
def highlight_tampered_blocks(image, tampered_blocks, block_size):
    highlight_block = 255  # Set the highlight color (e.g., white)
    
    # Loop through each tampered block's position and highlight it
    for position in tampered_blocks:
        x, y = position  # Unpack the position tuple
        # Highlight the block by setting its pixel values to the highlight color
        image[x:x + block_size, y:y + block_size] = highlight_block
    
    return image

# Function to extract recovery data from the 2nd LSB
def extract_recovery_from_lsb(block, bit_depth):
    flat_block = block.flatten()
    recovery_bits = [(flat_block[i] >> (bit_depth - 3)) & 1 for i in range(flat_block.size)]  # Extract 2nd LSB
    block_size = block.shape[0]  # Assuming square blocks
    required_bits = block_size * block_size  # We need block_size^2 bits

    # Ensure we only return the necessary bits
    recovery_bits = recovery_bits[:required_bits]  # Trim or pad if needed

    recovery_data = ''.join(map(str, recovery_bits))  # Return as a string of bits
    return recovery_data

# Function to apply recovery data and restore tampered blocks
def apply_recovery_data(block, recovery_data):
    block_size = block.shape[0]
    required_bits = block_size * block_size  # We need block_size^2 bits (1 bit per pixel)

    # Ensure the recovery data is long enough
    if len(recovery_data) < required_bits:
        raise ValueError(f"Not enough recovery data: expected {required_bits} bits, got {len(recovery_data)} bits.")

    # Convert recovery data from bits to LSB values (since we're dealing with 1 bit per pixel)
    recovery_values = np.array([int(bit) for bit in recovery_data]).reshape(block.shape)

    # Get the original MSBs from the block (5 MSBs from each pixel)
    msb_block = (block & 0xF8)  # Keep the 5 most significant bits intact
    
    # Combine the original MSBs with the recovered LSBs (shifted into the right position)
    recovered_block = msb_block | recovery_values  # Combine MSBs with recovered LSBs
    return recovered_block

# Function to save the image in its original format
def save_image(image, image_format, output_image_path):
    image_pil = Image.fromarray(image)
    
    # Save based on the input format
    if image_format == 'png':
        image_pil.save(output_image_path, "PNG")
    elif image_format in ['jpeg', 'jpg']:
        image_pil.save(output_image_path, "JPEG")
    elif image_format in ['tiff', 'tif']:
        image_pil.save(output_image_path, "TIFF")
    else:
        raise ValueError(f"Unsupported image format: {image_format}")
    
    print(f"Image saved as: {output_image_path}")


def extract_data_from_tiff_tags(image_path):
    with TiffFile(image_path) as tif:
        for page in tif.pages:
            # Look for the ImageDescription tag
            if 'ImageDescription' in page.tags:
                tag = page.tags['ImageDescription']
                description = tag.value  # Get the description text
                # Convert the description back to JSON and extract "EncryptedConfig"
                try:
                    description_json = json.loads(description)
                    if "EncryptedConfig" in description_json:
                        print(f"Found EncryptedConfig in ImageDescription.")
                        return description_json["EncryptedConfig"].encode('latin1')
                except json.JSONDecodeError:
                    print("Error decoding ImageDescription as JSON.")
    return None

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
    image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]

    if not image_files:
        print(f"No images found in {images_path}.")
        return

    for image_file in image_files:
        image_path = os.path.join(images_path, image_file)
        print(f"\nProcessing {image_file}...")

        # Load the processed image and determine bit depth and format
        image, bit_depth, image_format = load_image_and_bit_depth(image_path)
        
        # Extract encrypted metadata or TIFF tag data based on image format
        if image_format == 'png':
            encrypted_data = extract_metadata(Image.open(image_path))
        elif image_format in ['jpeg', 'jpg']:
            encrypted_data = extract_metadata(Image.open(image_path))
        elif image_format in ['tiff', 'tif']:
            encrypted_data = extract_data_from_tiff_tags(image_path)
        else:
            print(f"Unsupported image format: {image_format}")
            continue

        # Check if encrypted data was found
        if encrypted_data is None:
            print(f"No encrypted configuration data found in {image_file}.")
            continue

        # Decrypt the configuration data
        config = decrypt_config_data(encrypted_data, key)

        block_size = config["block_size"]
        magic_constant = config["magic_constant"]

        # Recreate the magic square using the block size and magic constant
        magic_square = create_magic_square(block_size, start_num=1)  # Start num should match Person A's choice
        
        print("Configuration Info:")
        print(json.dumps(config, indent=4))  # Display config information in a readable format

        print("Generated Magic Square:")
        print(magic_square)

        # Divide the image into blocks
        blocks, block_positions = divide_into_blocks(image, block_size)
        
        # Initialize a list to store tampered blocks
        tampered_blocks = []
        recovered_image = image.copy()  # Create a copy for recovery

        # Iterate over each block and verify hashes
        for i, (block, position) in enumerate(tqdm(zip(blocks, block_positions), total=len(blocks), desc="Processing Blocks")):
            # Step 1: Calculate the hash and parity just like Person A
            calculated_hash, calculated_parity = calculate_md5_and_parity(block, magic_square, i, block_size)

            # Step 2: Extract the hash and parity from the block's LSBs
            extracted_hash = extract_hash_from_lsb(block, block_size, bit_depth)
            extracted_parity = extract_parity(block, block_size, bit_depth)

            # Step 3: Ensure the extracted hash is padded to the required hash length for this block size
            expected_hash_length = (block_size * block_size * 2) - 1

            if len(extracted_hash) < expected_hash_length:
                extracted_hash += '0' * (expected_hash_length - len(extracted_hash))

            if len(calculated_hash) < expected_hash_length:
                calculated_hash += '0' * (expected_hash_length - len(calculated_hash))

            # Now compare the hashes
            if calculated_hash != extracted_hash or calculated_parity != str(extracted_parity):
                # print(f"Block {i} at position {position} is tampered.")
                # print(f"Calculated Hash: {calculated_hash}")
                # print(f"Extracted Hash: {extracted_hash}")
                # print(f"Calculated Parity: {calculated_parity}")
                # print(f"Extracted Parity: {extracted_parity}")
                tampered_blocks.append(position)


        # Highlight and save the tampered image
        if tampered_blocks:
            # Highlight the tampered blocks
            highlighted_image = highlight_tampered_blocks(recovered_image.copy(), tampered_blocks, block_size)
            
            # Save the highlighted image before recovery
            highlighted_image_path = os.path.join(images_path, "highlighted_" + image_file)
            save_image(highlighted_image, image_format, highlighted_image_path)

            print(f"Highlighted image saved as: highlighted_{image_file}")
            
            # Now ask the user if they want to recover the tampered blocks
            recover_choice = input("Do you want to attempt to recover the tampered blocks? (yes/no): ").lower()
            if recover_choice == 'yes':
                for position in tampered_blocks:  # Now correctly use the block position
                    x, y = position
                    block = blocks[block_positions.index(position)]  # Retrieve the tampered block
                    
                    # Extract recovery data from the 2nd LSB
                    recovery_data = extract_recovery_from_lsb(block, bit_depth)
                    
                    # Apply recovery data to restore the block
                    recovered_block = apply_recovery_data(block, recovery_data)
                    
                    # Replace the tampered block with the recovered block in the image
                    recovered_image[x:x + block_size, y:y + block_size] = recovered_block
                
                # Save the recovered image
                recovered_image_path = os.path.join(images_path, "recovered_" + image_file)
                save_image(recovered_image, image_format, recovered_image_path)
                print(f"Recovered image saved as: recovered_{image_file}")
        else:
            print(f"{image_file} is not tampered. All blocks are intact.")
    print("All images processed.")


if __name__ == "__main__":
    main()
