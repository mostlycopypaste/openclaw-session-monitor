# Add Status Column Feature Test Plan

**Date:** 2026-04-07  
**Feature:** Status column and smart sorting for dashboard  
**Implementation Plan:** [2026-04-07-add-status-column.md](./2026-04-07-add-status-column.md)

---

## Strategy Reconciliation

The implementation plan defines a TDD approach with 14 automated tests across model, parser, and dashboard components. This test plan verifies the strategy is complete and adds necessary detail for each test.

### Implementation Architecture Review

**Planned approach:**
- Add optional status field to Session model (dataclass extension)
- Extract status from sessions.json in parser (using .get() for safety)
- Pass status through monitor to Session objects (integration)
- Add Status column to dashboard Rich table (between Label and Age)
- Implement tuple-based sort key: (is_done, -window_percent)

**Testing strategy alignment:**
- ✅ Model tests verify field storage and defaults (3 tests)
- ✅ Parser tests verify extraction logic for all scenarios (4 tests)
- ✅ Dashboard tests verify rendering and sorting (7 tests)
- ✅ No monitor tests needed (covered by integration)
- ✅ Manual verification for visual appearance

**Coverage assessment:**
- All code paths covered (null, running, done, missing)
- Edge cases included (empty, all active, all done)
- Primary and secondary sorting both tested
- No performance concerns (tuple sort is O(n log n))
- Visual appearance requires manual verification only

**Conclusion:** Testing strategy is complete. No adjustments required.

---

## Test Plan

Tests are ordered by implementation sequence (TDD red-green-refactor) as specified in the implementation plan. All tests use pytest with no external mocking required.

### Phase 1: Model Tests (3 tests)

#### Test 1: Status field defaults to None

**Name:** Session status field defaults to None when not provided  
**Type:** Unit (model field validation)  
**Disposition:** New  
**Harness:** pytest  

**Preconditions:**
- `src/models.py` Session dataclass exists
- Test file `tests/test_models.py` exists

**Actions:**
1. Create Session with only required fields (no status)
2. Assert session.status is None

**Expected outcome:**
- Source of truth: Feature requirement "status: Optional[str] = None"
- status field defaults to None
- No exception raised
- Field is accessible after creation

**Interactions:**
- Session dataclass constructor

**Implementation phase:** Task 1, Subtask 1.1, Step 1-2

---

#### Test 2: Status field accepts running value

**Name:** Session status field accepts 'running' value  
**Type:** Unit (model field validation)  
**Disposition:** New  
**Harness:** pytest  

**Preconditions:**
- Test 1 passes (status field exists)

**Actions:**
1. Create Session with status="running"
2. Assert session.status == "running"

**Expected outcome:**
- Source of truth: Feature requirement "status values: running, done, null"
- status field stores "running" correctly
- Value is retrievable

**Interactions:**
- Session dataclass constructor

**Implementation phase:** Task 1, Subtask 1.2, Step 1

---

#### Test 3: Status field accepts done value

**Name:** Session status field accepts 'done' value  
**Type:** Unit (model field validation)  
**Disposition:** New  
**Harness:** pytest  

**Preconditions:**
- Test 2 passes (status field accepts values)

**Actions:**
1. Create Session with status="done"
2. Assert session.status == "done"

**Expected outcome:**
- Source of truth: Feature requirement "status values: running, done, null"
- status field stores "done" correctly
- Value is retrievable

**Interactions:**
- Session dataclass constructor

**Implementation phase:** Task 1, Subtask 1.2, Step 2

---

### Phase 2: Parser Tests (4 tests)

#### Test 4: Parser extracts status=running

**Name:** Parser extracts status='running' from sessions.json  
**Type:** Integration (parser → JSON)  
**Disposition:** New  
**Harness:** pytest + tmp_path fixture  

**Preconditions:**
- Model tests pass (status field exists)
- Parser function parse_sessions_metadata exists

**Actions:**
1. Create temporary sessions.json with status="running"
2. Create corresponding session JSONL file
3. Call parse_sessions_metadata(sessions_file)
4. Assert returned metadata includes status="running"

**Expected outcome:**
- Source of truth: OpenClaw sessions.json format (status field)
- Parsed metadata dict contains 'status' key
- Value is "running"
- No exception raised

**Interactions:**
- File system (tmp_path)
- JSON parsing (json.load)
- parse_sessions_metadata function

**Implementation phase:** Task 2, Subtask 2.1, Steps 1-2

---

#### Test 5: Parser extracts status=done

**Name:** Parser extracts status='done' from sessions.json  
**Type:** Integration (parser → JSON)  
**Disposition:** New  
**Harness:** pytest + tmp_path fixture  

**Preconditions:**
- Test 4 passes (status extraction working)

**Actions:**
1. Create temporary sessions.json with status="done"
2. Create corresponding session JSONL file
3. Call parse_sessions_metadata(sessions_file)
4. Assert returned metadata includes status="done"

**Expected outcome:**
- Source of truth: Feature requirement "status='done' for inactive"
- Parsed metadata dict contains status="done"
- No exception raised

**Interactions:**
- File system (tmp_path)
- JSON parsing
- parse_sessions_metadata function

**Implementation phase:** Task 2, Subtask 2.2, Step 1

---

#### Test 6: Parser handles status=null

**Name:** Parser handles status=null in sessions.json  
**Type:** Boundary (null value handling)  
**Disposition:** New  
**Harness:** pytest + tmp_path fixture  

**Preconditions:**
- Test 5 passes (status extraction working)

**Actions:**
1. Create temporary sessions.json with status: null (JSON null)
2. Create corresponding session JSONL file
3. Call parse_sessions_metadata(sessions_file)
4. Assert returned metadata has status=None (Python None)

**Expected outcome:**
- Source of truth: Feature requirement "treat null as active/running"
- JSON null converts to Python None
- Parsed metadata dict contains status=None
- No exception raised

**Interactions:**
- File system (tmp_path)
- JSON parsing (handles null)
- parse_sessions_metadata function

**Implementation phase:** Task 2, Subtask 2.2, Step 1

---

#### Test 7: Parser handles missing status field

**Name:** Parser handles missing status field in sessions.json  
**Type:** Boundary (missing field handling)  
**Disposition:** New  
**Harness:** pytest + tmp_path fixture  

**Preconditions:**
- Test 6 passes (null handling working)

**Actions:**
1. Create temporary sessions.json without status field
2. Create corresponding session JSONL file
3. Call parse_sessions_metadata(sessions_file)
4. Assert returned metadata has status=None

**Expected outcome:**
- Source of truth: Feature requirement "handle missing status gracefully"
- .get() returns None for missing key
- Parsed metadata dict contains status=None
- No exception raised
- Defensive coding verified

**Interactions:**
- File system (tmp_path)
- JSON parsing
- parse_sessions_metadata function with .get()

**Implementation phase:** Task 2, Subtask 2.2, Step 1

---

### Phase 3: Dashboard Rendering Tests (3 tests)

#### Test 8: Dashboard displays status=running

**Name:** Dashboard displays Status column with RUNNING value  
**Type:** Integration (model → dashboard display)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode  

**Preconditions:**
- Model and parser tests pass
- Dashboard class exists with test_mode support
- Test file `tests/test_dashboard.py` created

**Actions:**
1. Create Dashboard with test_mode=True
2. Create Session with status="running"
3. Call dashboard.render(sessions)
4. Parse JSON output
5. Assert "running" appears in output

**Expected outcome:**
- Source of truth: Feature requirement "display RUNNING for running status"
- Test mode JSON includes session_status field
- Value is "running" (lowercase in JSON)
- Display format will be "RUNNING" in rich UI (verified manually)

**Interactions:**
- Dashboard._render_test_mode method
- Session model
- JSON output parsing

**Implementation phase:** Task 4, Subtask 4.1, Steps 1-2

---

#### Test 9: Dashboard displays status=done

**Name:** Dashboard displays Status column with DONE value  
**Type:** Integration (model → dashboard display)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode  

**Preconditions:**
- Test 8 passes (status display working)

**Actions:**
1. Create Dashboard with test_mode=True
2. Create Session with status="done"
3. Call dashboard.render(sessions)
4. Parse JSON output
5. Assert "done" appears in output

**Expected outcome:**
- Source of truth: Feature requirement "display DONE for done status"
- Test mode JSON includes session_status="done"
- Display format will be "DONE" in rich UI (verified manually)

**Interactions:**
- Dashboard._render_test_mode method
- Session model
- JSON output parsing

**Implementation phase:** Task 4, Subtask 4.1, Step 2

---

#### Test 10: Dashboard displays status=null

**Name:** Dashboard displays Status column with — for null status  
**Type:** Boundary (null display handling)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode  

**Preconditions:**
- Test 9 passes (status display working)

**Actions:**
1. Create Dashboard with test_mode=True
2. Create Session with status=None
3. Call dashboard.render(sessions)
4. Parse JSON output
5. Assert session appears with appropriate null handling

**Expected outcome:**
- Source of truth: Feature requirement "display — for null (treat as running)"
- Test mode JSON includes session with status or running indicator
- Display format will be "—" (em dash) in rich UI (verified manually)

**Interactions:**
- Dashboard._render_test_mode method
- Session model with null status
- JSON output parsing

**Implementation phase:** Task 4, Subtask 4.1, Step 2

---

### Phase 4: Primary Sorting Tests (1 test)

#### Test 11: Active sessions appear before done

**Name:** Dashboard sorts active sessions (running/null) before done  
**Type:** Scenario (primary sort logic)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode + JSON parsing  

**Preconditions:**
- Display tests pass (rendering working)

**Actions:**
1. Create Dashboard with test_mode=True
2. Create 3 sessions with same window % but different status:
   - status="done" (50% usage)
   - status="running" (50% usage)
   - status=None (50% usage)
3. Call dashboard.render(sessions)
4. Parse JSON output to get session order
5. Assert both running and null appear before done

**Expected outcome:**
- Source of truth: Feature requirement "primary sort: active before inactive"
- Session order: [running, null, done] (any order for running/null is fine)
- Both active sessions precede done session
- Window % is same, so only status affects order

**Interactions:**
- Dashboard._render_rich_ui method (via test_mode)
- Sort key function
- Session model with various statuses

**Implementation phase:** Task 4, Subtask 4.2, Steps 1-2

---

### Phase 5: Secondary Sorting Tests (2 tests)

#### Test 12: Active group sorted by window % descending

**Name:** Dashboard sorts active sessions by window % descending  
**Type:** Scenario (secondary sort within active group)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode + JSON parsing  

**Preconditions:**
- Primary sort test passes

**Actions:**
1. Create Dashboard with test_mode=True
2. Create 3 active sessions with different window %:
   - status="running", 25% usage
   - status="running", 90% usage
   - status=None, 50% usage
3. Call dashboard.render(sessions)
4. Parse JSON output to get session order
5. Assert order is: 90%, 50%, 25%

**Expected outcome:**
- Source of truth: Feature requirement "secondary sort: window % descending within group"
- Active sessions ordered by window % high to low
- Session order: [90%, 50%, 25%]
- All active sessions appear first (no done sessions to interfere)

**Interactions:**
- Dashboard sort key function
- Session.window_percent property
- Multiple Session objects

**Implementation phase:** Task 4, Subtask 4.3, Step 1

---

#### Test 13: Done group sorted by window % descending

**Name:** Dashboard sorts done sessions by window % descending  
**Type:** Scenario (secondary sort within done group)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode + JSON parsing  

**Preconditions:**
- Test 12 passes (secondary sort working in active group)

**Actions:**
1. Create Dashboard with test_mode=True
2. Create 3 sessions: 1 active (20%) and 2 done (75%, 15%)
3. Call dashboard.render(sessions)
4. Parse JSON output to get session order
5. Assert order is: active (20%), done (75%), done (15%)

**Expected outcome:**
- Source of truth: Feature requirement "secondary sort: window % descending within group"
- Active session appears first (even though it's only 20%)
- Done sessions follow, ordered by window % high to low
- Session order: [active-20%, done-75%, done-15%]

**Interactions:**
- Dashboard sort key function
- Primary sort (active first) and secondary sort (window % within group)
- Mixed session statuses

**Implementation phase:** Task 4, Subtask 4.3, Step 1

---

### Phase 6: Edge Case Tests (1 test)

#### Test 14: Empty sessions dict

**Name:** Dashboard handles empty sessions dict gracefully  
**Type:** Boundary (empty input)  
**Disposition:** New  
**Harness:** pytest + Dashboard test_mode  

**Preconditions:**
- Sorting tests pass

**Actions:**
1. Create Dashboard with test_mode=True
2. Call dashboard.render({})  # Empty dict
3. Parse JSON output
4. Assert sessions list is empty
5. Assert total_sessions is 0

**Expected outcome:**
- Source of truth: Defensive coding requirement
- No exception raised
- Output is valid JSON
- sessions array is empty
- total_sessions is 0

**Interactions:**
- Dashboard.render method
- Empty dict handling
- sorted() with empty iterable

**Implementation phase:** Task 4, Subtask 4.4, Step 1

---

## Manual Verification Tests

After all automated tests pass, perform manual verification of terminal UI appearance.

### Manual Test 1: Status column visual appearance

**Setup:**
1. Create test OpenClaw state directory with sessions.json
2. Include sessions with running, done, and null status
3. Run `session-monitor watch` against test directory

**Verify:**
- Status column appears between Label and Age
- Column width is appropriate (~8-10 chars)
- Status values display as:
  - "RUNNING" in green for status="running"
  - "DONE" in dim/gray for status="done"
  - "—" (em dash) in dim/gray for status=null
- Column header is "Status"
- Text is centered in column

---

### Manual Test 2: Sort order verification

**Setup:**
1. Use same test directory from Manual Test 1
2. Ensure sessions have varying window % and statuses

**Verify:**
- Active sessions (RUNNING, —) appear at top of table
- Done sessions (DONE) appear at bottom of table
- Within active group: highest window % at top
- Within done group: highest window % at top
- No visual glitches in table rendering

---

### Manual Test 3: Edge case rendering

**Setup:**
1. Test with empty OpenClaw state directory
2. Test with only active sessions
3. Test with only done sessions

**Verify:**
- Empty directory: shows "0 sessions" message
- All active: no DONE statuses visible
- All done: all DONE statuses visible
- No table rendering issues

---

## Test Execution Summary

**Automated Tests: 14 total**
- Phase 1 (Model): 3 tests
- Phase 2 (Parser): 4 tests
- Phase 3 (Dashboard Rendering): 3 tests
- Phase 4 (Primary Sorting): 1 test
- Phase 5 (Secondary Sorting): 2 tests
- Phase 6 (Edge Cases): 1 test

**Manual Tests: 3 scenarios**
- Visual appearance verification
- Sort order verification
- Edge case rendering verification

**Total Coverage:**
- All status values: running, done, null, missing ✓
- All display formats: RUNNING, DONE, — ✓
- Primary sort: active before done ✓
- Secondary sort: window % descending ✓
- Edge cases: empty ✓
- Integration: model → parser → monitor → dashboard ✓

**Acceptance Criteria:**
- All 14 automated tests pass ✓
- All 3 manual verification scenarios pass ✓
- No regressions in existing tests ✓
- Total project tests: 49 (35 existing + 14 new) ✓

---

## Test Dependencies

```
Models (3) ──────┬──→ Parser (4) ──→ Dashboard (7)
                 │                         │
                 └──→ Integration ─────────┘
                                ↓
                         Manual Tests (3)
```

**Execution order:**
1. Run model tests first (independent)
2. Run parser tests (depend on model)
3. Run dashboard tests (depend on model, indirectly on parser)
4. Run full suite (verify no regressions)
5. Perform manual verification (verify visual appearance)

---

## Success Metrics

**Code Coverage:**
- Session model: status field and property (100%)
- Parser: status extraction logic (100%)
- Dashboard: status display and sort logic (100%)
- Monitor: status passthrough (integration coverage)

**Functional Coverage:**
- All status values: 4/4 scenarios (running, done, null, missing)
- Display formats: 3/3 formats (RUNNING, DONE, —)
- Sort combinations: 3/3 cases (primary, secondary, edge cases)
- Error handling: 1/1 case (missing field)

**User Experience Coverage:**
- Visual appearance: Manual verification ✓
- Sort behavior: Automated + manual ✓
- Edge cases: Automated ✓
- No regressions: Full suite ✓

---

## Remember

- **TDD approach**: Red-green-refactor for each test
- **Test independence**: Each test should run in isolation
- **Clear assertions**: One primary assertion per test
- **Descriptive names**: Test names explain what they verify
- **Edge cases matter**: Empty, null, missing all need coverage
- **Manual verification required**: Terminal UI appearance needs human review
- **No regressions**: Existing tests must continue to pass
- **Fast execution**: All 14 tests should run in <5 seconds total
