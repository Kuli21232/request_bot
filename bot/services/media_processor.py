from __future__ import annotations

import hashlib
import io

from aiogram import Bot
from aiogram.types import Message
from PIL import Image, ImageOps


class MediaProcessor:
    async def extract(self, message: Message, bot: Bot, *, media_policy: dict | None = None) -> tuple[list[dict], list[dict], dict]:
        attachments: list[dict] = []
        media_items: list[dict] = []
        policy = media_policy or {}
        image_max_side = int(policy.get("image_max_side", 1280))
        image_quality = int(policy.get("image_quality", 60))

        if message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            downloaded = await bot.download_file(file.file_path)
            raw_bytes = downloaded.read() if downloaded else b""
            preview_bytes, width, height = self._compress_image(raw_bytes, image_max_side, image_quality)
            sha256 = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None

            attachments.append({
                "type": "photo",
                "file_id": photo.file_id,
                "file_path": file.file_path,
                "width": width,
                "height": height,
            })
            media_items.append({
                "kind": "photo",
                "telegram_file_id": photo.file_id,
                "telegram_file_path": file.file_path,
                "mime_type": "image/jpeg",
                "sha256": sha256,
                "original_size": len(raw_bytes) if raw_bytes else None,
                "compressed_size": len(preview_bytes) if preview_bytes else None,
                "width": width,
                "height": height,
                "preview_bytes": preview_bytes,
                "storage_meta": {"compression": "jpeg", "quality": image_quality, "max_side": image_max_side},
            })

        if message.document:
            attachments.append({
                "type": "document",
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "mime_type": message.document.mime_type,
            })
            media_items.append({
                "kind": "document",
                "telegram_file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "mime_type": message.document.mime_type,
                "storage_meta": {"stored": "metadata_only"},
            })

        if message.voice:
            attachments.append({
                "type": "voice",
                "file_id": message.voice.file_id,
                "duration": message.voice.duration,
            })
            media_items.append({
                "kind": "voice",
                "telegram_file_id": message.voice.file_id,
                "duration_seconds": message.voice.duration,
                "mime_type": "audio/ogg",
                "storage_meta": {"stored": "metadata_only"},
            })

        if message.audio:
            attachments.append({
                "type": "audio",
                "file_id": message.audio.file_id,
                "file_name": message.audio.file_name,
            })
            media_items.append({
                "kind": "audio",
                "telegram_file_id": message.audio.file_id,
                "file_name": message.audio.file_name,
                "duration_seconds": message.audio.duration,
                "mime_type": message.audio.mime_type,
                "storage_meta": {"stored": "metadata_only"},
            })

        return attachments, media_items, {
            "has_photo": bool(message.photo),
            "has_document": bool(message.document),
            "has_voice": bool(message.voice),
            "has_audio": bool(message.audio),
            "has_video": bool(getattr(message, "video", None)),
        }

    def _compress_image(self, raw_bytes: bytes, max_side: int, quality: int) -> tuple[bytes | None, int | None, int | None]:
        if not raw_bytes:
            return None, None, None
        image = Image.open(io.BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((max_side, max_side))
        width, height = image.size
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", optimize=True, quality=quality)
        return buffer.getvalue(), width, height
