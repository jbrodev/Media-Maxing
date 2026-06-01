# Web App

Static first-pass web app shell.

No frontend framework has been installed yet. Open `index.html` directly in a browser to view the mock dashboard shell.

Available routes:

- `index.html#home`: mock dashboard shell.
- `index.html#brand`: first Brand Brain screen.
- `index.html#settings`: first Settings screen.

The Settings screen currently uses a temporary browser `localStorage` adapter. It mirrors the local SQLite settings shape, but it is not wired to the SQLite data layer until a web/API bridge exists.

The Brand Brain screen also uses a temporary browser `localStorage` adapter. It mirrors the seeded demo Brand Profile shape and should be replaced by the SQLite-backed Brand Brain service once a web/API bridge exists.
