def compare_hashes(file_a, file_b):
    with open(file_a, "r") as file:
        hashes_a = file.readlines()
    
    with open(file_b, "r") as file:
        hashes_b = file.readlines()
    
    if len(hashes_a) != len(hashes_b):
        print("The number of blocks in the two files does not match.")
        return
    
    tampered_blocks = []
    for i, (line_a, line_b) in enumerate(zip(hashes_a, hashes_b)):
        position_a, hash_a = line_a.strip().split(": ")
        position_b, hash_b = line_b.strip().split(": ")
        
        if hash_a != hash_b:
            tampered_blocks.append(position_a)
            print(f"Tampered block detected at {position_a}: {hash_a} != {hash_b}")
    
    print(f"Total tampered blocks: {len(tampered_blocks)}")
    print(f"Tampered blocks: {tampered_blocks}")

if __name__ == "__main__":
    compare_hashes("test_a.txt", "test_b.txt")
