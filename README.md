# GinDee LINE meal logging

In a private LINE chat, send a meal photo or description. GinDee returns estimated nutrition. Tap **Log meal** to save it to the shared diary. Send **Today's summary** to see meals logged on either platform and their calorie and macro totals.

Send **Connect GinDee**, open the one-time link and select **Continue with LINE**. The link expires after five minutes. The signed-in browser and LINE bot use the same diary. Your existing browser guest history stays with the guest account and is available again after signing out.

## Deploy GinDee sync

1. From the GinDee source repository, run `git apply --check /path/to/gindee-line-sync.patch`, then `git apply /path/to/gindee-line-sync.patch`. The patch targets the GinDee snapshot with the `v12_photo_credit` database migration.
2. Generate a shared secret with `openssl rand -hex 32`. Set it as `GINDEE_SYNC_SECRET` on both the GinDee backend and this Flask bot. Keep it on the servers.
3. Deploy GinDee with its usual AI configuration and set `DB_PATH` to a SQLite database on persistent storage. GinDee applies its new migrations on startup.
4. Set the following variables on the Flask bot and deploy it.

   | Variable | Value |
   | --- | --- |
   | `GINDEE_BASE_URL` | GinDee's HTTPS origin, e.g. `https://gindee.example.com` |
   | `GINDEE_SYNC_SECRET` | The same shared secret configured on GinDee |
   | `CHANNEL_SECRET` | The official account's LINE Messaging API channel secret |
   | `CHANNEL_ACCESS_TOKEN` | The official account's LINE Messaging API access token |

   Render build command is `pip install -r requirements.txt`. Start with `gunicorn --timeout 90 app:app` to allow time for photo download and analysis.
5. Point the official account webhook at `https://your-bot.example.com/callback`. Use the same official account if you want to see any LINE history GinDee already stored under that account's user IDs.

The sign-in flow uses a link from the private bot chat and an HTTPS browser session. To check both directions after deploying, log a meal in LINE and open the diary, then log a different meal on the website and request **Today's summary** in LINE.

## Standalone mode

Leave both GinDee variables unset and set `GEMINI_API_KEY` to use the original Gemini bot. Send `Goal= fat loss` followed by a photo or description, or send `oatmeal | fat loss`. Goals reset when the bot restarts.

For local use, install with `pip install -r requirements.txt`, set variables in an untracked `.env` file and start Gunicorn.
