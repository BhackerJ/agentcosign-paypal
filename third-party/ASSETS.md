# Bundled report asset provenance

The report renderer is reused from the author's existing `deciq-report-app` 0.4.0.
Original author code remains subject to the project owner's release authority.
The app's installed package metadata supplies the version/license inventory in
packages.json. Exact original compiled-build dependency provenance is not fully
attested by that metadata; external notices for the conservative runtime dependency closure are supplied. No private report source or node_modules is shipped.

Inter and Roboto Mono are from @fontsource/inter 5.3.0 and
@fontsource/roboto-mono 5.3.0, both OFL-1.1. All 54 bundled font files were compared
byte-for-byte with their installed package originals; complete original licenses
are included under licenses. Fonts have not been modified or renamed internally.

Merchant screenshots and Channel3 product evidence are not covered by these
software/font licenses. See PUBLIC-RESOURCES.md for the remaining display and
redistribution review. This notice is not permission to relicense merchant content.

decimal.js-light LICENCE.md and victory-vendor embedded d3/internmap notices are included. victory-vendor declares MIT AND ISC; its root MIT notice was retrieved from the upstream v37.3.6 tag and is included alongside embedded vendor notices. Exact compiled-build provenance remains an explicit release-review item.
