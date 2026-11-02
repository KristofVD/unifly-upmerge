# Upmerge report 2026-11-02

Merge Monday ticket: [UP-12768](https://unifly.atlassian.net/browse/UP-12768) (Merge Monday 02/11/2026: 4.0 up until 5.0)

## Summary

| repo | merge | status | tier (model/effort) | complexity | verdict | sonar baseline (source / target) | Jira sub-ticket |
|---|---|---|---|---|---|---|---|
| unifly-automation | v4.8→v5.0 | PR [#1666](https://github.com/unifly-aero/unifly-automation/pull/1666), no CI | clean (–; verifier sonnet/medium) | 0 | CONFIRM | – | – |
| unifly-services | v4.6→v4.7 | PR [#10298](https://github.com/unifly-aero/unifly-services/pull/10298), Jenkins green, Sonar OK | moderate (opus/high) | 3 | CONFIRM | v4.6 ERROR (2 minor) / v4.7 OK (0) | – |
| unifly-portal | v4.8→v5.0 | PR [#11951](https://github.com/unifly-aero/unifly-portal/pull/11951), Jenkins green, Sonar OK | hard (opus/max) | 6 | CONFIRM | v4.8 OK (1) / v5.0 ERROR (8) | – |
| unifly-services | v4.7→v4.8 | PR [#10301](https://github.com/unifly-aero/unifly-services/pull/10301), Jenkins green, Sonar OK | clean (–; verifier sonnet/medium) | 0 | CONFIRM | v4.7 OK (0) / – | – |
| unifly-portal | v4.6→v4.7 | merged by the developer (#11949) | clean | – | – | – | – |
| unifly-portal | v4.7→v4.8 | merged by the developer (#11950) | clean | – | – | – | – |
| unifly-services | v4.8→v5.0 | PR [#10303](https://github.com/unifly-aero/unifly-services/pull/10303), Jenkins green, Sonar OK | moderate (opus/high) | 4 | CONFIRM | – | – |
| unifly-services | v4.7→v4.8 (Sonar backport) | PR [#10302](https://github.com/unifly-aero/unifly-services/pull/10302), Jenkins green, Sonar OK | clean, tree identical to v4.8 | 0 | – | – | – |

Up to date: unifly-tiles, unifly-geoserver, proj-demo, unifly-keycloak, unifly-socketcluster, unifly.data.
Missing chain branches: unifly-services (v4.0), app-automation (v4.6, v4.7, v4.8, v5.0).

## Overview at scan time

### Clean

- **unifly-portal v4.6→v4.7**: PR #11918 already open at scan time; merged by the developer as #11949. CI: Jenkins `unifly-portal`, Sonar `unifly-portal`.
  - 624cb71435 Reduce billable HERE basemap tile requests in droneweb (#11912)
- **unifly-portal v4.7→v4.8**: deferred behind v4.6→v4.7 at scan time; merged by the developer as #11950. CI: Jenkins `unifly-portal`, Sonar `unifly-portal`.
  - 6665e51f03 New translations portal.json (French) (#11895)
- **unifly-automation v4.8→v5.0**: branch `merge02112026_48to50`. CI: none.
  - 514d4254 Merge pull request #1663 from unifly-aero/fixWalLevel
  - 61ff6f2c ⚙️Set `wal_level=logical` if any *_analytics group is present in the inventory

### Conflicting

- **unifly-services v4.6→v4.7**: branch `merge02112026_46to47`. CI: Jenkins `unifly-services`, Sonar `unifly-all-services`.
  - Conflict files: `unifly-geofence/.../ed269/outbound/converter/UasZoneDefaultPropertyResolver.java`, `UasZonePropertyResolver.java`
  - 7d5cf712db Merge pull request #10279 from `<fork>`/BEDG-1160
  - 735df32366 Merge pull request #10274 from `<fork>`/BEDG-1174
  - 372a56060e Droneguide - CIS invalid geometry according to GeoJSON specification BEDG-1160
  - ba4877dce7 Droneguide - EBAW VLLs showing wrong start active date BEDG-1174
- **unifly-portal v4.8→v5.0**: branch `merge02112026_48to50`. Deferred at scan time, started after the developer merged #11949 and #11950 (31 commits after the rescan). CI: Jenkins `unifly-portal`, Sonar `unifly-portal`.
  - Conflict files: `web-common/locales/ach/common.json`, `MapSearchbar.tsx`, `details-view/components/Description.tsx`, `UasOperationFeatureLoader.ts` (modify/delete), `web-components/src/styles/_ckEditor.component.scss`, `web-droneweb/src/droneweb/ol/OlLayerFactory.ts` (modify/delete), `web-droneweb/src/droneweb/ol/ol-map.ts` (modify/delete)
  - f4c43bb7e1 Merge pull request #11950 from unifly-aero/v4.7
  - 59d55eae06 Merge pull request #11949 from unifly-aero/v4.6
  - fd72c0c249 Remove some unused image assets (#11942)
  - c8889e3ff4 Reduce splash screen image sizes (#11935)
  - b564750f27 Merge pull request #11928 from `<fork>`/UP-12695
  - 3c74ba2e22 change key
  - 3720e7dcea Merge pull request #11930 from `<fork>`/UP-12705_add-copy-button
  - 89db86592c fix
  - f6e93ee497 Show copy button only on InternalNoteDialog => it overlaps with other buttons on other components UP-12705
  - 3a8f2a562a Format the description value in geozone details panel
  - 624cb71435 Reduce billable HERE basemap tile requests in droneweb (#11912)
  - e574702dc2 New Crowdin updates (#11908)
  - 6665e51f03 New translations portal.json (French) (#11895)
  - ff5ed4d7e1 Merge pull request #11897 from `<fork>`/UP-12705_add-copy-button
  - 6fc759342a log clipboard error in console
  - 3dbadab0ac Merge pull request #11903 from `<fork>`/UP-12743-3
  - e4fe3c759f Merge v4.7 -> v4.8
  - fa17b5d786 Merge pull request #11902 from `<fork>`/UP-12743-2
  - a39a97b066 Merge branch 'v4.6' into v4.7
  - e7d2ceafab Merge pull request #11899 from `<fork>`/UP-12743
  - da3e1a9585 timeout clear + try/catch
  - 7a100ce54b Reduce the debounce time
  - ab30d7c811 Use only 1 button instead of 2
  - c1e1bfb2c2 Optimize api calls for searchbar
  - 4420b0a251 disable 'copied' button
  - 4f1b06b3f9 Added copy all button for response templates UP-12705
  - 41708a0c2e New Crowdin updates (#11890)
  - 1cbe5aef3f Merge pull request #11888 from `<fork>`/UP-12697_prevent-drone-changes-while-in-active-operation
  - 6d33951822 New translation for UasInActiveOperationException UP-12697
  - d22aac4f3f Merge pull request #11883 from `<fork>`/CAN-7370
  - a9a10a2ac4 CAN-7370: Fix Copy operation opening the original operation instead of a copy
- **unifly-services v4.8→v5.0**: branch `merge02112026_48to50`, deferred behind v4.6→v4.7 (#10298) and the v4.7→v4.8 step after it. CI: Jenkins `unifly-services`, Sonar `unifly-all-services`.
  - Conflict files: `fleet/internal/UasEntityServiceImpl.java`, `UasEntityServiceImplTest.java`, `integration/api/converter/UasOperationPermissionProcessToUasOperationPermissionDetailInfoConverter.java` + test, `SoonActiveGeoZoneOverlapFinderIntegrationTest.java`
  - d47c668ad2 Align PermissionProcess and Permission to PermissionDetailInfo converters (#10287)
  - a11b099b9a 🕛❄️ Fix time dependent flaky test
  - a60a680d3f Align PermissionProcess and Permission to PermissionDetailInfo converters
  - 4dd247c58d Add assignee and conversation message to the converter (#10286)
  - bae705511a Merge pull request #10276 from `<fork>`/UP-12697_prevent-drone-changes-while-in-active-operation
  - 48e9f24d15 New query that doesnt return the whole operation, only a boolean UP-12697
  - 379869d621 Merge pull request #10270 from `<fork>`/UP-12697_prevent-drone-changes-while-in-active-operation
  - f4a492e47a fix sonarqube issues
  - 30ae3f098e Prevent uat parameter changes while uat is linked to active operation UP-12697
  - 22e244ba22 Merge pull request #10264 from `<fork>`/UP-12687_instructions-visible-for-sentry-in-PR-acknowledgement-pending-step
  - 4c91fb497a Both requires acknowledgement and acknowledged PR steps now show the instructions and the attached file in their history UP-12687

## unifly-automation v4.8→v5.0

Clean merge, one line in `playbooks/roles/postgresql/templates/postgresql.conf.j2`.

- Gates: merge-state pass, markers pass, carried pass. No build in this repo.
- Extra commits: none.
- Verifier: **CONFIRM**. Parents correct, source carried, no new or dropped lines.
- CI: no Jenkins job; the PR reports no checks.

## unifly-services v4.6→v4.7

Tier moderate (score 4), resolver opus/high, verifier opus/high.

| file | resolution | confident |
|---|---|---|
| `UasZoneDefaultPropertyResolver.java` | Union of imports (v4.7's `GeoZoneDetailsInternalInfo`, `CollectionUtils`; v4.6's `GeometryHelper`, `Polygon`). v4.6's new `buildPolygons` kept, parameter switched to `GeoZoneDetailsInternalInfo` | yes |
| `UasZonePropertyResolver.java` | v4.7's `buildIdentifier(GeoZoneDetailsInternalInfo)` plus v4.6's new `List<Polygon> buildPolygons(GeoZoneDetailsInternalInfo)` | yes |

Cause: on v4.7 the ED-269 outbound converters moved from `GeoZoneInternalInfo` to `GeoZoneDetailsInternalInfo` (9f742de60c); v4.6 (BEDG-1160) added `buildPolygons` on the old type.
Inside the merge commit, the three v4.6-added tests in the auto-merged `ED269UasZoneBuilderTest.java` were moved to `GeoZoneDetailsInternalInfo` as well (compile fix).
Note for the proj-* upmerges: any project implementation of `UasZonePropertyResolver` must implement `buildPolygons(GeoZoneDetailsInternalInfo)` once it is on v4.7.

- Gates: markers pass, carried pass, spotless pass, compile pass, unit tests pass, integration tests skipped locally.
- Extra commits: none.
- Verifier: **CONFIRM**. Diff stat against v4.7 equals the source's diff stat from the merge base (9 files, +291/-44); BEDG-1160 and BEDG-1174 carried in full.
- CI: Jenkins PR-10298 build #1 **SUCCESS** (compile, Spotless, full test incl. integration tests, Sonar PR). Sonar gate on the PR **OK**, 0 new issues, 0 hotspots. No fix commits.

## unifly-portal v4.8→v5.0

Tier hard (score 7), resolver opus/max with Jira, verifier opus/max.

| file | resolution | confident |
|---|---|---|
| `web-common/locales/ach/common.json` | v5.0's file plus v4.8's two new keys (`button.copied`, `errorMessages.uas_in_active_operation`) | yes |
| `MapSearchbar.tsx` | v4.8's `loadOptions` (trim, history on empty query, minimum length 3) on v5.0's callback props; the auto-merged `map.isCoordinateWithinBounds` call now uses the v5.0 `isCoordinateWithinBounds` prop | yes |
| `details-view/components/Description.tsx` | v4.8's formatted description and ` /` bullet split, plus v5.0's `showBorderBelow` prop | yes |
| `UasOperationFeatureLoader.ts` (modify/delete) | v5.0 delete kept. Replaced on v5.0 by `web-portal/.../loadOperationFeature.ts` (UP-12227), which already returns the copied feature, so the CAN-7370 fix is moot | yes |
| `_ckEditor.component.scss` | Union of v5.0's balloon-panel input style and v4.8's copy-button styles | yes |
| `web-droneweb/.../ol/OlLayerFactory.ts` (modify/delete) | v5.0 delete kept (UP-10919). #11912's `preload: 0` ported to `web-common/src/map/store/helpers/olLayerFactoryHelper.ts` | yes |
| `web-droneweb/.../ol/ol-map.ts` (modify/delete) | v5.0 delete kept (UP-11540). #11912's single 250ms location animation ported to `web-common/src/map/store/helpers/helpers.ts`; the stored-last-view part is already on v5.0 (#11160) | yes |

Jira tickets the resolver used:
- UP-12743: the searchbar change is about fewer location API calls, so v4.8's minimum-length logic goes on top of v5.0's callback-props refactor.
- UP-12695: the ` /` bullet split is meant for v4.8 and v5.0, so it is combined with v5.0's `showBorderBelow`.
- UP-12705: the CKEditor copy button and "Copied" feedback are intended; styles and the `button.copied` key kept.
- UP-12697: the new `uas_in_active_operation` error message is intended; key added to ach.
- CAN-7370: moved to UP-12706; v5.0's rewritten loader already returns the copy, no port needed.
- UP-12227: moved operation loading to `loadOperationFeature.ts`, confirming the delete of `UasOperationFeatureLoader.ts`.
- UP-11540: moved the React OL map into web-common and deleted droneweb `ol-map.ts`; that is where #11912 is ported.
- UP-10919: removed the old droneweb code including `OlLayerFactory.ts`; its replacement is `olLayerFactoryHelper.ts`.
- UP-12761: v5.0 HEAD (Luciad removal); it did not delete any of the three files.

Scope note for review: on v4.x #11912 only affected droneweb. On v5.0 all apps share the web-common OpenLayers map, so `preload: 0` and the single 250ms animation now apply to droneweb, portal, sentry and admin. The verifier judged this acceptable: `preload: Infinity` and the chained animation only reached the shared map by copying droneweb code, the billable-HERE reason applies to every app, `preload: 0` is the OpenLayers default, and the animation only runs from the centre-on-location button.

- Gates: markers pass, carried pass, install pass, lint pass, typecheck pass, unit tests pass. `yarn build` not run locally.
- Extra commits: none.
- Verifier: **CONFIRM**. For 31 of the 36 files v4.8 touched, the merge's change equals v4.8's own change; the other 5 and every flagged line are explained. No references to the deleted image assets remain.
- CI: Jenkins PR-11951 build #1 **SUCCESS** (Test, Sonar PR; the PR pipeline skips the full product build). Sonar gate on the PR **OK**, 0 new issues, 0 hotspots. No fix commits.

## unifly-services v4.7→v4.8

Started after #10298 was merged upstream. The developer first opened #10299 with the `v4.7` branch itself as head; Jenkins then took the Jenkinsfile from the head commit (v4.7, JDK 21) while building the merged v4.8 code, and dependency resolution failed:
`Dependency resolution is looking for a library compatible with JVM runtime version 21, but 'aero.unifly:unifly-translations:4.8-SNAPSHOT' is only compatible with JVM runtime version 25 or newer.`
Replaced by merge branch `merge02112026_47to48` (from v4.8, v4.7 merged in, so v4.8's JDK 25 Jenkinsfile), and #10299 was closed with a pointer to #10301.

Clean merge.
- Gates: markers pass, carried pass, spotless pass, compile pass (the ED-269 `buildPolygons` changes compile against v4.8), unit tests pass, integration tests skipped locally.
- Extra commits: none.
- Verifier: **CONFIRM**. No new or dropped lines.
- CI: Jenkins PR-10301 build #1 **SUCCESS**. Sonar gate on the PR **OK**, 0 new issues, 0 hotspots. No fix commits.

## Side fix: v4.7 branch Sonar stage

The v4.7 branch builds #49 and #50 failed after all tests passed, in the Sonar stage, which also aborted the parallel Publish stage:
`Invalid value of sonar.tests for :unifly-auth-mosquitto` (in #49: `:unifly-tracking-uspace`), the generated `build/generated/sources/proto/test/java` folder does not exist.
v4.8 fixed this in #10052 "Stabilize sonar build" (765cc9241b) by pinning `sonar.tests` to `src/test/java` in both modules; v4.6 and v4.7 never got it.
Backported to v4.7 as PR [#10300](https://github.com/unifly-aero/unifly-services/pull/10300) (cherry-pick; one conflict because v4.7 lacked the earlier uspace commit cbab095fe5, resolved to v4.8's block so both files match v4.8). Jenkins PR-10300 build #1 **SUCCESS**, Sonar PR analysis successful, gate OK. The branch Sonar stage is only proven fixed by the next v4.7 build after the merge.

## unifly-services v4.8→v5.0

Started after #10301 was merged upstream (19 commits). The developer stopped the first validation run by mistake; it was restarted from the committed merge.
Tier moderate (score 4), resolver opus/high, verifier opus/high.

| file | resolution | confident |
|---|---|---|
| `GeoZoneValidityServiceImpl.java` | v5.0 `GeoZoneValidityStatus` imports plus v4.8's `ZONE_UTC` import from v5.0's `aero.unifly.common.util.DateUtil` | yes |
| `UasEntityServiceImpl.java` | v4.8 method (in-air and in-active-operation checks) with v5.0's `getUniqueIdentifier().getValue()` | yes |
| `UasOperationPermissionProcessToUasOperationPermissionDetailInfoConverter.java` | v4.8 builder form with v5.0's `getUniqueIdentifier().getValue()` | yes |
| `UasEntityServiceImplTest.java` | v4.8 tests with v5.0 typed-id stubs | yes |
| `UasOperationPermissionProcessToUasOperationPermissionDetailInfoConverterTest.java` | Import union; v5.0 `UasOperationUuid.of` plus v4.8 assignee and conversation mocks | yes |
| `SoonActiveGeoZoneOverlapFinderIntegrationTest.java` | v4.8 `java.time` imports, v5.0 Spring `Transactional` | yes |

Compile adaptations of auto-merged v4.8 code inside the merge commit:
- BEDG-1174: `GeoZoneValidityRepository.findCurrentValiditiesByGeoZone` takes a `GeoZoneUuid`, like the neighbouring queries.
- UP-12697: `UasOperationRepository.isUasInActiveOperation` takes a `UasUuid`; `UasFlightInternalServiceImpl` wraps it like `isUasInAir`.
- BEDG-1160: `ED269UasZoneBuilderTest` uses the renamed `AipMappingConfigurationProperties`.

- Gates: markers pass, carried pass, spotless pass, compile pass, unit tests pass, integration tests skipped locally.
- Extra commits: `Fixed tests after upmerge` (the new `UasInActiveOperationException` imported a `CodeException` package that does not exist on v5.0).
- Verifier: **CONFIRM**. The diff against v5.0 covers exactly v4.8's 28 files (+492/-70); every differing line is an adaptation to v5.0 types or packages, nothing of v5.0 is reverted.
- CI: Jenkins PR-10303 build #1 **SUCCESS** (11896 tests passed, including `UasOperationRepositoryTest.isUasInActiveOperation*` and `SoonActiveGeoZoneOverlapFinderIntegrationTest`). Sonar gate on the PR **OK**, 0 new issues. No CI fix commits.

## unifly-services v4.7→v4.8 (Sonar backport)

Merging #10300 into v4.7 left a v4.7→v4.8 pair whose merged tree is identical to v4.8 (v4.8 already had #10052). PR #10302 only records the merge. Jenkins PR-10302 build #1 **SUCCESS**, Sonar gate OK.

## Jira sub-tickets

None.

## Deferred

None.
