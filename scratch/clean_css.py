import os

def clean_css():
    filepath = os.path.join("static", "css", "styles.css")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # File is 1-indexed:
    # line 2128 is index 2127
    # line 2322 is index 2321
    start_idx = 2127
    end_idx = 2321

    print(f"Start line content: {lines[start_idx].strip()}")
    print(f"End line content: {lines[end_idx].strip()}")

    # Assertions to make sure we are targeting the correct lines
    assert "DYNAMIC ADAPTIVE THEME OVERRIDES" in lines[start_idx], f"Start line mismatch: {lines[start_idx]}"
    assert lines[end_idx].strip() == "", f"End line mismatch: {lines[end_idx]}"

    # Delete lines from start_idx to end_idx (inclusive)
    new_lines = lines[:start_idx] + lines[end_idx+1:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("Successfully removed duplicate theme block from styles.css!")

if __name__ == "__main__":
    clean_css()
