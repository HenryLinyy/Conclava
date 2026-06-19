"""Vision evidence extraction through Ollama native multimodal chat."""

from __future__ import annotations

import re

from conclava.config import FusionConfig
from conclava.models import OllamaClient
from conclava.schemas import ParsedAgentTask
from conclava.vision import VisionEvidence, estimate_base64_size_mb


VISION_FAST_SYSTEM = """Extract concise, auditable visual evidence from the supplied image(s).
Do not call tools. Do not infer unseen facts. Return sections:
Summary
Visible Text
UI Elements
Tables
Charts
Warnings
Confidence"""


VISION_PRO_SYSTEM = """Extract detailed, auditable visual evidence from the supplied image(s).
Do not call tools. Do not perform file or browser actions. Return sections:
Summary
Visible Text
Detailed OCR
UI Elements
Layout
Tables
Charts
Visual Coding Clues
Possible Implementation
Warnings
Confidence"""


class VisionProcessor:
    """Produces VisionEvidence before downstream tool or heavy reasoning."""

    def __init__(self, config: FusionConfig, ollama: OllamaClient):
        self.config = config
        self.ollama = ollama

    async def extract_evidence(
        self, task: ParsedAgentTask, profile: str
    ) -> list[VisionEvidence]:
        """Extract visual evidence for supported inline base64 image inputs."""
        model = self._model_for_profile(profile)
        inline_images = [
            image.data_base64 for image in task.images if image.data_base64
        ]
        warnings: list[str] = []

        for image in task.images:
            if image.data_base64:
                size_mb = estimate_base64_size_mb(image.data_base64)
                if size_mb > self.config.vision_max_image_mb:
                    warnings.append(
                        f"image omitted because {size_mb:.1f}MB exceeds VISION_MAX_IMAGE_MB={self.config.vision_max_image_mb}"
                    )
            elif image.url:
                warnings.append(
                    "remote image URL preserved but not downloaded; inline base64 is required for local vision"
                )
            elif image.local_path:
                warnings.append(
                    "local image paths are disabled by default; inline base64 is required"
                )

        inline_images = [
            data
            for data in inline_images
            if estimate_base64_size_mb(data) <= self.config.vision_max_image_mb
        ][: self.config.vision_max_images]

        if not inline_images:
            return [
                VisionEvidence(
                    model=model,
                    profile=profile,
                    summary="No supported inline image data was available for local vision extraction.",
                    warnings=warnings or ["inline base64 image data is required"],
                    confidence=0.0,
                    raw_text="",
                )
            ]

        prompt = VISION_PRO_SYSTEM if profile == "vision-pro" else VISION_FAST_SYSTEM
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": task.text
                or "Extract visual evidence from the supplied image.",
                "images": inline_images,
            },
        ]
        try:
            response = self.ollama.native_chat_completion(
                model=model,
                messages=messages,
                max_tokens=self.config.vision_max_tokens,
                stream=False,
                temperature=0.0,
                think=False,
            )
        except Exception:
            fallback = self.config.model_vision_pro_fallback
            if profile != "vision-pro" or not fallback:
                raise
            response = self.ollama.native_chat_completion(
                model=fallback,
                messages=messages,
                max_tokens=self.config.vision_max_tokens,
                stream=False,
                temperature=0.0,
                think=False,
            )
            model = fallback

        raw_text = response.get("message", {}).get("content", "")
        if not isinstance(raw_text, str):
            raw_text = ""
        return [self._evidence_from_text(model, profile, raw_text, warnings)]

    def _model_for_profile(self, profile: str) -> str:
        if profile == "vision-fast":
            return self.config.model_vision_fast
        return self.config.model_vision_pro

    def _evidence_from_text(
        self,
        model: str,
        profile: str,
        raw_text: str,
        warnings: list[str],
    ) -> VisionEvidence:
        summary = self._extract_section(raw_text, "Summary") or raw_text.strip()
        visible_text = self._extract_section(raw_text, "Visible Text")
        confidence = self._extract_confidence(raw_text)
        return VisionEvidence(
            model=model,
            profile=profile,
            summary=summary,
            visible_text=visible_text,
            warnings=warnings,
            confidence=confidence,
            raw_text=raw_text,
        )

    def _extract_section(self, text: str, heading: str) -> str | None:
        pattern = re.compile(
            rf"{re.escape(heading)}\s*:?\s*(?P<body>.*?)(?:\n[A-Z][A-Za-z ]+\s*:|\Z)",
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            return None
        return match.group("body").strip()

    def _extract_confidence(self, text: str) -> float | None:
        match = re.search(r"Confidence\s*:?\s*([01](?:\.\d+)?)", text, re.IGNORECASE)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None
