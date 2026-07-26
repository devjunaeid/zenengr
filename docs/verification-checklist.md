# Verification Checklist

Run after code review and before considering a task done.

## Manual verification

- [ ] Start the app with the dev command.
- [ ] Exercise the feature through the UI or API.
- [ ] Verify happy path and known edge cases.
- [ ] Verify error paths show helpful feedback.

## Automated verification

- [ ] All lint checks pass.
- [ ] All type checks pass.
- [ ] All tests pass.
- [ ] Test coverage is acceptable for the change.

## Environment / integration

- [ ] Works with the configured database/services.
- [ ] Works in the target browser or client.
- [ ] Environment variables / config documented if changed.

## Sign-off

- [ ] Verification checklist walked end-to-end.
- [ ] `docs/progress.md` updated.
