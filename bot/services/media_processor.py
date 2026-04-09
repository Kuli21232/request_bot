from __future__ import annotations

import hashlib
import io
import math

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
            image_meta = self._analyze_image(preview_bytes or raw_bytes, width, height)
            sha256 = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None

            attachments.append(
                {
                    "type": "photo",
                    "file_id": photo.file_id,
                    "file_path": file.file_path,
                    "width": width,
                    "height": height,
                }
            )
            media_items.append(
                {
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
                    "storage_meta": {
                        "compression": "jpeg",
                        "quality": image_quality,
                        "max_side": image_max_side,
                        **image_meta,
                    },
                }
            )

        if message.document:
            attachments.append(
                {
                    "type": "document",
                    "file_id": message.document.file_id,
                    "file_name": message.document.file_name,
                    "mime_type": message.document.mime_type,
                }
            )
            media_items.append(
                {
                    "kind": "document",
                    "telegram_file_id": message.document.file_id,
                    "file_name": message.document.file_name,
                    "mime_type": message.document.mime_type,
                    "storage_meta": {"stored": "metadata_only"},
                }
            )

        if message.voice:
            attachments.append(
                {
                    "type": "voice",
                    "file_id": message.voice.file_id,
                    "duration": message.voice.duration,
                }
            )
            media_items.append(
                {
                    "kind": "voice",
                    "telegram_file_id": message.voice.file_id,
                    "duration_seconds": message.voice.duration,
                    "mime_type": "audio/ogg",
                    "storage_meta": {"stored": "metadata_only"},
                }
            )

        if message.audio:
            attachments.append(
                {
                    "type": "audio",
                    "file_id": message.audio.file_id,
                    "file_name": message.audio.file_name,
                }
            )
            media_items.append(
                {
                    "kind": "audio",
                    "telegram_file_id": message.audio.file_id,
                    "file_name": message.audio.file_name,
                    "duration_seconds": message.audio.duration,
                    "mime_type": message.audio.mime_type,
                    "storage_meta": {"stored": "metadata_only"},
                }
            )

        video = getattr(message, "video", None)
        if video:
            attachments.append(
                {
                    "type": "video",
                    "file_id": video.file_id,
                    "file_name": getattr(video, "file_name", None),
                    "mime_type": getattr(video, "mime_type", None),
                    "duration": video.duration,
                    "width": video.width,
                    "height": video.height,
                }
            )
            media_items.append(
                {
                    "kind": "video",
                    "telegram_file_id": video.file_id,
                    "file_name": getattr(video, "file_name", None),
                    "mime_type": getattr(video, "mime_type", None),
                    "duration_seconds": video.duration,
                    "width": video.width,
                    "height": video.height,
                    "storage_meta": {
                        "stored": "metadata_only",
                        "orientation": self._orientation(video.width, video.height),
                    },
                }
            )

        return attachments, media_items, {
            "has_photo": bool(message.photo),
            "has_document": bool(message.document),
            "has_voice": bool(message.voice),
            "has_audio": bool(message.audio),
            "has_video": bool(video),
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

    def _analyze_image(self, raw_bytes: bytes, width: int | None, height: int | None) -> dict:
        if not raw_bytes:
            return {}
        try:
            image = Image.open(io.BytesIO(raw_bytes))
            image = ImageOps.exif_transpose(image).convert("RGB")
            thumb = image.resize((8, 8)).convert("L")
            pixels = list(thumb.getdata())
            avg = sum(pixels) / len(pixels)
            phash = "".join("1" if value >= avg else "0" for value in pixels)

            rgb_thumb = image.resize((1, 1))
            avg_r, avg_g, avg_b = rgb_thumb.getpixel((0, 0))
            brightness = int((avg_r + avg_g + avg_b) / 3)

            return {
                "orientation": self._orientation(width, height),
                "aspect_ratio": round((width or 1) / (height or 1), 3) if width and height else None,
                "avg_color": {"r": int(avg_r), "g": int(avg_g), "b": int(avg_b)},
                "brightness": brightness,
                "brightness_bucket": self._brightness_bucket(brightness),
                "perceptual_hash": phash,
            }
        except Exception:
            return {
                "orientation": self._orientation(width, height),
            }

    def _orientation(self, width: int | None, height: int | None) -> str | None:
        if not width or not height:
            return None
        if math.isclose(width, height, rel_tol=0.02):
            return "square"
        return "landscape" if width > height else "portrait"

    def _brightness_bucket(self, brightness: int) -> str:
        if brightness < 70:
            return "dark"
        if brightness < 160:
            return "normal"
        return "bright"
