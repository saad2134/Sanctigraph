Web icon bundle

- apple-touch-icon.png: iOS home screen icon (180x180).
- icon-192.png / icon-512.png: standard PWA icons.
- icon-192-maskable.png / icon-512-maskable.png: maskable PWA icons.
- favicon.ico: multi-size favicon (16, 32).

Add to your HTML:
<link rel="icon" href="/web/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/web/apple-touch-icon.png">

Add to your web manifest:
{
  "icons": [
    { "src": "/web/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/web/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/web/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/web/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}