---
name: media-downloader
description: A tool to search and download royalty-free images and videos from Pixabay automatically.
license: MIT
---

# Media Downloader

## Instructions
Use this skill to download media content (images or videos) given a search query.
The skill uses a Python script located in `scripts/media_search_downloader.py`.

## Usage

### Install Dependencies
First, ensure dependencies are installed:
```bash
uv pip install -r requirements.txt
```

### Run the Downloader

**Basic Usage (Interactive Mode):**
```bash
python scripts/media_search_downloader.py
```

**Command Line Usage:**
Download images:
```bash
python scripts/media_search_downloader.py "search query" --limit 5
```

Download videos:
```bash
python scripts/media_search_downloader.py "search query" --type video --limit 3
```

**Advanced Search & Download Limits:**
Search for 20 items but only randomly download 5:
```bash
python scripts/media_search_downloader.py "search query" --search-limit 20 --download-limit 5
```

### File Structure
- `scripts/media_search_downloader.py`: Main entry point.
- `scripts/pixabay_service.py`: Pixabay API interaction service.
- `scripts/downloader.py`: General file downloader utility.

## Examples
Download 5 images of "cats":
```bash
python scripts/media_search_downloader.py "cats" --limit 5
```

Download 2 videos of "ocean":
```bash
python scripts/media_search_downloader.py "ocean" --type video --limit 2
```
