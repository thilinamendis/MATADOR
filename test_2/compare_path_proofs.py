import json
import argparse

def compare_path_proofs(path_proofs_a, path_proofs_b):
    mismatches = []

    for i, (proof_a, proof_b) in enumerate(zip(path_proofs_a, path_proofs_b)):
        if len(proof_a) != len(proof_b):
            mismatches.append({
                'block_index': i,
                'path_proof_a': proof_a,
                'path_proof_b': proof_b,
                'reason': 'Different number of levels in path proofs'
            })
            continue

        for level in range(len(proof_a)):
            if proof_a[level] != proof_b[level]:
                mismatches.append({
                    'block_index': i,
                    'level': level,
                    'path_proof_a': proof_a[level],
                    'path_proof_b': proof_b[level],
                    'reason': 'Different hashes at this level'
                })

    return mismatches

def main():
    parser = argparse.ArgumentParser(description="Compare two JSON files containing path proofs and identify mismatches.")
    parser.add_argument('path_proofs_a', type=str, help="Path to the first path proofs JSON file")
    parser.add_argument('path_proofs_b', type=str, help="Path to the second path proofs JSON file")

    args = parser.parse_args()

    # Load the path proofs from the JSON files
    with open(args.path_proofs_a, "r") as file:
        path_proofs_a = json.load(file)

    with open(args.path_proofs_b, "r") as file:
        path_proofs_b = json.load(file)

    # Compare the path proofs and identify mismatches
    mismatches = compare_path_proofs(path_proofs_a, path_proofs_b)

    if mismatches:
        print(f"Total mismatches found: {len(mismatches)}")
        for mismatch in mismatches:
            print(f"Block index: {mismatch['block_index']}")
            if 'level' in mismatch:
                print(f"Level: {mismatch['level']}")
            print(f"Path proof A: {mismatch['path_proof_a']}")
            print(f"Path proof B: {mismatch['path_proof_b']}")
            print(f"Reason: {mismatch['reason']}\n")
    else:
        print("No mismatches found. The path proofs are identical.")

if __name__ == "__main__":
    main()
