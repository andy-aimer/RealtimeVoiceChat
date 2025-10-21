# Manual Browser Testing Guide - Phase 2 P3 WebSocket Lifecycle

**Test Date**: October 20, 2025  
**Tester**: Tom  
**Tasks**: T106-T107 Manual Browser Validation  
**Purpose**: Verify WebSocket reconnection, session persistence, and UI indicators in real browser environment

---

## Pre-Test Setup

### 1. Start the Test Server

**Note**: Due to scipy compatibility issues with the full voice processing server on Python 3.13/macOS ARM, use the minimal test server instead.

```bash
cd /Users/Tom/dev-projects/RealtimeVoiceChat
source venv/bin/activate
python test_server.py
```

**Expected Output**:

```
🧪 WebSocket Lifecycle Test Server
📍 Server will start on: http://localhost:8000
🔗 WebSocket endpoint: ws://localhost:8000/ws
💚 Health check: http://localhost:8000/health
✅ SessionManager initialized
✅ Background cleanup task started
Session cleanup task started (interval: 60s)
Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Verify Health Endpoint

Open in browser or curl:

```bash
curl http://localhost:8000/health
```

**Expected Response**:

```json
{
  "status": "healthy",
  "timestamp": "2025-10-20T...",
  "session_manager": {
    "active_sessions": 0,
    "total_created": 0,
    "total_expired": 0
  }
}
```

---

## Test Suite

### T106: WebSocket Reconnection Testing

#### Test 1.1: Initial Connection with New Session

**Steps**:

1. Open browser to `http://localhost:8000`
2. Open DevTools Console (Cmd+Option+J on macOS)
3. Look for connection logs

**Expected Behavior**:

- ✅ Status indicator shows "Connecting..." (orange)
- ✅ Status changes to "Connected" (green)
- ✅ Console log: `WebSocket connected successfully`
- ✅ Console log: `Session ID: <uuid>`
- ✅ No `session_id` in localStorage initially (check Application tab → Local Storage)
- ✅ After connection, `session_id` saved to localStorage

**Screenshot/Notes**:

```
[ ] Status indicator color correct
[ ] Console logs present
[ ] localStorage session_id saved
[ ] No errors in console
```

---

#### Test 1.2: Connection with Existing Session

**Steps**:

1. Keep browser tab open from Test 1.1 (session_id in localStorage)
2. Refresh page (Cmd+R)
3. Observe connection process

**Expected Behavior**:

- ✅ Status shows "Connecting..." → "Connected"
- ✅ Console log: `Attempting to restore session: <same-uuid-as-before>`
- ✅ Console log: `Session restored successfully`
- ✅ Same `session_id` in localStorage (no new ID generated)
- ✅ Connection completes within 2 seconds

**Screenshot/Notes**:

```
[ ] Session ID matches previous test
[ ] "Session restored" message appears
[ ] No new session created (check health endpoint)
[ ] Fast reconnection (<2s)
```

---

#### Test 1.3: Simulate Network Disconnect (DevTools Offline Mode)

**Steps**:

1. With connected WebSocket, open DevTools Network tab
2. Enable "Offline" mode (dropdown at top of Network tab)
3. Wait 2 seconds
4. Disable "Offline" mode
5. Observe reconnection behavior

**Expected Behavior**:

- ✅ Status changes: "Connected" → "Disconnected" (red)
- ✅ Status changes: "Disconnected" → "Reconnecting..." (orange)
- ✅ Console shows exponential backoff attempts:
  - Attempt 1: 1 second delay
  - Attempt 2: 2 second delay
  - Attempt 3: 4 second delay
- ✅ When back online, status → "Connected" (green)
- ✅ Console log: `Reconnected successfully`
- ✅ Same `session_id` preserved in localStorage

**Screenshot/Notes**:

```
[ ] Disconnect detected immediately
[ ] Exponential backoff visible in console
[ ] Backoff delays match: 1s, 2s, 4s...
[ ] Reconnection successful
[ ] Session ID unchanged
[ ] No conversation context lost
```

---

#### Test 1.4: Extended Disconnect (30+ seconds)

**Steps**:

1. Connected WebSocket
2. Enable DevTools Offline mode
3. Wait 35 seconds (watch console for backoff attempts)
4. Disable Offline mode
5. Observe reconnection

**Expected Behavior**:

- ✅ Backoff delays cap at 30 seconds:
  - Attempts 1-5: 1s, 2s, 4s, 8s, 16s
  - Attempts 6-10: 30s, 30s, 30s, 30s, 30s
- ✅ After 10 attempts, status → "Reconnect Failed" (red)
- ✅ Console log: `Max reconnection attempts reached`
- ✅ When back online, manual reconnect required OR page refresh
- ✅ After refresh, session restored (if <5 minutes elapsed)

**Screenshot/Notes**:

```
[ ] Backoff caps at 30 seconds
[ ] Max attempts = 10
[ ] Clear failure message displayed
[ ] Session restoration works after manual reconnect
```

---

#### Test 1.5: Multiple Disconnect/Reconnect Cycles

**Steps**:

1. Connected WebSocket
2. Toggle offline mode 5 times with 5-second intervals:
   - Offline → wait 5s → Online → wait 5s → repeat
3. Observe session persistence

**Expected Behavior**:

- ✅ Each disconnect triggers reconnection logic
- ✅ Backoff resets after successful reconnection
- ✅ Same `session_id` maintained throughout all cycles
- ✅ No memory leaks (check DevTools Performance → Memory)
- ✅ Status indicator updates correctly for each cycle

**Screenshot/Notes**:

```
[ ] Backoff resets work correctly
[ ] Session ID consistent across all cycles
[ ] No JavaScript errors
[ ] Memory usage stable
```

---

### T107: Session Persistence and Context Preservation

#### Test 2.1: Session Expiration (5-minute timeout)

**Steps**:

1. Connect to WebSocket
2. Note the `session_id` in localStorage
3. Close browser tab (disconnect)
4. Wait 6 minutes
5. Open new tab to `http://localhost:8000`
6. Check console logs

**Expected Behavior**:

- ✅ Old session expired (not in server memory)
- ✅ Console log: `Previous session expired or not found`
- ✅ New `session_id` generated and saved to localStorage
- ✅ Connection successful with new session
- ✅ Health endpoint shows `total_expired: 1` (or more)

**Screenshot/Notes**:

```
[ ] Old session_id no longer valid
[ ] New session_id generated
[ ] Expiration message in console
[ ] Health endpoint reflects expiration
```

---

#### Test 2.2: Session Preservation (<5 minutes)

**Steps**:

1. Connect to WebSocket
2. Send a text message (if UI supports): "Test message 1"
3. Note `session_id` in localStorage
4. Close browser tab
5. Wait 2 minutes
6. Open new tab to `http://localhost:8000`
7. Check if session restored

**Expected Behavior**:

- ✅ Console log: `Session restored successfully`
- ✅ Same `session_id` as before
- ✅ Conversation context preserved (if server stores messages)
- ✅ Connection within 2 seconds
- ✅ No new session created

**Screenshot/Notes**:

```
[ ] Session restored after 2-minute gap
[ ] session_id matches previous
[ ] Context preserved (if applicable)
[ ] Fast restoration (<2s)
```

---

#### Test 2.3: localStorage Cleared (No session_id)

**Steps**:

1. Connect to WebSocket
2. Note `session_id` in localStorage
3. Open DevTools → Application → Local Storage
4. Delete the `session_id` entry
5. Refresh page

**Expected Behavior**:

- ✅ Console log: `No previous session_id found`
- ✅ New `session_id` generated
- ✅ New session created on server
- ✅ Connection successful
- ✅ Health endpoint shows `total_created` incremented

**Screenshot/Notes**:

```
[ ] New session created after localStorage clear
[ ] No errors during new session creation
[ ] Different session_id than previous
```

---

#### Test 2.4: Cross-Browser Session Isolation

**Steps**:

1. Open `http://localhost:8000` in Chrome
2. Note `session_id` in Chrome's localStorage
3. Open `http://localhost:8000` in Firefox (or Safari)
4. Note `session_id` in Firefox's localStorage
5. Compare session IDs

**Expected Behavior**:

- ✅ Different `session_id` in each browser (localStorage is browser-specific)
- ✅ Both sessions active simultaneously (check health endpoint)
- ✅ Each browser maintains its own session independently
- ✅ No cross-contamination of session data

**Screenshot/Notes**:

```
[ ] Chrome session_id: __________
[ ] Firefox session_id: __________
[ ] Session IDs are different
[ ] Health endpoint shows 2 active sessions
```

---

#### Test 2.5: Background Cleanup Validation

**Steps**:

1. Connect 3 WebSocket sessions (3 browser tabs)
2. Note all 3 `session_id` values
3. Close all 3 tabs
4. Wait 6 minutes (for cleanup + expiration)
5. Check health endpoint: `curl http://localhost:8000/health`
6. Open new connection

**Expected Behavior**:

- ✅ Health endpoint after 6 minutes:
  - `active_sessions: 0` (all expired and cleaned up)
  - `total_expired: 3` (or cumulative count)
- ✅ Background cleanup task logs visible in server console
- ✅ New connection creates new session (old ones purged)

**Screenshot/Notes**:

```
[ ] All 3 sessions expired
[ ] Cleanup task ran (server logs)
[ ] active_sessions = 0 after cleanup
[ ] Memory freed (server memory stable)
```

---

## UI Status Indicator Validation

### Test 3.1: Status Colors and Text

**Steps**:

1. Observe status indicator during various states:
   - Initial page load
   - Connection established
   - Manual disconnect (DevTools offline)
   - Reconnecting phase
   - Reconnection success
   - Reconnection failure (after 10 attempts)

**Expected Status States**:
| State | Color | Text | CSS Class |
|-------|-------|------|-----------|
| Connecting | 🟠 Orange | "Connecting..." | `.status-connecting` |
| Connected | 🟢 Green | "Connected" | `.status-connected` |
| Disconnected | 🔴 Red | "Disconnected" | `.status-disconnected` |
| Reconnecting (Attempt 1) | 🟠 Orange | "Reconnecting... (1/10)" | `.status-reconnecting` |
| Reconnecting (Attempt 5) | 🟠 Orange | "Reconnecting... (5/10)" | `.status-reconnecting` |
| Reconnect Failed | 🔴 Red | "Reconnect Failed" | `.status-reconnect-failed` |
| Reconnected | 🟢 Green | "Reconnected" → "Connected" | `.status-reconnected` → `.status-connected` |

**Screenshot/Notes**:

```
[ ] All colors correct per table above
[ ] Text matches expected states
[ ] Attempt counter increments (1/10, 2/10, etc.)
[ ] Status updates smoothly (no flickering)
```

---

## Performance Observations

### Test 4.1: Reconnection Latency

**Steps**:

1. Connected WebSocket
2. Enable DevTools Network tab
3. Trigger disconnect (offline mode)
4. Wait for 1st reconnect attempt
5. Re-enable network
6. Measure time from "Reconnecting..." to "Connected"

**Expected Performance**:

- ✅ First reconnection attempt: 1 second after disconnect
- ✅ Connection establishment: <2 seconds (network dependent)
- ✅ Session restoration: <10ms (server-side lookup)
- ✅ Total reconnection time: <3 seconds for first attempt

**Screenshot/Notes**:

```
[ ] First attempt delay = 1s
[ ] Connection time < 2s
[ ] Total < 3s
[ ] No lag in UI updates
```

---

### Test 4.2: Memory Leak Check (Extended Session)

**Steps**:

1. Open DevTools → Performance → Memory profiler
2. Take heap snapshot
3. Connect WebSocket and keep active for 10 minutes
4. Perform 20 disconnect/reconnect cycles (10s apart)
5. Take second heap snapshot
6. Compare memory usage

**Expected Behavior**:

- ✅ Memory growth <5MB over 10 minutes
- ✅ No detached DOM nodes accumulating
- ✅ Event listeners cleaned up after disconnect
- ✅ Stable memory after reconnection cycles

**Screenshot/Notes**:

```
[ ] Initial heap size: ______ MB
[ ] Final heap size: ______ MB
[ ] Growth acceptable (<5MB)
[ ] No memory warnings in console
```

---

## Browser Compatibility

### Test 5.1: Cross-Browser Validation

**Browsers to Test**:

- ✅ Chrome/Chromium (version: **\_**)
- ✅ Firefox (version: **\_**)
- ✅ Safari (macOS) (version: **\_**)

**Per Browser, Verify**:

1. Initial connection works
2. Reconnection logic functions
3. localStorage session_id persists
4. Status indicators display correctly
5. Console logs appear
6. No browser-specific errors

**Screenshot/Notes**:

```
Chrome:
[ ] All features working
[ ] No console errors
[ ] Version: __________

Firefox:
[ ] All features working
[ ] No console errors
[ ] Version: __________

Safari:
[ ] All features working
[ ] No console errors
[ ] Version: __________
```

---

## Test Results Summary

### Completion Checklist

- [ ] T106: WebSocket reconnection tested (5 tests)
- [ ] T107: Session persistence tested (5 tests)
- [ ] UI status indicators validated (1 test)
- [ ] Performance observations documented (2 tests)
- [ ] Browser compatibility verified (3 browsers)

### Issues Found

| Issue # | Severity | Description | Status |
| ------- | -------- | ----------- | ------ |
| 1       |          |             |        |
| 2       |          |             |        |
| 3       |          |             |        |

### Overall Assessment

**Pass Criteria**:

- ✅ All 10 manual tests pass
- ✅ No critical errors in any browser
- ✅ Reconnection works within expected timeframes
- ✅ Session persistence works <5 minutes
- ✅ UI indicators update correctly

**Result**: [ PASS / FAIL / PARTIAL ]

**Notes**:

```
[Add final observations, edge cases discovered, or recommendations]
```

---

## Next Steps

After completing manual tests:

1. Document any issues found in GitHub Issues or tasks.md
2. Update `specs/002-test-thermal-websocket/tasks.md`:
   - Mark T106 as [x] with notes
   - Mark T107 as [x] with notes
3. Proceed to **Phase 2 Polish & Validation** (T108-T125)
4. Generate final test report for Phase 2 P3
