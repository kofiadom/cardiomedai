# Frontend Translation Quick Start Guide

This guide helps frontend developers implement the language toggle feature for health advisor responses.

## Quick Summary

Users can now receive health advisor responses in Twi (and other African languages) by toggling a language selector on the frontend.

## What's New on the Backend

The backend now supports a `language` parameter in health advisor requests:

### Endpoints

#### GET - Simple Language Toggle
```
GET /health-advisor/advice/{user_id}?language=tw
```

**Response:**
```json
{
  "user_id": 1,
  "advisor_response": "Hi Sarah! Your reading is great...",
  "translated_response": "Maakye Sarah! Wo reading...",
  "language": "tw",
  "status": "completed"
}
```

#### POST - Full Request with Language
```
POST /health-advisor/advice
Content-Type: application/json

{
  "user_id": 1,
  "message": "Good morning!",
  "language": "tw"
}
```

#### List Supported Languages
```
GET /health-advisor/languages

Response:
{
  "languages": {
    "en": "English",
    "tw": "Twi",
    "gaa": "Ga",
    "ee": "Ewe",
    "fat": "Fante",
    "dag": "Dagbani"
  },
  "description": "..."
}
```

## Frontend Implementation

### 1. Create a Language Selector Component

```javascript
import React, { useState, useEffect } from 'react';

function LanguageSelector({ onLanguageChange, currentLanguage }) {
  const [languages, setLanguages] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch available languages on component mount
    fetchSupportedLanguages();
  }, []);

  const fetchSupportedLanguages = async () => {
    try {
      const response = await fetch('/health-advisor/languages');
      const data = await response.json();
      setLanguages(data.languages);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load languages:', error);
      // Fallback languages
      setLanguages({
        en: 'English',
        tw: 'Twi',
        gaa: 'Ga',
        ee: 'Ewe',
        fat: 'Fante',
        dag: 'Dagbani'
      });
      setLoading(false);
    }
  };

  return (
    <div className="language-selector">
      <label htmlFor="language">Language:</label>
      <select
        id="language"
        value={currentLanguage}
        onChange={(e) => onLanguageChange(e.target.value)}
        disabled={loading}
      >
        {Object.entries(languages).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}

export default LanguageSelector;
```

### 2. Update Health Advisor Widget

```javascript
import React, { useState } from 'react';
import LanguageSelector from './LanguageSelector';

function HealthAdvisorWidget({ userId }) {
  const [advice, setAdvice] = useState(null);
  const [language, setLanguage] = useState('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAdvice = async (lang = language) => {
    setLoading(true);
    setError(null);

    try {
      // Use GET endpoint with language parameter
      const response = await fetch(
        `/health-advisor/advice/${userId}?language=${lang}`
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setAdvice(data);
      setLanguage(lang);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch health advice:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = (newLanguage) => {
    fetchAdvice(newLanguage);
  };

  // Initial load
  React.useEffect(() => {
    fetchAdvice();
  }, [userId]);

  return (
    <div className="health-advisor-widget">
      <LanguageSelector
        currentLanguage={language}
        onLanguageChange={handleLanguageChange}
      />

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">Error: {error}</div>}

      {advice && (
        <div className="advice-container">
          <h3>Health Advisor</h3>

          {/* Display translated response if available, otherwise original */}
          <p className="advice-text">
            {advice.translated_response || advice.advisor_response}
          </p>

          {/* Show original English if showing translation */}
          {advice.translated_response && advice.language !== 'en' && (
            <details className="original-text">
              <summary>View in English</summary>
              <p>{advice.advisor_response}</p>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

export default HealthAdvisorWidget;
```

### 3. Simple Toggle Example (Button Style)

If you want a simple toggle button (e.g., English ↔ Twi):

```javascript
function HealthAdvisorWithToggle({ userId }) {
  const [isTwi, setIsTwi] = useState(false);
  const [advice, setAdvice] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchAdvice = async (useTwi) => {
    setLoading(true);
    const lang = useTwi ? 'tw' : 'en';

    try {
      const response = await fetch(
        `/health-advisor/advice/${userId}?language=${lang}`
      );
      const data = await response.json();
      setAdvice(data);
      setIsTwi(useTwi);
    } catch (error) {
      console.error('Failed to fetch advice:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="health-advisor">
      <button
        onClick={() => fetchAdvice(!isTwi)}
        className={`language-toggle ${isTwi ? 'twi' : 'english'}`}
        disabled={loading}
      >
        {loading ? 'Loading...' : (isTwi ? '🇬🇭 Twi' : '🇬🇧 English')}
      </button>

      {advice && (
        <div className="advice-content">
          <p>{advice.translated_response || advice.advisor_response}</p>
        </div>
      )}
    </div>
  );
}

export default HealthAdvisorWithToggle;
```

## Styling Examples

### CSS for Language Toggle Button

```css
.language-toggle {
  padding: 8px 16px;
  border: 2px solid #007bff;
  border-radius: 4px;
  background-color: white;
  color: #007bff;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.language-toggle:hover:not(:disabled) {
  background-color: #007bff;
  color: white;
}

.language-toggle.twi {
  border-color: #ff6b6b;
  color: #ff6b6b;
}

.language-toggle.twi:hover:not(:disabled) {
  background-color: #ff6b6b;
  color: white;
}

.language-toggle:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.original-text {
  margin-top: 12px;
  padding: 8px;
  background-color: #f8f9fa;
  border-left: 3px solid #6c757d;
}

.original-text summary {
  cursor: pointer;
  color: #6c757d;
  font-size: 0.9em;
  padding: 4px;
}

.original-text p {
  margin-top: 8px;
  color: #495057;
  font-size: 0.95em;
}
```

## Testing the Feature

### Using the API Directly

```bash
# Test with Twi
curl "http://localhost:8000/health-advisor/advice/1?language=tw"

# Test with different language
curl "http://localhost:8000/health-advisor/advice/1?language=gaa"

# Get available languages
curl "http://localhost:8000/health-advisor/languages"
```

### Using JavaScript in Browser Console

```javascript
// Fetch advice in Twi
fetch('/health-advisor/advice/1?language=tw')
  .then(r => r.json())
  .then(data => {
    console.log('English:', data.advisor_response);
    console.log('Twi:', data.translated_response);
  });
```

## Response Structure

The backend returns:

```json
{
  "user_id": 1,
  "request_message": "Good morning!",
  "advisor_response": "Hi Sarah! Your BP reading of 118/75 is excellent...",
  "translated_response": "Maakye Sarah! Wo BP reading...",
  "language": "tw",
  "agent_id": "asst_xxx",
  "thread_id": "thread_xxx",
  "status": "completed"
}
```

**Key fields:**
- `advisor_response`: Original English text (always present)
- `translated_response`: Translated text (null if language is "en" or translation failed)
- `language`: The language code that was requested

## Error Handling

Always gracefully handle cases where:
1. Translation service is unavailable (translated_response is null)
2. Network errors occur
3. User doesn't exist

```javascript
const handleResponse = (data) => {
  // If translation failed, use original
  const displayText = data.translated_response || data.advisor_response;

  // Check status
  if (data.status !== 'completed') {
    console.warn('Request not completed:', data.status);
  }

  return displayText;
};
```

## Available Languages for Users

Show users these options:

| Flag | Code | Language |
|------|------|----------|
| 🇬🇧 | en | English |
| 🇬🇭 | tw | Twi |
| 🇬🇭 | gaa | Ga |
| 🇬🇭 | ee | Ewe |
| 🇬🇭 | fat | Fante |
| 🇬🇭 | dag | Dagbani |

## Local Development

1. Ensure backend is running with `GHANA_NLP_API_KEY` set
2. Test the `/health-advisor/languages` endpoint first
3. Then test `/health-advisor/advice/{userId}?language=tw`
4. Implement frontend based on the examples above

## Troubleshooting

### Translation not appearing?
- Check browser console for errors
- Verify `GHANA_NLP_API_KEY` is set on backend
- Check `translated_response` field in response (should not be null)

### API endpoint not responding?
- Verify backend is running
- Check that health advisor service is initialized
- Look at backend logs for errors

### Language selector not loading?
- Verify `/health-advisor/languages` endpoint works
- Check network tab in browser dev tools
- Ensure CORS is properly configured if frontend is on different domain

## Performance Tips

1. Cache language choice in localStorage
2. Only refetch when language actually changes
3. Show loading state while translating
4. Consider debouncing language selection if needed

```javascript
// Save language preference
localStorage.setItem('healthAdvisorLanguage', language);

// Load on next visit
const savedLanguage = localStorage.getItem('healthAdvisorLanguage') || 'en';
```

## Next Steps

1. Choose component style (toggle button vs dropdown selector)
2. Implement one of the examples above
3. Test with real user data
4. Gather feedback from Twi-speaking users
5. Consider adding other language variants if needed
