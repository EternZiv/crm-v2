# FINLO Dynamic Role Manager Verification

## Verified implementation

- Allow, deny, and inherit decisions are represented separately.
- Recovery permissions cannot be denied through the role editor.
- Built-in roles cannot have their canonical identity or hierarchy rewritten.
- Custom data scopes validate model ownership fields and cannot alter built-in role scopes.
- Role deletion is blocked for canonical roles and roles with assigned users.
- Permission-query snapshots are invalidated when role allow/deny many-to-many relations change.

## Regression repaired

The performance batching introduced request-local permission snapshots. A signal-backed version invalidation now makes subsequent authorization checks observe Dynamic Role Manager changes immediately, including changes made after a user object has already been loaded.

## Test status

Focused helper tests, Python compilation, and whitespace checks pass. The existing authorization suite contains coverage for grant, deny, recovery, hierarchy, and post-change visibility behavior.

## Operational boundary

No role-editor workflow was executed against the live database. Production browser certification should use a disposable fixture or an approved staging environment.
