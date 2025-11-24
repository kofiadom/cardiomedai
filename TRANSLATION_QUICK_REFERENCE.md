# Translation Feature - Quick Reference

## Installation
```bash
pip install ghana-nlp
```

## Setup
```bash
# Add to .env
GHANA_NLP_API_KEY=your_api_key_here
```

## API Endpoints

### List Supported Languages
```bash
GET /health-advisor/languages
```

### Get Advice in Twi (Quick)
```bash
GET /health-advisor/advice/1?language=tw
```

### Get Advice with Custom Message
```bash
GET /health-advisor/advice/1?message=How%20am%20I%20doing?&language=tw
```

### Get Advice via POST (Full Control)
```bash
POST /health-advisor/advice
{
  "user_id": 1,
  "message": "Good morning!",
  "language": "tw"
}
```

## Supported Languages
- **en** - English (default)
- **tw** - Twi
- **gaa** - Ga
- **ee** - Ewe
- **fat** - Fante
- **dag** - Dagbani

## Response Example
```json
{
  "user_id": 1,
  "advisor_response": "Hi Sarah! Your BP reading...",
  "translated_response": "Maakye Sarah! Wo BP reading...",
  "language": "tw",
  "status": "completed"
}
```

## Frontend - Simple Toggle
```javascript
const lang = isTwi ? 'tw' : 'en';
fetch(`/health-advisor/advice/1?language=${lang}`)
  .then(r => r.json())
  .then(data => {
    // Show translated or original
    const text = data.translated_response || data.advisor_response;
  });
```

## Files Created
- `app/translation_service.py` - Translation service
- `pyproject.toml` - Updated with ghana-nlp dependency

## Files Modified
- `app/schemas.py` - Added language fields
- `app/routers/health_advisor.py` - Added translation logic

## Documentation Files
- `TRANSLATION_SETUP.md` - Full setup guide
- `TRANSLATION_IMPLEMENTATION_SUMMARY.md` - Technical details
- `FRONTEND_TRANSLATION_QUICKSTART.md` - Frontend guide
- `CHANGES_SUMMARY.md` - Complete changes list

## Testing
```bash
# Test languages endpoint
curl http://localhost:8000/health-advisor/languages

# Test with Twi
curl "http://localhost:8000/health-advisor/advice/1?language=tw"

# Test POST
curl -X POST http://localhost:8000/health-advisor/advice \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "message": "Hi", "language": "tw"}'
```

## Environment Variables
```bash
GHANA_NLP_API_KEY=your_api_key_here
```

## Key Points
- ✅ Backward compatible (English is default)
- ✅ Async/non-blocking
- ✅ Graceful error handling
- ✅ Both original and translated text returned
- ✅ Translation only happens if language ≠ "en"
- ✅ Supports Twi, Ga, Ewe, Fante, Dagbani

## Troubleshooting

**Translation not appearing?**
- Check `GHANA_NLP_API_KEY` is set
- Verify `translated_response` is not null in response
- Check browser console for errors

**Service not initializing?**
- Ensure `ghana-nlp` is installed
- Verify API key is valid
- Restart application after setting env vars

**Poor translations?**
- This is expected for some languages
- GhanaNLP improves over time
- Consider shorter, simpler health messages
