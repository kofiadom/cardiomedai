import os
import base64
import json
from typing import Dict, Tuple
from PIL import Image
from io import BytesIO
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure OpenAI Configuration
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")

# Define the Pydantic model for structured output
class BloodPressureReading(BaseModel):
    """
    Structured model for blood pressure readings extracted from images.
    """
    systolic: int = Field(
        description="The systolic blood pressure reading (top number)",
        ge=0, le=300
    )
    diastolic: int = Field(
        description="The diastolic blood pressure reading (bottom number)",
        ge=0, le=200
    )
    pulse: int = Field(
        description="The pulse rate in beats per minute",
        ge=0, le=250
    )

class OCRProcessor:
    def __init__(self):
        """Initialize the OCR processor for blood pressure readings."""
        # Check for required environment variables
        missing_vars = []
        if not AZURE_API_KEY:
            missing_vars.append("AZURE_API_KEY")
        if not AZURE_ENDPOINT:
            missing_vars.append("AZURE_ENDPOINT")
        if not AZURE_API_VERSION:
            missing_vars.append("AZURE_API_VERSION")
        if not AZURE_DEPLOYMENT:
            missing_vars.append("AZURE_DEPLOYMENT")

        if missing_vars:
            logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
            logger.warning("OCR functionality may not work correctly. Please check your .env file.")

        # Initialize the Azure OpenAI client
        try:
            self.client = AzureOpenAI(
                api_version=AZURE_API_VERSION,
                azure_endpoint=AZURE_ENDPOINT,
                api_key=AZURE_API_KEY,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self.client = None

    def _prepare_image(self, image_data: bytes) -> str:
        """
        Prepare the image for OCR processing.
        Resize and convert to base64 if needed.
        """
        try:
            # Open image and resize if necessary
            img = Image.open(BytesIO(image_data))

            # Resize if the image is too large
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024))

            # Convert to RGB if it's not already
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convert back to bytes
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)

            # Convert to base64
            encoded_image = base64.b64encode(buffer.read()).decode('utf-8')
            return encoded_image

        except Exception as e:
            logger.error(f"Error preparing image: {e}")
            raise

    def extract_readings(self, image_data: bytes) -> Tuple[int, int, int]:
        """
        Process image data and extract blood pressure readings using Azure OpenAI API.
        Returns a tuple of (systolic, diastolic, pulse) values.
        """
        # Check if client is initialized
        if self.client is None:
            logger.error("Azure OpenAI client is not initialized. Cannot process image.")
            return (0, 0, 0)

        try:
            # Prepare the image
            base64_image = self._prepare_image(image_data)

            # Create the messages for the API call
            messages = [
                {
                    "role": "system",
                    "content": "You are a highly accurate blood pressure reading OCR system. Your task is to analyze images from blood pressure monitors and extract ONLY the following values: systolic (top number), diastolic (bottom number), and pulse rate. Return ONLY these three numbers in a JSON format. If any of these values are missing, do not guess - use 0 instead. Do not include any explanations, just return the JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the systolic pressure, diastolic pressure, and pulse readings from this blood pressure monitor image. Only return the numbers in the exact JSON format: {\"systolic\": X, \"diastolic\": Y, \"pulse\": Z}. If any reading is unclear or missing, use 0 for that value."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]

            # Check if the API version supports structured output
            if self._supports_structured_output():
                logger.info("Using structured output for OCR processing")
                try:
                    # Use the beta.chat.completions.parse method for structured output
                    completion = self.client.beta.chat.completions.parse(
                        messages=messages,
                        temperature=0.1,
                        model=AZURE_DEPLOYMENT,
                        response_format=BloodPressureReading
                    )

                    # Extract the structured data
                    reading = completion.choices[0].message.parsed
                    systolic = reading.systolic
                    diastolic = reading.diastolic
                    pulse = reading.pulse

                except (AttributeError, ImportError) as e:
                    logger.warning(f"Structured output failed, falling back to standard method: {e}")
                    return self._extract_readings_legacy(base64_image, messages)
            else:
                # Fall back to legacy method if structured output is not supported
                return self._extract_readings_legacy(base64_image, messages)

            # Basic validation
            if systolic < 70 or systolic > 250:
                logger.warning(f"Unusual systolic value detected: {systolic}")
            if diastolic < 40 or diastolic > 150:
                logger.warning(f"Unusual diastolic value detected: {diastolic}")
            if pulse < 30 or pulse > 220:
                logger.warning(f"Unusual pulse value detected: {pulse}")

            return (systolic, diastolic, pulse)

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return (0, 0, 0)

    def _supports_structured_output(self) -> bool:
        """
        Check if the current API version and client support structured output.
        """
        # Temporarily disable structured output until we confirm it works
        return False

        # Original implementation:
        # try:
        #     # Check if the beta attribute exists
        #     return hasattr(self.client, 'beta') and hasattr(self.client.beta, 'chat')
        # except Exception:
        #     return False

    def _extract_readings_legacy(self, _: str, messages: list) -> Tuple[int, int, int]:
        """
        Legacy method to extract readings without structured output.
        """
        try:
            # Make API request using the Azure OpenAI client
            logger.info("Using legacy method for OCR processing")
            completion = self.client.chat.completions.create(
                messages=messages,
                temperature=0.1,
                max_tokens=100,
                model=AZURE_DEPLOYMENT,
                response_format={"type": "json_object"}
            )

            # Extract the content from the response
            content = completion.choices[0].message.content

            # Extract JSON
            try:
                # Try to parse directly
                readings = json.loads(content)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from the text
                import re
                json_match = re.search(r'\{.*\}', content)
                if json_match:
                    readings = json.loads(json_match.group(0))
                else:
                    logger.error(f"Could not extract JSON from response: {content}")
                    return (0, 0, 0)

            # Extract the readings
            systolic = int(readings.get("systolic", 0))
            diastolic = int(readings.get("diastolic", 0))
            pulse = int(readings.get("pulse", 0))

            return (systolic, diastolic, pulse)

        except Exception as e:
            logger.error(f"Error in legacy OCR processing: {e}")
            return (0, 0, 0)