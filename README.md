
# Thai Nutrition Assistant

A LINE bot prototype that uses Gemini to identify food from a photo or description, estimate nutrition, and suggest changes based on a nutrition goal.

## Use the bot

1. Send `Goal= fat loss` to set your goal.
2. Send a food photo or description.
3. Or send both as text, for example: `oatmeal | fat loss`.

The bot gives estimated nutrition information. Your goal is kept in memory and is cleared when the server restarts.

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Set these environment variables in a local `.env` file:

```text
GEMINI_API_KEY=your-gemini-key
CHANNEL_SECRET=your-line-channel-secret
CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
```

Start the web server:

```bash
gunicorn app:app
```

## Deploy

Deploy the repository as a Render web service with:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **LINE webhook URL:** `https://your-render-service.onrender.com/callback`

Add the three environment variables above in Render’s Environment settings. Keep `.env` out of Git.