"""
Image Storage Utility

Handles saving, retrieving, and deleting Instagram images.
Supports local filesystem and S3 (future).

Features:
- Save images to local filesystem
- Download images from URLs
- Generate public URLs
- Delete images
- Directory management
- Security validation

Usage:
    storage = ImageStorage()
    path = await storage.save_image(image_bytes, "image.png", user_id=1)
    url = storage.get_image_url(path)
    await storage.delete_image(path)
"""

import os
import aiofiles
import asyncio
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
from loguru import logger
import httpx


class InvalidFilenameError(Exception):
    """Raised when filename contains invalid characters"""
    pass


class StorageError(Exception):
    """Base exception for storage operations"""
    pass


class ImageStorage:
    """Handles image storage operations for Instagram images"""

    def __init__(self):
        """Initialize image storage with configuration"""
        self.storage_backend = os.getenv("IMAGE_STORAGE_BACKEND", "local")

        # Get base directory dynamically (utils/ -> backend/)
        BASE_DIR = Path(__file__).resolve().parent.parent
        self.base_path = Path(
            os.getenv(
                "IMAGE_STORAGE_PATH",
                str(BASE_DIR / "storage" / "instagram_images")
            )
        )

        self.max_file_size_mb = int(os.getenv("MAX_IMAGE_FILE_SIZE_MB", "8"))
        self.base_url = os.getenv("IMAGE_BASE_URL", "/api/images/instagram")

        # Ensure base directory exists
        self._ensure_directory(self.base_path)

    async def save_image(
        self,
        image_bytes: bytes,
        filename: str,
        user_id: Optional[int] = None
    ) -> Path:
        """
        Save image bytes to storage

        Args:
            image_bytes: Image data as bytes
            filename: Filename to save as
            user_id: Optional user ID for organizing files

        Returns:
            Path: Full path to saved image

        Raises:
            InvalidFilenameError: Invalid filename
            StorageError: Failed to save
        """
        # Validate filename
        self._validate_filename(filename)

        # Check file size
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            raise StorageError(
                f"Image size ({size_mb:.2f}MB) exceeds limit ({self.max_file_size_mb}MB)"
            )

        # Determine save path
        if user_id:
            save_dir = self.base_path / str(user_id)
        else:
            save_dir = self.base_path / "shared"

        # Ensure directory exists
        self._ensure_directory(save_dir)

        # Full path
        save_path = save_dir / filename

        # Save file
        try:
            async with aiofiles.open(save_path, 'wb') as f:
                await f.write(image_bytes)

            logger.info(
                f"Saved image to {save_path}",
                extra={"size_mb": size_mb, "user_id": user_id}
            )

            return save_path

        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise StorageError(f"Failed to save image: {str(e)}")

    async def download_from_url(
        self,
        url: str,
        filename: str,
        user_id: Optional[int] = None
    ) -> Path:
        """
        Download image from URL and save to storage

        Args:
            url: Image URL to download
            filename: Filename to save as
            user_id: Optional user ID

        Returns:
            Path: Full path to saved image

        Raises:
            StorageError: Download or save failed
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                image_bytes = response.content

                return await self.save_image(
                    image_bytes=image_bytes,
                    filename=filename,
                    user_id=user_id
                )

        except httpx.HTTPError as e:
            raise StorageError(f"Failed to download image: {str(e)}")

    def get_image_url(self, image_path: Union[str, Path]) -> str:
        """
        Generate public URL for an image

        Args:
            image_path: Path to image file

        Returns:
            str: Public URL
        """
        path = Path(image_path)

        # Get relative path from base_path
        try:
            relative_path = path.relative_to(self.base_path)
            url = f"{self.base_url}/{relative_path}"
            return url
        except ValueError:
            # Path is not relative to base_path
            logger.warning(f"Path {path} is not within base storage path")
            return f"{self.base_url}/{path.name}"

    async def delete_image(self, image_path: Union[str, Path]) -> bool:
        """
        Delete an image from storage

        Args:
            image_path: Path to image file

        Returns:
            bool: True if deleted, False if not found

        Raises:
            StorageError: Failed to delete
        """
        path = Path(image_path)

        if not path.exists():
            logger.warning(f"Image not found: {path}")
            return False

        try:
            path.unlink()
            logger.info(f"Deleted image: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete image: {str(e)}")
            raise StorageError(f"Failed to delete image: {str(e)}")

    async def get_image_metadata(self, image_path: Union[str, Path]) -> dict:
        """
        Get metadata for an image

        Args:
            image_path: Path to image file

        Returns:
            dict: Image metadata
        """
        path = Path(image_path)

        if not path.exists():
            raise StorageError(f"Image not found: {path}")

        stat = path.stat()

        return {
            "path": str(path),
            "filename": path.name,
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def _validate_filename(self, filename: str):
        """
        Validate filename for security

        Args:
            filename: Filename to validate

        Raises:
            InvalidFilenameError: Invalid filename
        """
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise InvalidFilenameError("Filename contains invalid characters")

        # Check for empty
        if not filename or filename.strip() == "":
            raise InvalidFilenameError("Filename cannot be empty")

        # Check extension
        allowed_extensions = [".png", ".jpg", ".jpeg", ".gif"]
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise InvalidFilenameError(
                f"Invalid file extension. Allowed: {allowed_extensions}"
            )

    def _ensure_directory(self, directory: Path):
        """
        Ensure directory exists, create if not

        Args:
            directory: Directory path to ensure
        """
        directory.mkdir(parents=True, exist_ok=True)

    async def get_storage_stats(self, user_id: Optional[int] = None) -> dict:
        """
        Get storage statistics

        Args:
            user_id: Optional user ID to get stats for

        Returns:
            dict: Storage statistics
        """
        if user_id:
            target_dir = self.base_path / str(user_id)
        else:
            target_dir = self.base_path

        if not target_dir.exists():
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "avg_size_mb": 0.0
            }

        # Count files and sizes
        total_files = 0
        total_size = 0

        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size

        total_size_mb = total_size / (1024 * 1024)
        avg_size_mb = total_size_mb / total_files if total_files > 0 else 0.0

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size_mb, 2),
            "avg_size_mb": round(avg_size_mb, 2),
            "directory": str(target_dir)
        }

    async def cleanup_old_images(self, days_old: int = 30) -> int:
        """
        Delete images older than specified days

        Args:
            days_old: Delete images older than this many days

        Returns:
            int: Number of images deleted
        """
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        deleted_count = 0

        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Cleaned up old image: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")

        logger.info(f"Cleanup complete: deleted {deleted_count} old images")
        return deleted_count
