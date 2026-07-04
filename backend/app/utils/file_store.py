import os
import shutil
import hashlib
from fastapi import UploadFile
from app.config.settings import settings


class FileStore:
    """Manages raw document file storage on the local file system."""

    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def get_file_path(self, filename: str) -> str:
        """Returns absolute path for a filename in the upload directory."""
        return os.path.abspath(os.path.join(self.upload_dir, filename))

    async def save_file(self, file: UploadFile, custom_filename: str = None) -> str:
        """Saves an uploaded file to the upload directory. Returns the absolute file path."""
        filename = custom_filename or file.filename
        # Ensure name is safe (simple normalization)
        filename = os.path.basename(filename)
        file_path = self.get_file_path(filename)
        
        # Reset file read position just in case
        await file.seek(0)
        
        # Write file in chunks
        with open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(content)
                
        return file_path

    def delete_file(self, file_path: str) -> bool:
        """Deletes a file if it exists."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False

    def compute_checksum(self, file_path: str) -> str:
        """Computes SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
