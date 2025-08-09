# Copilot Instructions for Anime Cars Generator

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This is a Python script project that generates anime-style car images using Stable Diffusion API and uploads them to PixelDrain. 

## Project Context
- Uses local Stable Diffusion API (http://127.0.0.1:7860)
- Generates images in batches (packs)
- Uploads generated content to PixelDrain
- Includes error handling and logging
- Windows-specific implementation with audio notifications

## Dependencies
- requests: HTTP API calls
- base64: Image data handling  
- winsound: Audio notifications
- Standard library: os, time, datetime, sys, shutil

## Key Features
- Batch image generation
- Pack creation and zipping
- Cloud upload functionality
- Comprehensive logging
- Error resilience
