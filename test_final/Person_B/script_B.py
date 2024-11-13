import numpy as np
from hashlib import sha256
from cryptography.fernet import Fernet
from PIL import Image, ImageDraw
import argparse
import json
import os
import time

# Usage
# python3 Person_B/script_B.py Person_B/images/ Person_B/config/config.json Person_B/hashes/ Person_B/output.json

def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0], block_size):
        for j in range(0, image.shape[1], block_size):
            block = image[i:i+block_size, j:j+block_size]
            blocks.append(block)
            block_positions.append((i, j))
    return blocks, block_positions

def calculate_magic_square_hash(block, magic_square, position):
    multiplied_block = block * magic_square
    block_flattened = multiplied_block.flatten()
    block_string = ''.join(map(str, block_flattened))
    position_string = ''.join(map(str, position))
    combined_string = block_string + position_string
    return sha256(combined_string.encode('utf-8')).hexdigest()

def hash_pair(left, right):
    return sha256((left + right).encode('utf-8')).hexdigest()

def create_magic_square(n, start_num=1):
    if n < 3:
        raise ValueError("Block size must be at least 3 to form a valid magic square.")
    
    if n % 2 == 1:
        return create_siamese_magic_square(n, start_num)
    elif n % 4 == 0:
        return create_doubly_even_magic_square(n, start_num)
    else:
        return create_singly_even_magic_square(n, start_num)

def create_siamese_magic_square(n, start_num=1):
    magic_square = np.zeros((n, n), dtype=int)
    num = start_num
    i, j = 0, n // 2
    while num < start_num + n**2:
        magic_square[i, j] = num
        num += 1
        newi, newj = (i-1) % n, (j+1) % n
        if magic_square[newi, newj]:
            i += 1
        else:
            i, j = newi, newj
    return magic_square

def create_doubly_even_magic_square(n, start_num=1):
    magic_square = np.arange(start_num, start_num + n*n).reshape(n, n)
    indices = np.indices((n, n))
    r, c = indices[0], indices[1]
    mask = ((r % 4 == c % 4) | ((r % 4 + c % 4) == 3))
    magic_square[mask] = start_num + n*n - 1 - (magic_square[mask] - start_num)
    return magic_square

def create_singly_even_magic_square(n, start_num=1):
    half_n = n // 2
    half_magic_square = create_siamese_magic_square(half_n, start_num)
    magic_square = np.zeros((n, n), dtype=int)

    for i in range(4):
        r_offset = (i // 2) * half_n
        c_offset = (i % 2) * half_n
        if i == 0:
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square
        elif i == 1:
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 2*half_n*half_n
        elif i == 2:
            magic_square[r_offset+r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 3*half_n*half_n
        elif i == 3:
            magic_square[r_offset+r_offset+half_n, c_offset+c_offset+half_n] = half_magic_square + half_n*half_n

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

def retrieve_root_hash(key_file, storage_file):
    with open(key_file, "rb") as key_file:
        key = key_file.read()
    
    cipher_suite = Fernet(key)
    
    with open(storage_file, "rb") as file:
        encrypted_root_hash = file.read()
    
    root_hash = cipher_suite.decrypt(encrypted_root_hash).decode()
    return root_hash

def build_merkle_tree(hashes):
    while len(hashes) > 1:
        new_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i+1] if i+1 < len(hashes) else hashes[i]
            new_level.append(hash_pair(left, right))
        hashes = new_level
    return hashes[0]

def verify_image(image, magic_square, stored_root_hash):
    blocks, block_positions = divide_into_blocks(image, magic_square.shape[0])
    recalculated_hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]
    
    recalculated_root_hash = build_merkle_tree(recalculated_hashes)

    is_tampered = recalculated_root_hash != stored_root_hash
    print(f"Stored Root Hash: {stored_root_hash}")
    print(f"Recalculated Root Hash: {recalculated_root_hash}")
    print(f"Is tampered: {is_tampered}")

    return is_tampered, recalculated_hashes, block_positions

def add_padding(image, block_size):
    h, w = image.shape
    new_h = (h + block_size - 1) // block_size * block_size
    new_w = (w + block_size - 1) // block_size * block_size
    padded_image = np.zeros((new_h, new_w), dtype=image.dtype)
    padded_image[:h, :w] = image
    return padded_image

# def generate_block_pixels(block, block_size):
#     bx, by = block
#     return [(bx + x, by + y) for x in range(block_size) for y in range(block_size)]


def main():
    parser = argparse.ArgumentParser(description="Verify images and check if they are tampered.")
    parser.add_argument('images_dir', type=str, help="Directory containing the received images or a single image file")
    parser.add_argument('config_file', type=str, help="Path to the config JSON file")
    parser.add_argument('path_proofs_dir', type=str, help="Directory containing the original path proofs")
    parser.add_argument('output_file', type=str, help="File to save detected tampering information")

    args = parser.parse_args()
    images_path = args.images_dir
    config_file = args.config_file
    path_proofs_dir = args.path_proofs_dir
    output_file = args.output_file

    if os.path.isdir(images_path):
        image_files = [os.path.join(images_path, f) for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    else:
        image_files = [images_path]

    start_time = time.time()
    with open(config_file, "r") as file:
        config = json.load(file)
    end_time = time.time()
    print(f"Time taken to load config file: {end_time - start_time} seconds")
    
    block_size = config["block_size"]
    magic_constant = config["magic_constant"]
    start_num = config["start_num"]

    key_filename = "encryption_key.txt"
    key_path = os.path.join("Person_B/key", key_filename)
    if not os.path.exists(key_path):
        print(f"Encryption key file not found at {key_path}. Exiting...")
        return
    
    total_images = 0
    total_processing_time = 0
    overall_start_time = time.time()

    detected_tampering_log = {}

    for image_filename in image_files:
        image_path = image_filename

        print("\n" + "="*50)
        print(f"\nProcessing for the image --> {os.path.basename(image_filename)}.")
        print("\n" + "="*50)
        total_images += 1
        start_time = time.time()
        image = Image.open(image_path).convert('L')
        image_array = np.array(image)
        end_time = time.time()

        print(f"Time taken to load image: {end_time - start_time} seconds")

        start_time = time.time()
        if image_array.shape[0] % block_size != 0 or image_array.shape[1] % block_size != 0:
            print(f"Image dimensions of {image_filename} are not multiples of the block size. Adding padding...")
            image_array = add_padding(image_array, block_size)
        end_time = time.time()
        print(f"Time taken to add padding: {end_time - start_time} seconds")

        print(f"Verifying {image_filename}...")
        
        start_time = time.time()
        magic_square = create_magic_square(block_size, start_num)
        end_time = time.time()
        print(f"Time taken to create magic square: {end_time - start_time} seconds")
        print(f"Magic Square:\n{magic_square}")

        root_hash_filename = f"root_hash_storage_{os.path.basename(image_filename)}.txt"
        root_hash_path = os.path.join("Person_B/hashes", root_hash_filename)

        if not os.path.exists(root_hash_path):
            print(f"Root hash file not found at {root_hash_path}. Skipping...")
            continue

        start_time = time.time()
        stored_root_hash = retrieve_root_hash(key_path, root_hash_path)
        end_time = time.time()
        print(f"Time taken to retrieve root hash: {end_time - start_time} seconds")
        
        start_time = time.time()
        is_tampered, recalculated_hashes, block_positions = verify_image(image_array, magic_square, stored_root_hash)
        end_time = time.time()
        print(f"Time taken to verify image: {end_time - start_time} seconds")

        if is_tampered:
            path_proofs_filename = f"path_proofs_{os.path.basename(image_filename)}.json"
            path_proofs_path = os.path.join(path_proofs_dir, path_proofs_filename)
            
            if not os.path.exists(path_proofs_path):
                print(f"Path proofs file not found at {path_proofs_path}. Skipping...")
                continue
            
            start_time = time.time()
            with open(path_proofs_path, "r") as file:
                original_hashes = json.load(file)
            end_time = time.time()
            print(f"Time taken to load path proofs: {end_time - start_time} seconds")
            
            start_time = time.time()
            tampered_blocks = []
            for idx, (recalculated_hash, original_hash) in enumerate(zip(recalculated_hashes, original_hashes)):
                if recalculated_hash != original_hash:
                    tampered_blocks.append(block_positions[idx])
            end_time = time.time()
            print(f"Time taken to compare recalculated hashes with original hashes: {end_time - start_time} seconds")
            
            start_time = time.time()
            path_proofs_b_filename = f"path_proofs_b_{os.path.basename(image_filename)}.json"
            path_proofs_b_path = os.path.join("Person_B/hashes", path_proofs_b_filename)
            with open(path_proofs_b_path, "w") as file:
                json.dump(recalculated_hashes, file)
            end_time = time.time()
            print(f"Time taken to save recalculated hashes: {end_time - start_time} seconds")

            detected_tampering_log[os.path.basename(image_filename)] = tampered_blocks

            if tampered_blocks:
                start_time = time.time()
                tampered_image = Image.open(image_path).convert('RGB')
                draw = ImageDraw.Draw(tampered_image)
                for position in tampered_blocks:
                    i, j = position
                    for bi in range(block_size):
                        for bj in range(block_size):
                            draw.rectangle([j+bj, i+bi, j+bj+1, i+bi+1], outline="red")
                
                os.makedirs("Person_B/outputs", exist_ok=True)
                tampered_image_filename = f"tampered_analysis_{os.path.basename(image_filename)}"
                tampered_image_path = os.path.join("Person_B/outputs", tampered_image_filename)
                tampered_image.save(tampered_image_path)
                end_time = time.time()
                print(f"Time taken to highlight and save tampered areas: {end_time - start_time} seconds")
                print(f"Tampered areas highlighted and saved as {tampered_image_path}")
        else:
            print(f"No tampering detected for {image_filename}.")

    with open(output_file, 'w') as output_json:
        json.dump(detected_tampering_log, output_json, indent=4)

    print(f"\nDetected tampering log saved to {output_file}")

    print("\n" + "="*100)
    overall_end_time = time.time()
    total_processing_time = overall_end_time - overall_start_time

    print(f"\nTotal time taken for processing all images is : {overall_end_time - overall_start_time} seconds")
    print(f"Total number of images processed: {total_images}")
    print(f"Average processing time per image: {total_processing_time / total_images} seconds")

if __name__ == "__main__":
    main()
