# Math explanation video pipeline — base image (Manim + LaTeX are heavy; extend as needed).
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    fonts-noto-cjk \
    texlive-latex-extra \
    texlive-fonts-recommended \
    dvipng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"

ENV MANIM_VIDEO_GEN_CJK_FONT=Noto Sans CJK KR

# Default: override at runtime with API keys and problem text
CMD ["python", "-m", "manim_video_gen", "--help"]
