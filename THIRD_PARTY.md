# Dependencies and provenance

This repository contains original application/adaptation code and minimized extracts of the author’s existing synthetic shopping tasks/profiles. Neither the private harness implementation nor a real customer dataset is vendored. Compiled report assets and fonts include third-party dependencies as listed below. Anthropic SDK, Playwright and their transitive packages are installed from their public distributions and retain their own licenses. PayPal names identify the sandbox API integration; no affiliation or endorsement is claimed.

The canonical review video uses the owner’s original English voice and camera recording; no synthetic voice or background music was added. Source hashes refer to historical full files, while fixtures/manifest.json hashes the minimized extracts shipped here.

The candidate replay bundle includes third-party captured merchant pages and renderer assets. These are not relicensed under MIT; see [PUBLIC-RESOURCES.md](PUBLIC-RESOURCES.md) for the inventory and pending public-display review.

## Bundled renderer notices

See [asset provenance](third-party/ASSETS.md), [package inventory](third-party/packages.json) and the original license/notice texts in `third-party/licenses/`. The inventory conservatively covers the renderer runtime dependency closure plus Tailwind CSS; it is not a claim every package is present in the compiled output. Source package versions are provenance evidence, not a reproducible-build attestation.
