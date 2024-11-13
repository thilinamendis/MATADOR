import numpy as np

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

    # Positioning smaller squares in quadrants
    indices = np.indices((half_n, half_n))
    for i in range(4):
        r_offset = (i//2) * half_n
        c_offset = (i%2) * half_n
        if i == 0:
            # Top-left quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square
        elif i == 1:
            # Top-right quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 2*half_n*half_n
        elif i == 2:
            # Bottom-left quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 3*half_n*half_n
        elif i == 3:
            # Bottom-right quadrant
            magic_square[r_offset:r_offset+half_n, c_offset+c_offset+half_n] = half_magic_square + half_n*half_n

    # Swapping values to make it magic
    k = (n - 2) // 4
    for i in range(half_n):
        for j in range(k):
            if j == k - 1 and i == k:
                # Do nothing
                continue
            # Swap elements in top-left and bottom-left quadrants
            magic_square[i, j], magic_square[i + half_n, j] = magic_square[i + half_n, j], magic_square[i, j]

    for i in range(half_n):
        for j in range(n - k, n):
            # Swap elements in top-right and bottom-right quadrants
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

def main():
    while True:
        try:
            block_size = get_positive_integer("Enter the block size (positive integer, at least 3): ")
            if block_size < 3:
                raise ValueError("Block size must be at least 3 to form a valid magic square.")
            break
        except ValueError as e:
            print(f"Error: {e}")

    start_nums = list(range(2, 12))  # You can adjust this range as needed
    possible_magic_numbers = generate_possible_magic_numbers(block_size, start_nums)
    print(f"Suggested magic numbers for a {block_size}x{block_size} grid based on different starting numbers: {possible_magic_numbers}")

    while True:
        try:
            magic_number = get_positive_integer("Enter the magic number: ")
            if magic_number not in possible_magic_numbers:
                raise ValueError(f"Magic number must be one of the suggested values: {possible_magic_numbers}")
            break
        except ValueError as e:
            print(f"Error: {e}")

    start_num_index = possible_magic_numbers.index(magic_number)
    start_num = start_nums[start_num_index]

    # Create the magic square
    magic_square = create_magic_square(block_size, start_num)
    print(f"Magic Square:\n{magic_square}")

if __name__ == "__main__":
    main()
