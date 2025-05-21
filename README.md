# CardioMed AI

CardioMed AI is a comprehensive blood pressure management system designed to help users track, analyze, and interpret their blood pressure readings. The application provides a RESTful API for managing blood pressure data, user profiles, and includes OCR functionality to extract readings from blood pressure monitor images.

![CardioMed AI Logo](https://via.placeholder.com/150x150.png?text=CardioMed+AI)

## Features

- **User Management**: Create and manage user profiles with medical information
- **Blood Pressure Tracking**: Log and monitor blood pressure readings over time
- **OCR Processing**: Extract blood pressure readings from images using AI
- **Standardized Interpretation**: Automatic categorization of readings based on medical guidelines
- **Statistical Analysis**: View trends and patterns in blood pressure data

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager
- Azure OpenAI API access (for OCR functionality)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kofiadom/cardiomedai.git
   cd cardiomedai
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
   Using uv:
   ```bash
   uv venv # to set up the environment
   uv sync # to install dependencies
   uv run app/main.py # to run the application
   ```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. Install dependencies:

   Using pip:
   ```bash
   pip install -e .
   ```


5. Set up environment variables by creating a `.env` file based on `.env.example`:
   ```
   AZURE_API_KEY="your_azure_api_key_here"
   AZURE_ENDPOINT="your_azure_endpoint_here"
   AZURE_API_VERSION="your_azure_api_version_here"
   AZURE_DEPLOYMENT="your_azure_deployed_model_name_here eg gpt-4o-mini"
   ```

6. Run database migrations:
   ```bash
   python migrate_db.py
   ```

7. Start the application:

   Using python:
   ```bash
   python -m app.main
   ```

   Using uv:
   ```bash
   uv run app/main.py
   ```

The API will be available at `http://localhost:8000`.

## API Endpoints

### User Management

- `POST /users/`: Create a new user
- `GET /users/`: List all users

### Blood Pressure Management

- `POST /bp/readings/`: Create a new blood pressure reading
- `GET /bp/readings/{user_id}`: Get all readings for a user
- `POST /bp/upload/`: Upload a blood pressure monitor image for OCR processing
- `GET /bp/readings/stats/{user_id}`: Get statistics about a user's blood pressure readings

## Blood Pressure Interpretation

CardioMed AI automatically interprets blood pressure readings according to the American Heart Association and National Heart, Lung, and Blood Institute guidelines:

| Category | Systolic | Diastolic |
|----------|----------|-----------|
| Normal | < 120 | < 80 |
| Elevated | 120-129 | < 80 |
| Hypertension Stage 1 | 130-139 | OR 80-89 |
| Hypertension Stage 2 | ≥ 140 | OR ≥ 90 |
| Hypertensive Crisis | > 180 | OR > 120 |

## OCR Functionality

The OCR functionality uses Azure OpenAI's vision capabilities to extract blood pressure readings from images of blood pressure monitors. Users can upload images and the system will automatically extract:

- Systolic pressure (top number)
- Diastolic pressure (bottom number)
- Pulse rate

Users can optionally add their own notes to the readings.

## Project Structure

- `app/`: Main application package
  - `main.py`: Application entry point
  - `models.py`: SQLAlchemy models
  - `schemas.py`: Pydantic schemas
  - `database.py`: Database configuration
  - `ocr.py`: OCR processing logic
  - `routers/`: API route handlers
    - `users.py`: User management endpoints
    - `blood_pressure.py`: Blood pressure endpoints

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

When changing the database schema:
1. Update the model in `models.py`
2. Create a migration script similar to `migrate_db.py`
3. Run the migration script to update the database

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- American Heart Association for blood pressure guidelines
- Azure OpenAI for OCR capabilities

---

*CardioMed AI - Empowering better cardiovascular health through technology*