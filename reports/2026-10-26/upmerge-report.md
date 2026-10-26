# Upmerge report 2026-10-26

Chain: v4.0 → v4.5 → v4.6 → v4.7 → v4.8 → v5.0

## Summary

| repo | merge | status | tier (model/effort) | complexity | verdict | sonar baseline (source / target) |
|---|---|---|---|---|---|---|
| unifly-services | v4.8→v5.0 | PR #10269, CI green, Sonar OK | moderate (opus/high) | 3 | CONFIRM | v4.8 OK, 0 issues / v5.0 ERROR, 369 issues |
| unifly-portal | v4.8→v5.0 | SKIPPED by the developer (not pushed) | moderate (opus/high) | 3 | NEEDS-REVIEW | v4.8 OK, 1 issue / v5.0 ERROR, 12 issues |
| unifly-services | v4.6→v4.7 | nothing to merge (done upstream in #10267 during the run) | clean | 0 | - | v4.6 OK, 0 / v4.7 OK, 0 |
| unifly-portal | v4.7→v4.8 | nothing to merge (done upstream in #11884 during the run) | clean | 0 | - | v4.7 OK, 0 / v4.8 OK, 1 |
| unifly-automation | v4.8→v5.0 | nothing to merge (done upstream in #1657 during the run) | clean | 0 | - | no Sonar project |

Nothing pending in unifly-tiles, unifly-geoserver, proj-demo, unifly-keycloak, unifly-socketcluster, unifly.data.
Missing branches: unifly-services has no v4.0; app-automation has no v4.6, v4.7, v4.8, v5.0.

## Run notes

The first scan showed three clean merges (services v4.6→v4.7, portal v4.7→v4.8, automation v4.8→v5.0)
and deferred the two conflicting v4.8→v5.0 pairs behind them. Between the scan and the merge agents,
those three upmerges were merged upstream (PRs #10267, #10268, #11884, #1657, 07:00-07:02 UTC), so each
merge returned "Already up to date". A rescan then unblocked both v4.8→v5.0 pairs, which the developer
selected.

## Overview

### Conflicting

**unifly-services v4.8→v5.0**, branch `merge26102026_48to50`, CI: Jenkins `unifly-services` / Sonar `unifly-all-services`
- conflicts: `unifly-alerting/src/testIntegration/java/aero/unifly/alerting/integration/collision/CollisionFlowTest.java`,
  `unifly-geofence/src/testIntegration/java/aero/unifly/ed318/file/Ed318FileConfigurationIntegrationTest.java`
- bb852d890b Merge pull request #10268 from unifly-aero/v4.7
- 4e888deda7 Merge pull request #10267 from unifly-aero/v4.6
- b584c60a96 Merge pull request #10265 from unifly-aero/tracking-lock-fixes-to-v4.6
- 579dd6e908 fix: make geometryFactory final in MovementInternalCachingServiceImpl
- 3d703f91ae test: cover movement lookup and sync lock release in tracking
- 7679bba496 fix sonar issues in MovementInternalCachingServiceImpl
- 83b60a8aa7 🐛 fix deadlock in tracking / syncMovementsToDatabase
- 90ffd6e59b Use a lock per UAS for UasGeoZoneOperationalConditionsCachingServiceImpl (#10141)
- 71bcce46be ❄️🗑️ Flaky test fix (#10259)
- c3d2d759fd Merge pull request #10257 from `<fork>`/CAN-7323_show-attachment-in-instructions
- 91adfcb3a5 Merge pull request #10254 from `<fork>`/company-event
- c931e08509 Added new field documentUuid in ConfirmationMessage => deleted CONFIRMATION_DOCUMENT_UUID workflow variable
- 6bf92920bd rename param to companyUniqueIdentifier
- 4870e3bc62 ❄️⛔ Fixed the flaky test by changing how it puts files into the inbound directory. (#10246)
- 6ab18e4424 Added confirmationDocumentUuid in UserTaskInfo RequiresAcknowledgementStatusDelegate now saves that id in the permission request flow CAN-7323
- 1e4e25d159 Handle null company creation when retrieving client id
- ab9d49682c provide company create method with uniqueIdentifier

**unifly-portal v4.8→v5.0**, branch `merge26102026_48to50`, CI: Jenkins `unifly-portal` / Sonar `unifly-portal`
- conflicts: `packages/web-sentry/src/flightview/flightview.ts`
- fd1dfa0219 Merge pull request #11884 from unifly-aero/v4.7
- 5e3c62691b Merge pull request #11878 from `<fork>`/CAN-7323_show-attachment-in-instructions
- e68cd75b8b Add document download to ProcessAcknowledgeModal CAN-7323
- d80dd7c377 Merge pull request #11871 from `<fork>`/CAN-7322
- 030a8e9e4f CAN-7322. Operation creation: Save button no longer ignores the first click after editing a field
- 047ab88d4e Update Operator access rights not required for API key mgmt (#11860)
- 08bae0d474 fix error thrown because subscription is undefined (#11857)
- b2143b31ea Merge pull request #11849 from `<fork>`/CAN-7360
- 792c886dcb Take into account clock skew of the client OS to time the token refresh CAN-7360

### Clean

None left after the rescan.

## unifly-services v4.8→v5.0

Merge commit `54d4fafb48`, head `c1b7ddf99f`.

Conflict resolutions:
- `CollisionFlowTest.java` (confident): kept v5.0's removal of `redis.expire.collision=50000` (de692327fb,
  DigitalElevationService removal) and added v4.8's `nearby.warning.locationValidity=3600` from flaky-test fix 71bcce46be.
- `Ed318FileConfigurationIntegrationTest.java` (confident): imports only, union of `StandardCopyOption` (v4.8)
  and `Collection`, `Optional` (v5.0); all three are used.

Validation gates: markers pass, carried pass, spotless pass, compile pass, unit tests pass (after fix commit),
integrationTest skipped locally (Jenkins runs it).

Extra commit `c1b7ddf99f Fixed tests after upmerge` (semantic conflicts, no textual conflict):
- ab9d49682c calls `Company.setUniqueIdentifier(String)`; v5.0's `Company` uses the typed `CompanyUuid` and had
  no setter. Added `@Setter` on `uniqueIdentifier` in `unifly-lib-auth-model` and call
  `setUniqueIdentifier(CompanyUuid.of(...))`.
- `CompanyInternalServiceImplTest`: assert on `getUniqueIdentifier().getValue()`.
- `MovementInternalCachingServiceImplTest`: hamcrest → assertj, and `LockRegistry` → `StaticKeyLockRegistry`
  with `StaticLockKey.SYNC_MOVEMENTS_TO_DATABASE`, the lock the v5.0 service really uses.

Verifier (opus/high): **CONFIRM**. No dropped changes, no unsound resolutions, no added comments.
- The `@Setter` is the minimal port: v5.0 has no other way to give a new `Company` a chosen unique identifier.
  `updatable=false` does not affect the create path (the id is set before the INSERT). Note for reviewers:
  v5.0 made this field builder-only on purpose; a public setter on a shared entity does nothing on already
  persisted companies.
- The v4.6 tracking-lock fixes were already on v5.0 as cherry-picks; only 579dd6e908 (geometryFactory final) is new.
- CAN-7323 changes carried exactly.

PR: https://github.com/unifly-aero/unifly-services/pull/10269

CI: Jenkins PR-10269 build #1 **SUCCESS** on the first run (13.4 min): 11565 tests passed, 0 failed,
49 skipped, integration tests included. The two conflicted integration tests passed:
CollisionFlowTest (4/4), Ed318FileConfigurationIntegrationTest (6/6). Sonar PR gate **OK**, 0 new issues,
0 hotspots. No fix commits needed.

## unifly-portal v4.8→v5.0 (skipped)

Merge commit `71dc2208db`, head `81bf758271`. Not pushed; the branch stays local.

Conflict resolution:
- `flightview.ts` (confident): kept v5.0. 08bae0d474 only made `subscription` null-safe in code that v5.0
  removed (UP-12136 rewrote the view into a React wrapper; the subscription now lives in
  `layers/createOperationLayer.ts` and is removed via `map.onRemoved`).

Validation gates: markers, carried, install, lint, typecheck, unit tests pass (typecheck after fix commit).

Extra commit `81bf758271 Fixed tests after upmerge`: `Actions.tsx` auto-merged CAN-7322, which imports
`./providers/GeometryPropertiesProvider`; on v5.0 that provider moved to web-common (UP-12241 #11759,
UP-11540 #11808). The fix imports `useGeometryProperties` from web-common and calls it with
`OPERATION_DRAWING_LAYER_ID`.

Verifier (opus/high): **NEEDS-REVIEW**. Nothing dropped, but a behaviour clash:
- CAN-7322 (#11871, Bug "Save button requires two clicks to redirect to Operation Details page", v4.8.x)
  replaces `useIsAnyRequestLoading()` in the Save guard with geometry-properties loading only.
- On v5.0, `useIsAnyRequestLoading()` also covered `store.isLoading()`, which includes supporting-volumes
  loading (UP-10948 #10824, refactored in #10944). v4.8 has no supporting volumes.
- So on v5.0, Save can be clicked while supporting volumes reload after a startTime or shape edit, and
  `getSupportingVolumes()` is sent as it is at click time (stale or null).
- Adding `getIsSupportingVolumesLoading()` back to the guard would bring back the first-click problem for
  those edits. This needs a decision from the CAN-7322 / UP-10948 owners.

The developer chose to skip this merge for today.

## Deferred

None.
