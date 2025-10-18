# Model Files

This directory contains TTS model files that are too large to store in Git.

## Required Models

### Lasinya Model (1.7GB)

**Location:** `code/models/Lasinya/model.pth`

**Download Options:**

1. **From Hugging Face** (if available):

   ```bash
   # Download from Hugging Face model hub
   # huggingface-cli download <model-id> --local-dir code/models/Lasinya/
   ```

2. **From Google Drive/Dropbox** (team setup):

   - Contact repository owner for download link
   - Place downloaded `model.pth` in `code/models/Lasinya/`

3. **From External Storage:**
   - Store on team cloud storage (Google Drive, Dropbox, S3)
   - Document download instructions here

## Git LFS Alternative (Optional)

For team collaboration, consider using Git LFS:

```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "code/models/**/*.pth"

# Commit and push
git add .gitattributes
git commit -m "Configure Git LFS for model files"
git push
```

## Model File Formats

The following formats are excluded from Git (via .gitignore):

- `*.pth` - PyTorch model files
- `*.bin` - Binary model files
- `*.onnx` - ONNX model files
- `*.safetensors` - Safetensors format

## Setup Instructions

1. Clone the repository
2. Download required model files (see above)
3. Place them in the correct directories
4. Verify with: `ls -lh code/models/Lasinya/model.pth`

Expected output: `1.7G model.pth`
