# Static assets

| Path | What it is |
|---|---|
| `icon.svg` | App icon, referenced by the web manifest |
| `manifest.webmanifest` | PWA manifest — makes WANAS installable to a home screen |
| `vendor/` | A-Frame, AR.js and the Hiro marker, vendored for offline AR. See `vendor/NOTICE.md` |

## The AR marker

The augmented-reality screen uses AR.js's built-in **Hiro** preset, and the
marker image is served locally from `vendor/hiro.png`. Nothing in the AR path
touches the network.

To use it: open the AR screen, tap **view the marker**, and either print that
image or show it full-screen on a second device. Point the phone at it from
about 30–50 cm.

## Why the camera needs HTTPS

Browsers only grant camera access on a secure origin. `http://localhost` counts
as secure, so the AR demo works in local development. On any other host it must
be served over HTTPS, or the camera request is refused before the app sees it —
which is what the recovery screen in `ArScreen.tsx` explains to the visitor.
