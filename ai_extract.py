"""
ai_extract.py - ask an AI model (with vision) to read a receipt.

Steps:
  1. Turn the file into image(s)        -> file_to_images()
  2. Send the image(s) + instructions   -> extract_with_ai()
  3. Parse the JSON reply with pydantic -> Receipt.model_validate()

Settings (environment variables):
  OPENAI_API_KEY   your key (required for this mode)
  OPENAI_BASE_URL  optional, for any OpenAI-compatible provider
  MODEL            optional, defaults to gpt-4o-mini
"""
import base64
import io
import json
import os
from pathlib import Path

import pdfplumber
from openai import OpenAI

from schema import Receipt

# The instructions we give the AI. We include the JSON schema so it knows
# exactly which fields to return.
PROMPT = f"""You are a receipt reader. Look at the receipt image and return ONLY a JSON object
that matches this JSON schema:

{json.dumps(Receipt.model_json_schema())}

Rules:
- date must be YYYY-MM-DD.
- currency must be a 3-letter code like USD or EUR.
- numbers are plain numbers (12.5, not "$12.50").
- use null for anything you cannot find. Do not invent values.
"""


def file_to_images(path):
    """Return a list of PNG images (as bytes). PDFs become one image per page."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        images = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:3]:  # receipts are short; 3 pages is plenty
                buffer = io.BytesIO()
                page.to_image(resolution=200).original.save(buffer, format="PNG")
                images.append(buffer.getvalue())
        return images
    return [path.read_bytes()]  # already an image (png/jpg)


def extract_with_ai(path, client=None):
    """Read one receipt file with the AI and return a validated Receipt."""
    client = client or OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
    model = os.getenv("MODEL", "gpt-4o-mini")

    # Build the message: our text instructions + each image as a data URL.
    content = [{"type": "text", "text": PROMPT}]
    for img in file_to_images(path):
        b64 = base64.b64encode(img).decode()
        mime = "image/jpeg" if Path(path).suffix.lower() in (".jpg", ".jpeg") else "image/png"
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},  # ask for JSON only
        temperature=0,                             # same input -> same answer
    )
    reply = response.choices[0].message.content
    return Receipt.model_validate(json.loads(reply))  # raises if the shape is wrong
