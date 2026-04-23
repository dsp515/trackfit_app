# Testing Practices

## Frameworks
- **Frontend**: Vitest configured for Node environments to test non-visual logic.
- **Backend**: None explicitly found. Manual testing assumed.

## Frontend Structure
- `vitest.config.ts` roots execution.
- Tests stored directly under `/__tests__/` (e.g., `rep-counter.test.ts`).
- `setup-rn-mocks.ts` provides shims for React Native globals.

## Mocking & Coverage
- Tests focus heavily on computational logic (e.g., angle math porting from python, MET calorie conversions).
- `npm run test:coverage` exists in `package.json` for tracking.

## Gaps
- Heavy Context providers (`AppContext.tsx`) rely on manual device testing.
- Integration tests representing API latency failovers are currently missing.
