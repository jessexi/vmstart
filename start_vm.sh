#!/bin/bash

# Configuration
IMAGE_URL="https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"
IMAGE_FILE="ubuntu-24.04-server-cloudimg-amd64.img"
RAW_IMAGE="ubuntu.raw"

echo "Checking environment..."

# 1. Check for RAW image
if [ ! -f "$RAW_IMAGE" ]; then
    echo "RAW image '$RAW_IMAGE' not found."
    
    # Check for Source Image
    if [ ! -f "$IMAGE_FILE" ]; then
        echo "Source image not found. Downloading..."
        curl -L -o "$IMAGE_FILE" "$IMAGE_URL"
    fi

    # Check for qemu-img
    if command -v qemu-img &> /dev/null; then
        echo "Converting $IMAGE_FILE to $RAW_IMAGE..."
        qemu-img convert -f qcow2 -O raw "$IMAGE_FILE" "$RAW_IMAGE"
        echo "Conversion complete."
    else
        echo "Error: 'qemu-img' is required to convert the QCOW2 image to RAW format."
        echo "Please install QEMU (e.g., 'brew install qemu') and run this script again."
        echo "Alternatively, manually convert the image to '$RAW_IMAGE'."
        exit 1
    fi
fi

# 2. Check for seed.iso
if [ ! -f "seed.iso" ]; then
    echo "Generating seed.iso..."
    if [ ! -d "seed" ]; then
        mkdir -p seed
        # Ensure config files exist (created by previous steps or manually)
        if [ ! -f "user-data" ]; then
            echo "Error: user-data not found."
            exit 1
        fi
        cp user-data meta-data seed/
    fi
    hdiutil makehybrid -o seed.iso -hfs -joliet -iso -default-volume-name cidata seed/
fi

# 3. Start VM
echo "Starting VM..."
echo "To exit the console, you may need to kill the process or use appropriate VM signals."
echo "Default user: ubuntu"
echo "Password: ubuntu"
echo "SSH Key: ./vm_key"
echo "----------------------------------------------------------------"

# Run the swift binary
# Ensure it is signed with entitlements (idempotent, fast)
codesign --sign - --entitlements vmstart.entitlements --force ./vmstart > /dev/null 2>&1

./vmstart
