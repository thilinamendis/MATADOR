# import cv2
# import numpy as np
# from scipy.fftpack import dct, idct
# import matplotlib.pyplot as plt

# # Step 1: Divide the image into non-overlapping blocks
# def divide_into_blocks(image, block_size):
#     blocks = []
#     height, width = image.shape
#     for i in range(0, height, block_size):
#         for j in range(0, width, block_size):
#             block = image[i:i + block_size, j:j + block_size]
#             blocks.append(block)
#     return blocks

# # Step 2: Perform DCT on a block
# def perform_dct(block):
#     return dct(dct(block.T, norm='ortho').T, norm='ortho')

# # Step 3: Inverse DCT to get the block back
# def perform_idct(block_dct):
#     return idct(idct(block_dct.T, norm='ortho').T, norm='ortho')

# # Step 4: Generate watermark from DC and AC coefficients of the blocks
# def generate_watermark(blocks, block_size):
#     watermark_bits = []
#     for block in blocks:
#         dct_block = perform_dct(block)

#         # Extract DC coefficient (0,0) and some AC coefficients for watermarking
#         dc_coeff = dct_block[0, 0]
#         ac_coeffs = dct_block[0, 1:block_size]  # Using first row AC coefficients for watermark generation

#         # Example: Use the parity (even/odd) of DC and AC coefficients to generate watermark bits
#         for ac in ac_coeffs:
#             watermark_bits.append(1 if ac % 2 == 0 else 0)
    
#     return np.array(watermark_bits)

# # Step 5: Embed the generated watermark into the image
# def embed_watermark(blocks, watermark_bits, block_size):
#     watermark_index = 0
#     watermarked_blocks = []
#     for block in blocks:
#         dct_block = perform_dct(block)

#         # Modify the DC coefficient based on the watermark bit (fragile embedding)
#         if watermark_bits[watermark_index] == 1:
#             dct_block[0, 0] += 1  # Altering the DC coefficient
#         watermark_index += 1

#         # Reconstruct the block using inverse DCT
#         watermarked_block = perform_idct(dct_block)
#         watermarked_blocks.append(watermarked_block)
    
#     return watermarked_blocks

# # Step 6: Reconstruct the image from the watermarked blocks
# def reconstruct_image(blocks, height, width, block_size):
#     reconstructed_image = np.zeros((height, width))
#     block_index = 0
#     for i in range(0, height, block_size):
#         for j in range(0, width, block_size):
#             reconstructed_image[i:i + block_size, j:j + block_size] = blocks[block_index]
#             block_index += 1
#     return reconstructed_image

# def main():
#     # Load image and convert to grayscale
#     image_path = 'test_image_1.jpeg'  # Replace with your image
#     image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

#     # Ensure image size is divisible by block size (8x8 blocks in this example)
#     block_size = 8
#     height, width = image.shape
#     height -= height % block_size
#     width -= width % block_size
#     image = image[:height, :width]

#     # Divide image into blocks
#     blocks = divide_into_blocks(image, block_size)

#     # Generate watermark from the image's DCT coefficients
#     print("Generating watermark from image...")
#     watermark_bits = generate_watermark(blocks, block_size)

#     # Embed watermark back into the image
#     print("Embedding watermark into the image...")
#     watermarked_blocks = embed_watermark(blocks, watermark_bits, block_size)

#     # Reconstruct the watermarked image
#     watermarked_image = reconstruct_image(watermarked_blocks, height, width, block_size)

#     # Save and display results
#     cv2.imwrite('watermarked_image.png', watermarked_image)
#     plt.imshow(watermarked_image, cmap='gray')
#     plt.title('Watermarked Image')
#     plt.show()

# if __name__ == "__main__":
#     main()

import cv2
import numpy as np
from scipy.fftpack import dct, idct
from time import time

# Perform SVD on the block
def perform_svd(block):
    U, S, V = np.linalg.svd(block, full_matrices=False)
    return U, S, V

# Calculate the Block Authentication Number (BAN)
def calculate_ban(singular_values):
    trace = np.sum(singular_values)
    # Map trace to the range [0, 4095] to get a 12-bit BAN
    ban = int(trace) % 4096
    return ban

# Calculate the average of the 5 MSBs of each 2x2 sub-block for self-recovery
def calculate_self_recovery(block):
    msb_values = (block >> 3) & 0x1F  # Extract first 5 MSBs
    avg_msb = np.mean(msb_values)
    return avg_msb

# Arnold transformation (scramble)
def arnold_scramble(block, iterations):
    N = block.shape[0]
    scrambled = np.copy(block)
    for _ in range(iterations):
        new_block = np.zeros_like(block)
        for x in range(N):
            for y in range(N):
                new_x = (x + y) % N
                new_y = (x + 2 * y) % N
                new_block[new_x, new_y] = scrambled[x, y]
        scrambled = new_block
    return scrambled

# Divide image into 4x4 blocks
def divide_into_blocks(image, block_size):
    blocks = []
    height, width = image.shape
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            block = image[i:i + block_size, j:j + block_size]
            blocks.append(block)
    return blocks

# Embed BAN and self-recovery bits into the LSB of blocks
def embed_watermark(blocks, bans, recovery_bits):
    watermarked_blocks = []
    for i, block in enumerate(blocks):
        ban = int(bans[i])  # Ensure ban is an integer
        recovery = int(recovery_bits[i])  # Ensure recovery is an integer
        
        # Ensure the block is in integer format (for bitwise operations)
        block = block.astype(np.uint8)

        print(f"Embedding BAN {ban} into block {i}")

        for x in range(4):
            for y in range(4):
                # Embed BAN and recovery into the LSBs
                block[x, y] = (block[x, y] & 0xFC) | (ban & 0x03) | (recovery & 0x03)
                ban >>= 2
                recovery >>= 2
        
        watermarked_blocks.append(block)
    return watermarked_blocks

# Reconstruct image from blocks
def reconstruct_image(blocks, height, width, block_size):
    reconstructed_image = np.zeros((height, width))
    block_index = 0
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            reconstructed_image[i:i + block_size, j:j + block_size] = blocks[block_index]
            block_index += 1
    return reconstructed_image

def main():
    start_time = time()

    image_path = 'test_image_1.jpeg'  # Your image
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    block_size = 4
    iterations = 1

    # Ensure both height and width are divisible by the block size
    height, width = image.shape
    height = height - (height % block_size)
    width = width - (width % block_size)
    image = image[:height, :width]  # Crop the image to fit the block size exactly

    blocks = divide_into_blocks(image, block_size)
    # Show the number of blocks
    

    # Step 1: Calculate BAN and recovery bits for each block
    print("Generating BAN and recovery bits...")
    bans = []
    recovery_bits = []
    for block in blocks:
        U, S, V = perform_svd(block)
        bans.append(calculate_ban(S))
        recovery_bits.append(calculate_self_recovery(block))

    # Step 2: Embed the BAN and recovery bits into the image
    print("Embedding watermark and recovery bits...")
    watermarked_blocks = embed_watermark(blocks, bans, recovery_bits)
    watermarked_image = reconstruct_image(watermarked_blocks, height, width, block_size)
    
    cv2.imwrite('watermarked_image.png', watermarked_image)

    print(f"Watermark embedding completed in {time() - start_time:.2f} seconds")
    print(f"Total number of blocks: {len(blocks)}")

if __name__ == "__main__":
    main()
