import cv2
import numpy as np

# Function to divide the image into blocks
def divide_into_blocks(image, block_size):
    blocks = []
    positions = []
    h, w = image.shape
    for i in range(0, h, block_size):
        for j in range(0, w, block_size):
            block = image[i:i+block_size, j:j+block_size]
            blocks.append(block)
            positions.append((i, j))
    return blocks, positions

# Function to detect tampered blocks based on SVD
def detect_tampering(image, block_size=8, threshold=0.1):
    blocks, positions = divide_into_blocks(image, block_size)
    tampered_blocks = []

    for block in blocks:
        u, s, v = np.linalg.svd(block)
        # We use the singular values to detect tampering (simplified here)
        if np.var(s) > threshold:  # Check variance of singular values to detect tampering
            tampered_blocks.append(True)
        else:
            tampered_blocks.append(False)

    return tampered_blocks, positions

# Function to recover the tampered blocks using SVD
def recover_tampered_blocks(image, tampered_blocks, positions, block_size=8):
    recovered_image = image.copy()
    
    for (i, j), tampered in zip(positions, tampered_blocks):
        if tampered:
            block = image[i:i+block_size, j:j+block_size]
            # Recover the block using SVD (simplified)
            u, s, v = np.linalg.svd(block)
            s_recovered = np.clip(s, 0, 255)  # Adjust singular values
            block_recovered = np.dot(u, np.dot(np.diag(s_recovered), v))
            recovered_image[i:i+block_size, j:j+block_size] = block_recovered
    
    return recovered_image

# Combine detection and recovery
def detect_and_recover(image, block_size=8, threshold=0.1):
    print("Detecting tampered blocks...")
    tampered_blocks, positions = detect_tampering(image, block_size, threshold)
    
    print(f"Detected {sum(tampered_blocks)} tampered blocks.")
    
    print("Recovering tampered blocks...")
    recovered_image = recover_tampered_blocks(image, tampered_blocks, positions, block_size)
    
    return recovered_image

# Main function to load image and perform tamper detection and recovery
def main():
    image_path = 'tampered_image.png'
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        print("Error: Could not load image.")
        return
    
    block_size = 8
    threshold = 0.1  # Threshold for tamper detection
    
    # Detect and recover tampered blocks
    recovered_image = detect_and_recover(image, block_size, threshold)
    
    # Save the recovered image
    recovered_image_path = "recovered_image.png"
    cv2.imwrite(recovered_image_path, recovered_image)
    print(f"Recovered image saved at {recovered_image_path}")

if __name__ == "__main__":
    main()
