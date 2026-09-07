# Vendored third-party assets

These files are **not** part of WANAS. They are redistributed here so the
augmented-reality demo runs with no network connection — a competition jury room
cannot be assumed to have connectivity, and a CDN request is a single point of
failure in a live demo.

Each file is pinned to an exact version. To update one, replace the file, bump
the version below, and re-run `npm run build`.

| File | Project | Version | Licence | Source |
|---|---|---|---|---|
| `aframe.min.js` | A-Frame | 1.4.0 | MIT | https://aframe.io/releases/1.4.0/aframe.min.js |
| `aframe-ar.js` | AR.js (AR-js-org) | 3.4.5 | MIT | https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.5/aframe/build/aframe-ar.js |
| `hiro.png` | AR.js — Hiro fiducial marker | from AR.js `data/images` | MIT | https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/images/hiro.png |

A-Frame is copyright Mozilla and A-Frame contributors, released under the MIT
licence. AR.js is copyright Jerome Etienne and the AR-js-org contributors, also
MIT. Both licences permit redistribution provided the copyright notice and
permission notice are retained — which is the purpose of this file. Full licence
text: <https://github.com/aframevr/aframe/blob/master/LICENSE> and
<https://github.com/AR-js-org/AR.js/blob/master/LICENSE>.

AR.js bundles ARToolKit5 (LGPL-3.0) compiled to WebAssembly. It is redistributed
here unmodified as part of the AR.js build.

## Re-downloading

If these files are ever lost, `curl` them back:

```bash
cd web/public/vendor
curl -L -o aframe.min.js https://aframe.io/releases/1.4.0/aframe.min.js
curl -L -o aframe-ar.js  https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.5/aframe/build/aframe-ar.js
curl -L -o hiro.png      https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/images/hiro.png
```

The AR screen falls back to the CDN URLs above if a vendored file is missing, so
a deployment that omits this directory still works — it just needs the network.
