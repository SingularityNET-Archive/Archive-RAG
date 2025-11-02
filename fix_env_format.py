#!/usr/bin/env python3
"""Fix .env file format - remove 'export' and add missing variables."""

from pathlib import Path

env_path = Path(".env")

if not env_path.exists():
    print("❌ .env file not found!")
    exit(1)

print(f"Reading .env file: {env_path.absolute()}")
print()

# Read current content
with open(env_path, 'r') as f:
    content = f.read()

# Check if it has 'export' statements
has_export = 'export ' in content
has_processing_mode = 'ARCHIVE_RAG_PROCESSING_MODE' in content

print(f"Current status:")
print(f"  Has 'export' statements: {has_export}")
print(f"  Has ARCHIVE_RAG_PROCESSING_MODE: {has_processing_mode}")
print()

if has_export or not has_processing_mode:
    print("Fixing .env file format...")
    
    # Process lines
    processed_lines = []
    has_processing_mode_line = False
    
    for line in content.splitlines():
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            processed_lines.append(line)
            continue
        
        # Skip comments
        if stripped.startswith('#'):
            processed_lines.append(line)
            continue
        
        # Remove 'export' keyword
        if stripped.startswith('export '):
            line = stripped.replace('export ', '', 1)
            stripped = line.strip()
        
        # Check if this is PROCESSING_MODE
        if 'ARCHIVE_RAG_PROCESSING_MODE' in stripped:
            has_processing_mode_line = True
            # Ensure it's set to remote if embeddings are enabled
            if 'ARCHIVE_RAG_REMOTE_EMBEDDINGS=true' in content or 'ARCHIVE_RAG_REMOTE_EMBEDDINGS=true' in content.upper():
                # Update or add processing mode
                if '=' not in stripped or 'local' in stripped.lower():
                    line = 'ARCHIVE_RAG_PROCESSING_MODE=remote'
            processed_lines.append(line)
        else:
            processed_lines.append(line)
    
    # Add ARCHIVE_RAG_PROCESSING_MODE if missing
    if not has_processing_mode_line:
        print("  Adding missing ARCHIVE_RAG_PROCESSING_MODE=remote")
        # Add at the beginning after comments
        header = []
        body = []
        for line in processed_lines:
            if line.strip().startswith('#') or not line.strip():
                header.append(line)
            else:
                body.append(line)
        processed_lines = header + ['ARCHIVE_RAG_PROCESSING_MODE=remote', ''] + body
    
    # Write fixed content
    backup_path = env_path.with_suffix('.env.bak')
    print(f"  Creating backup: {backup_path}")
    with open(backup_path, 'w') as f:
        f.write(content)
    
    with open(env_path, 'w') as f:
        f.write('\n'.join(processed_lines))
    
    print("✓ .env file fixed!")
    print(f"  Backup saved to: {backup_path}")
    print()
    print("Updated .env file:")
    with open(env_path, 'r') as f:
        print(f.read())
else:
    print("✓ .env file format looks correct!")

