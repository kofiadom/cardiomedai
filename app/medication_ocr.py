import os
import base64
import json
from typing import Dict, List
from PIL import Image
from io import BytesIO
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure OpenAI Configuration
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_2")

# Define the Pydantic models for structured output
class MedicationScheduleItem(BaseModel):
    """Individual medication dose schedule item."""
    datetime: str = Field(description="Exact date and time for the dose in ISO 8601 format")
    dosage: str = Field(description="Amount to be taken at that time")

class MedicationPrescription(BaseModel):
    """
    Structured model for medication prescription details extracted from images.
    """
    name: str = Field(description="The name of the medication")
    dosage: str = Field(description="The composition or strength of the medication")
    schedule: List[MedicationScheduleItem] = Field(description="List of scheduled doses with datetime and dosage")
    interpretation: str = Field(description="Explanation of what was observed in the image and how the prescription information was interpreted")

class MedicationOCRProcessor:
    def __init__(self):
        """Initialize the OCR processor for medication prescriptions."""
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

    def extract_prescription(self, image_data: bytes) -> Dict:
        """
        Process image data and extract medication prescription details using Azure OpenAI API.
        Returns a dictionary with medication name, dosage, and schedule.
        """
        # Check if client is initialized
        if self.client is None:
            logger.error("Azure OpenAI client is not initialized. Cannot process image.")
            return {"name": "", "dosage": "", "schedule": [], "interpretation": ""}

        try:
            # Prepare the image
            base64_image = self._prepare_image(image_data)

            # Get current datetime for the prompt
            current_datetime = datetime.now(timezone.utc).isoformat()

            # Create the system prompt
            system_prompt = f"""You are a medical assistant AI. Your task is to extract structured prescription details from the given medication instruction text or transcription (e.g., from a photo of a box or doctor's note).

IMPORTANT: Look carefully for ALL prescription details including:
- Medication name and strength
- Total quantity/number of tablets or doses in the package
- Frequency (how often to take)
- Duration (how many days)
- SPECIFIC TIMING PATTERNS: Look for exact times, irregular intervals, or phrases like "take at 8 PM first day, then 4 AM next day, then 8 PM" - these are NOT evenly spaced
- Timing instructions (with food, morning/evening, etc.)
- Any special instructions or dosing patterns

The output must be in JSON format with the following fields:

name: The name of the medication (e.g., "Lonart DS")

dosage: The composition or strength of the medication (e.g., "80mg artemether + 480mg lumefantrine", or "1 tablet")

schedule: A list of ALL doses based on the complete treatment, each with:

datetime: Exact date and time for the dose, in ISO 8601 format (e.g., "2025-07-01T08:00:00")

dosage: Amount to be taken at that time (e.g., "1 tablet")

interpretation: Explain what you observed in the image and how you interpreted the prescription information. Specifically mention: what text/numbers you could see, the total quantity if visible, the frequency instructions, duration, and explain your reasoning for the complete schedule. This helps users understand how you processed the image and verify if your understanding matches what's actually shown.

🔹 Assume the current date and time is: {current_datetime}. When calculating schedules:
   - For relative timing (e.g., "take immediately, then after 8 hours"), use this datetime to calculate
   - For specific times, understand day progression: early morning times (like 4 AM) typically indicate the next day
   - Calculate proper date transitions when times cross midnight

🔹 CRITICAL: Generate the COMPLETE schedule for the entire treatment duration. If you see "5 tablets" and "twice daily for 3 days", create exactly 6 scheduled doses over 3 days.

🔹 TIMING INSTRUCTIONS: Pay close attention to specific timing patterns:
   - Look for exact times mentioned and understand the day progression
   - When you see a sequence like "8 PM, 4 AM, 8 PM, 8 AM, 8 PM" - this typically means:
     * Day 1: 8 PM
     * Day 2: 4 AM, then 8 PM (same day)
     * Day 3: 8 AM, then 8 PM (same day)
   - Some medications have irregular intervals (not evenly spaced)
   - If specific times are given, use those EXACTLY and calculate proper day transitions
   - Only use even spacing (e.g., every 12 hours) if no specific times are mentioned
   - Pay attention to natural day boundaries - times like 4 AM usually start a new day

🔹 For the interpretation, describe what you saw in the image including total quantity, frequency, duration, specific timing instructions if any, and how you calculated the complete schedule.

Return only the JSON structure."""

            # Create the messages for the API call
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the complete medication prescription details from this image. Look carefully for the medication name, total quantity/number of tablets, dosage instructions, frequency (how often), and duration (how many days). Generate the FULL schedule for the entire treatment period. Return the information in the exact JSON format specified in the system prompt."
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
                logger.info("Using structured output for medication OCR processing")
                try:
                    # Use the beta.chat.completions.parse method for structured output
                    completion = self.client.beta.chat.completions.parse(
                        messages=messages,
                        temperature=0.1,
                        model=AZURE_DEPLOYMENT,
                        response_format=MedicationPrescription
                    )

                    # Extract the structured data
                    prescription = completion.choices[0].message.parsed
                    return {
                        "name": prescription.name,
                        "dosage": prescription.dosage,
                        "schedule": [{"datetime": item.datetime, "dosage": item.dosage} for item in prescription.schedule],
                        "interpretation": prescription.interpretation
                    }

                except (AttributeError, ImportError) as e:
                    logger.warning(f"Structured output failed, falling back to standard method: {e}")
                    return self._extract_prescription_legacy(messages)
            else:
                # Fall back to legacy method if structured output is not supported
                return self._extract_prescription_legacy(messages)

        except Exception as e:
            logger.error(f"Error processing medication image: {e}")
            return {"name": "", "dosage": "", "schedule": [], "interpretation": ""}

    def _supports_structured_output(self) -> bool:
        """
        Check if the current API version and client support structured output.
        """
        # Temporarily disable structured output until we confirm it works
        return False

    def _extract_prescription_legacy(self, messages: list) -> Dict:
        """
        Legacy method to extract prescription without structured output.
        """
        try:
            # Make API request using the Azure OpenAI client
            logger.info("Using legacy method for medication OCR processing")
            completion = self.client.chat.completions.create(
                messages=messages,
                temperature=0.1,
                max_tokens=700,
                model=AZURE_DEPLOYMENT,
                response_format={"type": "json_object"}
            )

            # Extract the content from the response
            content = completion.choices[0].message.content

            # Extract JSON
            try:
                # Try to parse directly
                prescription_data = json.loads(content)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from the text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    prescription_data = json.loads(json_match.group(0))
                else:
                    logger.error(f"Could not extract JSON from response: {content}")
                    return {"name": "", "dosage": "", "schedule": []}

            # Validate and return the prescription data
            name = prescription_data.get("name", "")
            dosage = prescription_data.get("dosage", "")
            schedule = prescription_data.get("schedule", [])
            interpretation = prescription_data.get("interpretation", "")

            return {
                "name": name,
                "dosage": dosage,
                "schedule": schedule,
                "interpretation": interpretation
            }

        except Exception as e:
            logger.error(f"Error in legacy medication OCR processing: {e}")
            return {"name": "", "dosage": "", "schedule": [], "interpretation": ""}
