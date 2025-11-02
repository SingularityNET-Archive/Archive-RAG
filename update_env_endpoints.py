#!/usr/bin/env python3
"""Update .env file to use new HuggingFace Inference Providers API endpoint."""

from pathlib import Path
import re

env_path = Path(".env")

if not env_path.exists():
    print("❌ .env file not found!")
    exit(1)

print(f"Reading .env file: {env_path.absolute()}")
print()

# Read current content
with open(env_path, 'r') as f:
    content = f.read()

# Check for old endpoint
old_endpoint = "https://api-inference.huggingface.co"
new_endpoint = "https://router.huggingface.co/hf-inference"

has_old_endpoint = old_endpoint in content

if not has_old_endpoint:
    print("✓ .env file already uses the new endpoint or doesn't have HuggingFace URLs")
    exit(0)

print("Found deprecated endpoint in .env file:")
print(f"  Old: {old_endpoint}")
print(f"  New: {new_endpoint}")
print()

# Create backup
backup_path = env_path.with_suffix('.env.backup')
print(f"Creating backup: {backup_path}")
with open(backup_path, 'w') as f:
    f.write(content)

# Replace old endpoint with new endpoint
updated_content = content.replace(old_endpoint, new_endpoint)

# Count replacements
old_count = content.count(old_endpoint)
new_count = updated_content.count(new_endpoint)

if old_count > 0:
    print(f"Replacing {old_count} occurrence(s)...")
    
    # Write updated content
    with open(env_path, 'w') as f:
        f.write(updated_content)
    
    print(f"✓ .env file updated!")
    print(f"  Backup saved to: {backup_path}")
    print(f"  Replaced: {old_count} occurrence(s)")
    print()
    
    # Show what changed
    print("Changes made:")
    for line in updated_content.splitlines():
        if new_endpoint in line and old_endpoint not in line:
            print(f"  {line}")
    
    print()
    print("✓ Migration complete!")
    print("  Your .env file now uses the new HuggingFace Inference Providers API")
else:
    print("No changes needed")

