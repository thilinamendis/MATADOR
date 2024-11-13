import cv2
import numpy as np
from scipy.fftpack import dct, idct
from time import time

# Perform SVD on a block
def perform_svd(block):
    U, S, V = np.linalg.svd(block, full_matrices=False)
    return S  # We only need the singular values

# Calculate BAN from singular values
def calculate_ban(singular_values):
    trace = np.sum(singular_values)  # Trace is the sum of singular values
    ban = int(trace) % 4096  # Calculate BAN, mod 4096 (12-bit range)
    return ban

# Extract BAN and recovery bits from the block
def extract_watermark(block):
    extracted_ban = 0
    extracted_recovery = 0
    for x in range(4):
        for y in range(4):
            # Extracting 2 LSBs for BAN and recovery bits
            extracted_ban |= (block[x, y] & 0x03) << (2 * (x * 4 + y))
            extracted_recovery |= (block[x, y] & 0x03) << (2 * (x * 4 + y))

    print(f"Extracted BAN: {extracted_ban}")
    return extracted_ban, extracted_recovery

# Detect tampered blocks by comparing recalculated and extracted BANs
def detect_tampering(blocks, tolerance=35):
    tampered_blocks = []
    for i, block in enumerate(blocks):
        S = perform_svd(block)  # Recalculate SVD for the block
        recalculated_ban = calculate_ban(S)  # Recalculate BAN from singular values

        extracted_ban, _ = extract_watermark(block)  # Extract BAN from watermark
        
        # Allow for a small tolerance in BAN comparison
        if abs(recalculated_ban - extracted_ban) > tolerance:
            tampered_blocks.append(i)  # Block is tampered if BANs don't match closely
    return tampered_blocks

# Recover tampered blocks using stored self-recovery bits
def recover_tampered_blocks(blocks, tampered_blocks, block_size=4):
    height = int(np.sqrt(len(blocks)))  # Assuming blocks form a square image
    recovered_blocks = blocks.copy()

    def get_neighboring_blocks(block_idx):
        """Returns the indices of neighboring blocks for a given block index."""
        neighbors = []
        row, col = divmod(block_idx, height)
        
        # Add neighbors (top, bottom, left, right)
        if row > 0:
            neighbors.append(block_idx - height)  # top
        if row < height - 1:
            neighbors.append(block_idx + height)  # bottom
        if col > 0:
            neighbors.append(block_idx - 1)  # left
        if col < height - 1:
            neighbors.append(block_idx + 1)  # right
        
        return neighbors

    for i in tampered_blocks:
        print(f"Attempting to recover tampered block {i}...")
        
        # First try to recover using the block's own recovery bits
        _, recovery_bits = extract_watermark(recovered_blocks[i])
        recovery_block = np.zeros((block_size, block_size))
        for x in range(block_size):
            for y in range(block_size):
                recovery_block[x, y] = recovery_bits & 0x1F  # Use 5 MSBs for recovery
                recovery_bits >>= 5

        # If recovery bits fail, use neighboring blocks
        if np.all(recovery_block == 0):  # If block is not recoverable
            print(f"Recovery failed for block {i}, attempting to use neighbors...")
            neighbors = get_neighboring_blocks(i)
            for neighbor in neighbors:
                _, neighbor_recovery_bits = extract_watermark(recovered_blocks[neighbor])
                for x in range(block_size):
                    for y in range(block_size):
                        recovery_block[x, y] = neighbor_recovery_bits & 0x1F
                        neighbor_recovery_bits >>= 5
                # Exit if successful recovery
                if not np.all(recovery_block == 0):
                    print(f"Recovered block {i} from neighbor {neighbor}")
                    break
        
        if np.all(recovery_block == 0):
            print(f"Recovery failed completely for block {i}")
        else:
            print(f"Successfully recovered block {i}")

        recovered_blocks[i] = recovery_block

    return recovered_blocks

# Divide image into 4x4 blocks
def divide_into_blocks(image, block_size):
    blocks = []
    height, width = image.shape
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            block = image[i:i + block_size, j:j + block_size]
            blocks.append(block)
    return blocks

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
    # Load the tampered image
    tampered_image = cv2.imread('tampered_image.png', cv2.IMREAD_GRAYSCALE)

    # Divide tampered image into 4x4 blocks
    tampered_blocks = divide_into_blocks(tampered_image, 4)

    # Detect tampered blocks by comparing recalculated and extracted BANs
    print("Detecting tampering...")
    tampered_positions = detect_tampering(tampered_blocks)
    print(f"Detected {len(tampered_positions)} tampered blocks.")

    # Recover tampered blocks using the stored recovery bits
    print("Recovering tampered blocks...")
    recovered_blocks = recover_tampered_blocks(tampered_blocks, tampered_positions)

    # Reconstruct the image with recovered blocks
    recovered_image = reconstruct_image(recovered_blocks, tampered_image.shape[0], tampered_image.shape[1], 4)

    # Save the recovered image
    cv2.imwrite('recovered_image.png', recovered_image)

    print(f"Recovered image saved as 'recovered_image.png'")
    print(f"Total execution time: {time() - start_time:.2f} seconds")
    print("total number of blocks in the image: ", len(tampered_blocks))

if __name__ == "__main__":
    main()
