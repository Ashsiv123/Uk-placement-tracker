# UK Placement Tracker

## Publish with GitHub Pages
1. Upload all files/folders into `Ashsiv123/Uk-placement-tracker`.
2. Go to **Settings → Pages**.
3. Choose **Deploy from a branch**.
4. Select `main` and `/ (root)`.
5. Save.

Expected URL:
https://ashsiv123.github.io/Uk-placement-tracker/

## Automatic updater
The GitHub Actions workflow runs daily at 07:15 UTC and can also be run manually.

Important: the included updater checks/fingerprints configured public employer pages. It does not yet extract every new job automatically, because employer sites use different systems and many block scraping. The dashboard/data structure is ready for employer-specific parsers or public job feeds.
