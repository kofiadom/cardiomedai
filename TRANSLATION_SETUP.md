# Health Advisor Translation Feature

This document explains how to set up and use the GhanaNLP API for translating health advisor responses into African languages like Twi, Ga, Ewe, Fante, and Dagbani.

## Overview

The translation feature allows users to receive health advisor responses in their preferred African language. The integration uses the **Ghana NLP Python Library** which provides easy access to local African language technologies.

## Setup Instructions

### 1. Install the ghana-nlp Package

```bash
pip install ghana-nlp
```

To upgrade to the latest version:

```bash
python -m pip install --upgrade ghana-nlp
```

### 2. Configure Your API Key

Get your GhanaNLP API key by visiting the [Ghana NLP website](https://ghananlp.org).

Set the API key as an environment variable in your `.env` file:

```bash
GHANA_NLP_API_KEY=your_api_key_here
```

The application will automatically load this when the translation service is initialized.

## Supported Languages

The GhanaNLP library supports the following African languages:

| Language Code | Language Name |
|---------------|---------------|
| `en`          | English       |
| `tw`          | Twi           |
| `gaa`         | Ga            |
| `ee`          | Ewe           |
| `fat`         | Fante         |
| `dag`         | Dagbani       |

## API Usage

### Get List of Supported Languages

```bash
GET /health-advisor/languages
```

**Response:**
```json
{
  "languages": {
    "en": "English",
    "tw": "Twi",
    "gaa": "Ga",
    "ee": "Ewe",
    "fat": "Fante",
    "dag": "Dagbani"
  },
  "description": "Supported languages for translating health advisor responses"
}
```

### Get Health Advice with Translation (POST)

```bash
POST /health-advisor/advice
Content-Type: application/json

{
  "user_id": 1,
  "message": "Good morning! How am I doing with my health today?",
  "language": "tw"
}
```

**Response:**
```json
{
  "user_id": 1,
  "request_message": "Good morning! How am I doing with my health today?",
  "advisor_response": "Hi Sarah! Your BP reading this morning is 118/75, which is excellent!...",
  "translated_response": "Maakye Sarah! Wo abɔ a woyoo ɔkyena no....",
  "language": "tw",
  "agent_id": "asst_xxx",
  "thread_id": "thread_xxx",
  "status": "completed"
}
```

### Get Health Advice with Translation (GET)

Quick daily check-in with optional translation:

```bash
GET /health-advisor/advice/1?language=tw
```

With a custom message and language:

```bash
GET /health-advisor/advice/1?message=How%20did%20I%20do%20yesterday?&language=tw
```

**Parameters:**
- `user_id` (path): The ID of the user requesting check-in
- `message` (query, optional): Custom message (defaults to morning check-in prompt)
- `language` (query, optional): Language code for translation (default: "en")

## Frontend Integration Example

### React Component Example

```javascript
// Get supported languages
async function getSupportedLanguages() {
  const response = await fetch('/health-advisor/languages');
  return response.json();
}

// Get health advice with translation
async function getHealthAdviceInLanguage(userId, language = 'en') {
  const endpoint = `/health-advisor/advice/${userId}?language=${language}`;
  const response = await fetch(endpoint);
  const data = await response.json();

  return {
    original: data.advisor_response,
    translated: data.translated_response || data.advisor_response,
    language: data.language
  };
}

// Example usage in a component
function HealthAdvisorWidget({ userId }) {
  const [advice, setAdvice] = useState(null);
  const [language, setLanguage] = useState('en');
  const [languages, setLanguages] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load available languages
    getSupportedLanguages().then(data => {
      setLanguages(data.languages);
    });
  }, []);

  const fetchAdvice = async (lang) => {
    setLoading(true);
    try {
      const result = await getHealthAdviceInLanguage(userId, lang);
      setAdvice(result);
      setLanguage(lang);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="health-advisor-widget">
      <div className="language-selector">
        {Object.entries(languages).map(([code, name]) => (
          <button
            key={code}
            onClick={() => fetchAdvice(code)}
            className={language === code ? 'active' : ''}
          >
            {name}
          </button>
        ))}
      </div>

      {loading && <p>Loading...</p>}

      {advice && (
        <div className="advice-content">
          <h3>Health Advisor</h3>
          <p>{advice.translated || advice.original}</p>
          {advice.translated && advice.translated !== advice.original && (
            <details>
              <summary>View in English</summary>
              <p>{advice.original}</p>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

export default HealthAdvisorWidget;
```

## How It Works

### Architecture

1. **Frontend**: User selects a language from the dropdown (or toggles to Twi)
2. **Backend Request**: Frontend sends request with `language` parameter
3. **Health Advisor Agent**: Generates English health advice
4. **Translation Service**: GhanaNLP API translates the response to target language
5. **Response**: Returns both original English and translated text

### Translation Flow

```
User Request (language: "tw")
        ↓
Health Advisor Service
        ↓
Generate English Response
        ↓
Translation Service
        ↓
GhanaNLP API (en → tw)
        ↓
Return Translated + Original Response
```

## Error Handling

If translation fails for any reason:

- The original English response is still returned
- A warning is logged to the console
- `translated_response` will be `null` in the response
- The `status` remains "completed"

**Example failure response:**
```json
{
  "user_id": 1,
  "advisor_response": "Hi Sarah!...",
  "translated_response": null,
  "language": "tw",
  "status": "completed"
}
```

## Troubleshooting

### API Key Not Found

**Error:** `ValueError: GhanaNLP API key not provided`

**Solution:**
1. Ensure `GHANA_NLP_API_KEY` is set in your `.env` file
2. Restart the application after setting the environment variable
3. Check that the key is valid and has not expired

### Translation Service Not Initializing

**Error:** `⚠️ Translation service initialization failed`

**Solution:**
1. Verify the GhanaNLP package is installed: `pip list | grep ghana`
2. Check your API key is correct
3. Verify internet connectivity (GhanaNLP is a cloud-based service)

### Poor Translation Quality

**Note:** Translation quality varies by language pair and text complexity. Consider:

- Breaking up long responses into shorter sentences
- Using simple, clear language in the health advisor prompts
- Testing with different language pairs

## Backend Files Modified

### New Files
- `app/translation_service.py` - Main translation service using GhanaNLP API

### Modified Files
- `app/schemas.py` - Added `language` parameter to `HealthAdvisorRequest` and `translated_response` to `HealthAdvisorResponse`
- `app/routers/health_advisor.py` - Added translation logic and new `/languages` endpoint

## Performance Considerations

- Translation adds ~1-3 seconds latency per request (depends on API response time)
- Responses are NOT cached - each request triggers a new translation
- Consider implementing caching for frequently requested translations
- The translation happens asynchronously, so it doesn't block the response

## Future Enhancements

1. **Response Caching**: Cache translations for duplicate advice texts
2. **Bulk Translation**: Support multiple language translations in a single request
3. **Language Detection**: Auto-detect user's preferred language from frontend settings
4. **Audio Generation**: Combine with TTS (Text-to-Speech) for spoken responses
5. **Custom Terminology**: Train GhanaNLP models with health-specific vocabulary

## Testing

### Using cURL

```bash
# Get languages
curl http://localhost:8000/health-advisor/languages

# Get advice in Twi
curl -X POST http://localhost:8000/health-advisor/advice \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "Good morning!",
    "language": "tw"
  }'

# Get advice in Ga
curl http://localhost:8000/health-advisor/advice/1?language=gaa
```

### Using Python Requests

```python
import requests

# Get advice with translation
response = requests.post(
    'http://localhost:8000/health-advisor/advice',
    json={
        'user_id': 1,
        'message': 'Good morning!',
        'language': 'tw'
    }
)

data = response.json()
print(f"Original: {data['advisor_response']}")
print(f"Twi: {data['translated_response']}")
```

## References

- [GhanaNLP Documentation](https://ghananlp.org/docs)
- [Ghana NLP GitHub Repository](https://github.com/ghananlp/ghana-nlp)
- [Supported Language Codes](https://ghananlp.org/languages)
