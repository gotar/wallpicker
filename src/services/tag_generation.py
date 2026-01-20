"""Tag Generation Service using AI for image recognition."""

import asyncio
import shutil
from pathlib import Path

from services.base import BaseService


class TagGenerationError(Exception):
    """Exception raised when tag generation fails."""

    pass


class TagGenerationService(BaseService):
    """Service for generating AI tags for images using CLIP-based recognition."""

    def __init__(self):
        """Initialize tag generation service."""
        super().__init__()
        self._clip_anytorch_available: bool | None = None
        self._clip_cpp_available: bool | None = None

    def is_available(self) -> bool:
        """Check if any tag generation tool is available.

        Returns:
            True if at least one tool is available
        """
        return self._get_tool() is not None

    def _get_tool(self) -> str | None:
        """Get the first available tag generation tool.

        Returns:
            Tool name or None if no tool available
        """
        if self._check_clip_anytorch():
            return "clip-anytorch"
        if self._check_clip_cpp():
            return "clip-cpp"
        return None

    def _check_clip_anytorch(self) -> bool:
        """Check if clip-anytorch Python module is available."""
        if self._clip_anytorch_available is not None:
            return self._clip_anytorch_available
        try:
            import clip  # noqa: F401
            import torch  # noqa: F401

            self._clip_anytorch_available = True
        except ImportError:
            self._clip_anytorch_available = False
        return self._clip_anytorch_available
        try:
            import clip_anytorch  # noqa: F401

            self._clip_anytorch_available = True
        except ImportError:
            self._clip_anytorch_available = False
        return self._clip_anytorch_available

    def _check_clip_cpp(self) -> bool:
        """Check if clip-cpp image-search is available."""
        if self._clip_cpp_available is not None:
            return self._clip_cpp_available
        # Check for clip-cpp binary
        self._clip_cpp_available = (
            shutil.which("clip-cpp") is not None or shutil.which("image-search") is not None
        )
        return self._clip_cpp_available

    async def generate_tags_async(self, image_path: Path) -> tuple[list[str], dict]:
        """Generate tags for an image asynchronously.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (tags list, confidence dict)

        Raises:
            TagGenerationError: If no tool is available or generation fails
        """
        tool = self._get_tool()
        if tool is None:
            raise TagGenerationError(
                "No tag generation tool available. Install clip-anytorch or clip-cpp."
            )

        if tool == "clip-anytorch":
            return await self._generate_clip_anytorch(image_path)
        elif tool == "clip-cpp":
            return await self._generate_clip_cpp(image_path)

        raise TagGenerationError(f"Unknown tool: {tool}")

    async def _generate_clip_anytorch(self, image_path: Path) -> tuple[list[str], dict]:
        """Generate tags using CLIP (clip-anytorch package) Python API.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (tags list, confidence dict)
        """
        try:
            import clip
            import torch
            from PIL import Image

            def run_model():
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model, preprocess = clip.load("ViT-B/32", device=device)

                image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

                common_tags = [
                    "nature",
                    "mountain",
                    "forest",
                    "beach",
                    "ocean",
                    "sunset",
                    "sunrise",
                    "city",
                    "building",
                    "sky",
                    "cloud",
                    "tree",
                    "flower",
                    "animal",
                    "cat",
                    "dog",
                    "bird",
                    "landscape",
                    "portrait",
                    "abstract",
                    "minimalist",
                    "dark",
                    "light",
                    "blue",
                    "green",
                    "red",
                    "black",
                    "white",
                    "water",
                    "snow",
                    "desert",
                    "jungle",
                    "garden",
                    "park",
                    "street",
                    "night",
                    "day",
                    "morning",
                    "evening",
                    "anime",
                    "digital art",
                    "painting",
                    "photography",
                    "3d render",
                    "wallpaper",
                    "scenery",
                    "lake",
                ]

                text = clip.tokenize(common_tags).to(device)

                with torch.no_grad():
                    image_features = model.encode_image(image)
                    text_features = model.encode_text(text)

                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    text_features /= text_features.norm(dim=-1, keepdim=True)

                    similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                    values, indices = similarity[0].topk(len(common_tags))

                results = {common_tags[idx]: float(values[i]) for i, idx in enumerate(indices)}
                return results

            results = await asyncio.to_thread(run_model)
            return self._parse_clip_anytorch_python(results)

        except Exception as e:
            self.log_warning(f"clip-anytorch failed for {image_path}: {e}")
            raise TagGenerationError(f"clip-anytorch failed: {e}") from None

    def _parse_clip_anytorch_python(self, results: dict) -> tuple[list[str], dict]:
        """Parse clip-anytorch Python API results.

        Args:
            results: Dictionary with tag scores (0-1 range)

        Returns:
            Tuple of (tags list, confidence dict)
        """
        tags = []
        confidence = {}

        for tag, score in results.items():
            if score >= 0.05:
                tags.append(tag.lower())
                confidence[tag.lower()] = float(score)

        sorted_tags = sorted(tags, key=lambda t: confidence[t], reverse=True)
        return sorted_tags[:10], confidence

    async def _generate_clip_cpp(self, image_path: Path) -> tuple[list[str], dict]:
        """Generate tags using clip-cpp CLI.

        Uses the image-search tool with predefined tags.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (tags list, confidence dict)
        """
        # Predefined tag categories for clip-cpp
        common_tags = [
            "nature",
            "mountain",
            "forest",
            "beach",
            "ocean",
            "sunset",
            "sunrise",
            "city",
            "building",
            "sky",
            "cloud",
            "tree",
            "flower",
            "animal",
            "cat",
            "dog",
            "bird",
            "landscape",
            "portrait",
            "abstract",
            "minimalist",
            "dark",
            "light",
            "blue",
            "green",
            "red",
            "black",
            "white",
            "water",
            "snow",
            "desert",
            "jungle",
            "garden",
            "park",
            "street",
            "night",
            "day",
            "morning",
            "evening",
            "anime",
            "digital art",
            "painting",
            "photography",
            "3d render",
            "wallpaper",
            "scenery",
            "ocean",
            "lake",
        ]

        try:
            # Build the query string
            query = " ".join(f'"{tag}"' for tag in common_tags)

            proc = await asyncio.create_subprocess_exec(
                "image-search",
                "-q",
                query,
                str(image_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                self.log_warning(f"clip-cpp failed for {image_path}: {stderr.decode()}")
                raise TagGenerationError(f"clip-cpp failed: {stderr.decode()}")

            output = stdout.decode().strip()
            return self._parse_clip_cpp_output(output)

        except FileNotFoundError:
            self._clip_cpp_available = False
            raise TagGenerationError("clip-cpp/image-search not found in PATH") from None

    def _parse_clip_cpp_output(self, output: str) -> tuple[list[str], dict]:
        """Parse clip-cpp/image-search output.

        Example output:
        nature: 0.85
        sunset: 0.72
        mountain: 0.68

        Args:
            output: Raw CLI output

        Returns:
            Tuple of (tags list, confidence dict)
        """
        tags = []
        confidence = {}

        if not output:
            return tags, confidence

        try:
            for line in output.split("\n"):
                line = line.strip()
                if ":" in line:
                    tag, conf = line.split(":", 1)
                    tag = tag.strip().lower()
                    conf_value = float(conf.strip())

                    if conf_value >= 0.3:  # Threshold for including tag
                        tags.append(tag)
                        confidence[tag] = conf_value
        except (ValueError, AttributeError) as e:
            self.log_warning(f"Failed to parse clip-cpp output: {e}")

        return tags, confidence

    def generate_tags_sync(self, image_path: Path) -> tuple[list[str], dict]:
        """Generate tags synchronously (blocking).

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (tags list, confidence dict)
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.generate_tags_async(image_path))
            finally:
                loop.close()
        except TagGenerationError:
            return [], {}
