# Truth Social Collector Chrome Extension

This is a Manifest V3 Chrome extension scaffold that collects Truth Social posts from an authenticated browser session.

## What it does
- runs on `truthsocial.com`
- looks up the configured account handle
- fetches recent statuses from the browser session
- deduplicates by last seen post ID
- periodically runs via `chrome.alarms`
- optionally uploads new posts to a webhook

## Important constraint
This is a browser-resident collector. It depends on an open, logged-in Truth Social tab.

## Install for development
1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `chrome-extension/` directory

## Configure
Open the popup or options page and set:
- handle: default is `realDonaldTrump`
- interval: default is `15` minutes
- webhook URL: optional
- enabled: on/off

## Notes
- Chrome alarms only run while the browser is open.
- If Truth Social changes its API paths, update `src/content.js`.
- If you want to send data to a local collector, point the webhook URL at your server or n8n endpoint.
