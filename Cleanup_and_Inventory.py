import os
import re
import json

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_DIR = "papers"
INVENTORY_FILE = "papers.json"

# Keep these file types in the final analysis. Files like 'gt' or 'er' 
# will be bypassed for question/answer parsing but kept intact on disk.
TARGET_DOC_TYPES = ["qp", "ms"]


def parse_filename(filename):
    """
    Extracts metadata from standard CAIE filenames.
    Example: 5090_s24_qp_11.pdf -> session_code='s24', doc_type='qp', variant='11'
    """
    # Regex matching: syllabus_session_doctype_variant.pdf (variant is optional)
    pattern = re.compile(r"5090_([wsm]\d{2})_(qp|ms|gt|er|ci|ir)_?(\d+)?\.pdf", re.IGNORECASE)
    match = pattern.match(filename)
    if not match:
        return None
        
    session_code = match.group(1).lower()
    doc_type = match.group(2).lower()
    variant = match.group(3) or "0"
    
    # Calculate absolute year and session name
    yy = int(session_code[1:])
    year = 1900 + yy if yy >= 80 else 2000 + yy
    session_char = session_code[0]
    session_name = {"w": "Oct-Nov", "s": "May-Jun", "m": "Feb-Mar"}.get(session_char, session_code)
    
    return {
        "year": year,
        "session": session_name,
        "session_code": session_code,
        "doc_type": doc_type,
        "variant": variant
    }


def clean_and_inventory():
    print("=" * 60)
    print("  BioSearch — Segment 1: Verification & Cleanup")
    print("=" * 60)
    
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Error: The directory '{INPUT_DIR}' does not exist.")
        return
        
    deleted_empty_count = 0
    total_scanned_files = 0
    
    # Map to hold paired files: {(year, session_code, variant): {"qp": path, "ms": path}}
    pairs = {}
    unpaired_files = []

    # Walk through the papers directory
    for root, _, files in os.walk(INPUT_DIR):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue
                
            file_path = os.path.join(root, file)
            total_scanned_files += 1
            
            # 1. Clean up empty/corrupt files
            try:
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    print(f"🗑 [Removed Empty File] {file}")
                    deleted_empty_count += 1
                    continue
            except OSError as e:
                print(f"⚠ Could not access file {file}: {e}")
                continue

            # 2. Extract Metadata
            meta = parse_filename(file)
            if not meta:
                continue
                
            # If the file is not a Target Document Type (e.g., gt, er), we skip mapping
            if meta["doc_type"] not in TARGET_DOC_TYPES:
                continue
                
            key = (meta["year"], meta["session"], meta["variant"])
            if key not in pairs:
                pairs[key] = {
                    "year": meta["year"],
                    "session": meta["session"],
                    "session_code": meta["session_code"],
                    "variant": meta["variant"],
                    "qp_path": None,
                    "ms_path": None
                }
                
            if meta["doc_type"] == "qp":
                pairs[key]["qp_path"] = file_path
            elif meta["doc_type"] == "ms":
                pairs[key]["ms_path"] = file_path

    # 3. Assess Pairs and Filter Complete Matches
    complete_inventory = []
    
    for key, data in pairs.items():
        if data["qp_path"] and data["ms_path"]:
            complete_inventory.append(data)
        else:
            # Keep track of orphaned/unpaired papers
            unpaired_files.append(data)

    # Merge complete pairs and unpaired files (putting unpaired ones at the end)
    full_inventory = complete_inventory + unpaired_files

    # 4. Save Full Inventory to JSON
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(full_inventory, f, indent=2, ensure_ascii=False)

    # 5. Output Summary Report
    print("-" * 60)
    print(f"📊 Summary Report:")
    print(f"   - Total PDF files scanned:      {total_scanned_files}")
    print(f"   - Deleted empty/corrupt files:  {deleted_empty_count}")
    print(f"   - Successfully matched pairs:   {len(complete_inventory)}")
    print(f"   - Unpaired (QP or MS missing):  {len(unpaired_files)}")
    print(f"   - Total items saved to JSON:    {len(full_inventory)}")
    print("-" * 60)
    
    if len(full_inventory) > 0:
        print(f"✅ Created catalog: '{INVENTORY_FILE}' (includes complete pairs and unpaired files)")
        
        # Print matched pairs preview
        if len(complete_inventory) > 0:
            print("\nMatched Pair Preview:")
            for entry in complete_inventory[:5]:
                print(f"   • {entry['year']} | {entry['session']} | Variant {entry['variant']}")
                print(f"     QP: {os.path.basename(entry['qp_path'])}")
                print(f"     MS: {os.path.basename(entry['ms_path'])}")
            if len(complete_inventory) > 5:
                print(f"   ... and {len(complete_inventory) - 5} more.")
    else:
        print("⚠ No valid QP or MS files found on disk.")
        
    # Detailed display for unpaired files
    if len(unpaired_files) > 0:
        print("\nUnpaired Files Details:")
        for entry in unpaired_files:
            missing_parts = []
            present_file = None
            
            if not entry["qp_path"]:
                missing_parts.append("Question Paper (QP)")
            else:
                present_file = os.path.basename(entry["qp_path"])
                
            if not entry["ms_path"]:
                missing_parts.append("Mark Scheme (MS)")
            else:
                present_file = os.path.basename(entry["ms_path"])
                
            print(f"   • {entry['year']} | {entry['session']} | Variant {entry['variant']}")
            print(f"     Present: {present_file}")
            print(f"     Missing: {', '.join(missing_parts)}")
    print("=" * 60)


if __name__ == "__main__":
    clean_and_inventory()