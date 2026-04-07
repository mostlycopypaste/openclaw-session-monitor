# OpenClaw Session Memory Monitor - Implementation Plan

## Executive Summary

**Project**: Real-time OpenClaw session token usage monitoring tool  
**Goal**: Provide visibility into context window consumption to avoid unexpected session resets  
**Approach**: File-watching Python tool with terminal dashboard  
**Timeline**: 18 hours MVP (Phases 1-3), 30 hours full implementation  
**Risk Level**: Low (read-only, <2% overhead target)

## Problem Statement

OpenClaw sessions frequently hit the 200K token context window limit without warning, forcing users to restart conversations and lose continuity. Current tools provide only historical aggregates (`openclaw usage-cost`), with no real-time visibility or per-message breakdown. This results in:

- 3-4 unexpected session resets per day
- 30-45 minutes daily spent debugging context issues
- No data to optimize compaction settings or identify expensive operations
- Users flying blind on token consumption

## Architecture

### System Design

```
Session JSONL Files → File Watcher → Incremental Parser → Live Dashboard
    (source)          (inotify)      (extract tokens)     (terminal UI)
```

### Key Design Decisions

#### 1. File Watching vs Gateway API Polling

**Decision**: Use file watching (inotify/FSEvents)

**Rationale**:
- Gateway API doesn't expose per-message token streaming
- Polling adds 10x overhead vs event-driven monitoring
- Session files already contain all needed data (tokens, timestamps, roles)
- Read-only file access has zero impact on OpenClaw performance

#### 2. Python vs Shell Script

**Decision**: Python with `watchdog` and `rich` libraries

**Rationale**:
- `watchdog`: Cross-platform file monitoring with <1% CPU overhead
- `rich`: Industry-standard terminal UI with live updates, tables, colors
- Better maintainability than shell scripts for complex logic
- Easy to add analysis features incrementally

#### 3. In-Memory State vs File Seeking

**Decision**: Track file positions, read incrementally

**Rationale**:
- Session files can be 8MB+ (current largest observed)
- Reading full files on each change would waste I/O
- Incremental reads: read only new lines appended since last position
- Memory footprint: <30MB target (just position tracking + recent messages)

#### 4. Terminal UI vs Web UI

**Decision**: Terminal UI for MVP, Web UI as Phase 6 (future)

**Rationale**:
- Faster to build (18 hours vs 40+ hours for web UI)
- Users are already terminal-comfortable (OpenClaw is CLI-heavy)
- `rich` provides excellent UX with tables, colors, live updates
- Can add web UI later if terminal proves insufficient

#### 5. Sandbox Mode vs Gateway Execution

**Decision**: Run on gateway (host), not in sandbox

**Rationale**:
- Monitoring tool needs access to session files on host filesystem
- Sandbox doesn't have Python by default
- Read-only operations don't require isolation
- Simpler deployment (no Docker configuration needed)

#### 6. Alert Thresholds

**Decision**: Warning at 160K tokens (80%), Critical at 180K tokens (90%)

**Rationale**:
- 80%: Early warning, time to finish current task and start new session
- 90%: Critical, compaction imminent or session reset needed
- Thresholds configurable via CLI flags for user preference
- Based on observed compaction trigger points in research

## Implementation Phases

### Phase 1: Core Parser (6 hours)

**Goal**: Prove we can read session data without impacting OpenClaw

**Components**:

1. **sessions.json Reader** (`session_manager.py`)
   - Parse `~/.openclaw-primary/agents/*/sessions/sessions.json`
   - Extract active sessions (filter out `.reset`, `.deleted`)
   - Return: sessionId, label, agent, updatedAt, status

2. **JSONL Parser** (`jsonl_parser.py`)
   - Read session JSONL files incrementally
   - Extract per-message: `timestamp`, `role`, `usage.totalTokens`, `usage.input`, `usage.output`, `stopReason`
   - Track file position to avoid re-reading
   - Handle malformed lines gracefully (skip, log warning)

3. **Token Aggregator** (`token_aggregator.py`)
   - Sum tokens per session (lifetime total)
   - Calculate context window utilization (% of 200K)
   - Track tokens by role (user/assistant/tool breakdown)

**Deliverables**:
- `session_manager.py`: Session metadata reader
- `jsonl_parser.py`: Incremental JSONL parser
- `token_aggregator.py`: Token counting logic
- `test_parser.py`: Unit tests
- Performance benchmark script

**Success Criteria**:
- Parse 8MB session file in <500ms
- CPU usage <2% while monitoring 5 sessions
- Memory usage <30MB
- No file locking conflicts with OpenClaw

**Tests**:
```python
# Test: Parse existing session
def test_parse_session():
    session = parse_session("~/.openclaw-primary/agents/main/sessions/5f3febb2.jsonl")
    assert session.total_tokens > 0
    assert session.total_tokens <= 200000
    
# Test: Incremental read
def test_incremental_read():
    pos = 0
    messages1, pos = read_messages("session.jsonl", pos)
    append_message("session.jsonl", {"role": "user", "usage": {"totalTokens": 100}})
    messages2, pos = read_messages("session.jsonl", pos)
    assert len(messages2) == 1  # Only new message
```

### Phase 2: File Watcher (4 hours)

**Goal**: Real-time detection of new messages (<1s latency)

**Components**:

1. **Session Watcher** (`session_watcher.py`)
   - Use `watchdog.observers.Observer` for event-driven monitoring
   - Monitor `~/.openclaw-primary/agents/*/sessions/*.jsonl`
   - Track file positions per session
   - Emit events: `SessionCreated`, `MessageAdded`, `SessionUpdated`, `SessionEnded`

2. **Event Dispatcher** (`event_dispatcher.py`)
   - Queue events for processing
   - Batch rapid events (avoid thrashing on burst writes)
   - Thread-safe (watcher runs in background thread)

**Deliverables**:
- `session_watcher.py`: File watching with watchdog
- `event_dispatcher.py`: Event handling and batching
- `test_watcher.py`: Integration tests
- Benchmark: measure detection latency

**Success Criteria**:
- Detect new messages within 1 second
- No duplicate message processing
- Handle 10+ sessions simultaneously without dropped events
- Graceful degradation if inotify fails (fallback to polling)

**Tests**:
```python
# Test: Event detection
def test_message_detection():
    watcher = SessionWatcher()
    events = []
    watcher.on_message = lambda e: events.append(e)
    watcher.start()
    
    append_to_session("test.jsonl", new_message)
    time.sleep(0.5)
    
    assert len(events) == 1
    assert events[0].type == "MessageAdded"
```

### Phase 3: Live Dashboard (8 hours)

**Goal**: Visual real-time monitoring in terminal

**Components**:

1. **Dashboard UI** (`dashboard.py`)
   - Use `rich.live.Live` for auto-refreshing display
   - Three panels:
     - **Summary**: Total sessions, aggregate tokens, alerts
     - **Session Table**: Per-session breakdown (ID, label, tokens, %, status)
     - **Message Stream**: Scrolling log of recent messages (last 20)

2. **Session Table Layout**:
   ```
   Agent | Session ID    | Label           | Tokens  | Window % | Last Activity | Status
   ------|---------------|-----------------|---------|----------|---------------|-------
   main  | 5f3febb2-ebd  | main:heartbeat  | 145,234 | 73%      | 2s ago        | Active
   main  | 9e1a5a15-ad3  | claude:herd     | 12,456  | 6%       | 30s ago       | Idle
   ```

3. **Message Stream Format**:
   ```
   [10:45:32] main:heartbeat     +1,234 tokens  (user: check email)
   [10:45:45] main:heartbeat     +8,912 tokens  (assistant: executed check + 3 reads)
   [10:46:15] main:heartbeat     +125,000 tokens (⚠️  COMPACTION TRIGGERED)
   [10:46:18] main:heartbeat     -98,000 tokens  (✅ COMPACTION: 125K → 27K)
   ```

4. **Alerts**:
   - 🟡 Warning (160K+): Yellow highlight on session row
   - 🔴 Critical (180K+): Red highlight + bold
   - ⚠️ Spike: Messages >10K tokens highlighted
   - 🔥 Rapid Growth: >50K tokens in 5 minutes

5. **Keyboard Controls**:
   - `q`: Quit
   - `r`: Force refresh
   - `c`: Clear message stream
   - `f`: Toggle freeze (pause updates)
   - `s`: Sort sessions (by tokens, time, agent)

**Deliverables**:
- `dashboard.py`: Main UI with rich library
- `formatters.py`: Token formatting, time deltas, colors
- `alerts.py`: Alert detection and highlighting
- `test_dashboard.py`: UI tests (smoke tests only, visual verification manual)

**Success Criteria**:
- Dashboard updates every 1 second
- Responsive keyboard input (<100ms)
- Works over SSH (no color issues)
- Handles 10+ sessions without UI flicker
- Provides `--simple` flag for plain text output (no colors/tables)

**Tests**:
```python
# Test: Alert detection
def test_alert_detection():
    session = Session(tokens=165000)
    alert = check_alert(session)
    assert alert.level == "warning"
    assert alert.message == "Context window 82% full"
    
# Test: Formatting
def test_format_tokens():
    assert format_tokens(1234) == "1,234"
    assert format_tokens(145234) == "145,234"
    assert format_tokens(1500000) == "1,500,000"
```

### Phase 4: Analysis Features (6 hours)

**Goal**: Identify what's consuming tokens

**Components**:

1. **Message Breakdown** (`analyzer.py`)
   - Count tokens by role: user, assistant, tool
   - Identify expensive operations:
     - Tool results by type (read, grep, bash, etc.)
     - Messages >10K tokens (extract command/context)
   - Track memory file loads at session start

2. **Compaction Analysis**:
   - Detect compaction events:
     - `stopReason: "length_limit"` in messages
     - Sudden drop in total tokens (>50K decrease)
   - Calculate tokens reclaimed (before - after)
   - Track compaction frequency per session

3. **Report Generation** (`reports.py`):
   - Export to Obsidian markdown
   - Sections:
     - Session summary (lifetime, tokens, compactions)
     - Top 10 expensive operations
     - Token breakdown by role
     - Compaction effectiveness
     - Recommendations (reduce memory loads, optimize prompts)

**Deliverables**:
- `analyzer.py`: Token analysis by role and operation
- `compaction_detector.py`: Detect and measure compaction
- `reports.py`: Generate markdown reports
- CLI command: `session-monitor analyze <session-id> --report`

**Success Criteria**:
- Identify top 3 token consumers within 1 week of use
- Accurately detect compaction events (100% recall)
- Reports actionable (specific commands/files identified)

**Example Analysis Output**:
```markdown
# Session Analysis: main:heartbeat (5f3febb2)

## Summary
- Total Tokens: 145,234 (73% of 200K)
- Duration: 3h 24m
- Compactions: 2
- Messages: 89

## Token Breakdown
- User: 12,456 tokens (8.6%)
- Assistant: 89,123 tokens (61.4%)
- Tool: 43,655 tokens (30.0%)

## Top 10 Expensive Operations
1. Read `/workspace/scripts/herd_mail.py` - 12,345 tokens
2. Grep "openclaw" in workspace - 8,912 tokens
3. Bash: `openclaw config get tools` - 6,543 tokens
...

## Compaction Events
1. At 125,000 tokens → 27,000 tokens (98K reclaimed, 78%)
2. At 180,000 tokens → 32,000 tokens (148K reclaimed, 82%)

## Recommendations
- Memory loads: Consider reducing CLAUDE.md size (current: 15K tokens)
- File reads: Use `limit` parameter for large files (3 reads >10K tokens)
- Compaction: Current frequency is appropriate for workload
```

### Phase 5: Historical Trending (6 hours)

**Goal**: Track token usage over days/weeks

**Components**:

1. **Metrics Exporter** (`metrics_exporter.py`)
   - Run as background process or cron job (every 5 minutes)
   - Append summaries to `~/.openclaw/monitoring.jsonl`
   - Format:
     ```json
     {
       "timestamp": "2026-04-07T12:34:56Z",
       "sessionId": "5f3febb2-ebdd-4b1c-a933-48c23c159f01",
       "agent": "main",
       "label": "main:heartbeat",
       "totalTokens": 145234,
       "windowPercent": 0.73,
       "messagesCount": 89,
       "compactionCount": 2,
       "lastCompactionAt": "2026-04-07T10:15:30Z",
       "tokensReclaimed": 98000
     }
     ```

2. **Metrics Viewer** (`metrics_viewer.py`)
   - Query historical data
   - Generate plots: token usage over time (7/30 days)
   - Identify patterns:
     - Sessions that repeatedly hit limits
     - Time-of-day usage patterns
     - Agent comparison (main vs claude vs rescue)

3. **Trend Analysis**:
   - Calculate moving averages (daily, weekly)
   - Detect anomalies (unusual spikes)
   - Predict when session will hit limit (linear extrapolation)

**Deliverables**:
- `metrics_exporter.py`: Background metrics collection
- `metrics_viewer.py`: Query and plot historical data
- CLI commands:
  - `session-monitor metrics export` (start background exporter)
  - `session-monitor metrics view --days 7` (show trends)
  - `session-monitor metrics report` (weekly summary to Obsidian)

**Success Criteria**:
- Metrics export <1% CPU overhead
- Historical data queryable (<1s for 7 days)
- Trends identify optimization opportunities

**Example Trend Output**:
```
Token Usage Trends (Last 7 Days)

Average Session Tokens:
  main:      89,234 tokens/session (44.6%)
  claude:    23,456 tokens/session (11.7%)
  
Peak Usage Times:
  10am-12pm: 145K avg (morning standup + email checks)
  2pm-4pm:   98K avg (afternoon coding)
  
Sessions Hitting Limits:
  main:heartbeat - 3 resets this week (down from 7 last week)
  
Recommendation: Morning email checks consuming 45K tokens avg.
  Consider running herd-mail separately from main OC session.
```

### Phase 6: Optional - Integration Improvements (Future)

**Components**:
- OpenClaw plugin integration (show token % in prompt)
- Web UI for remote monitoring
- Slack/Discord notifications for critical alerts
- Auto-suggest `/new` when approaching limits
- Compaction tuning recommendations

## File Structure

```
openclaw-session-monitor/
├── README.md                    # Project overview, installation, usage
├── PLAN.md                      # This implementation plan
├── pyproject.toml               # Python project config (uv-compatible)
├── requirements.txt             # Dependencies
├── .gitignore                   # Python, venv, logs
│
├── src/
│   ├── __init__.py
│   ├── session_manager.py       # Read sessions.json, list active sessions
│   ├── jsonl_parser.py          # Incremental JSONL parsing
│   ├── token_aggregator.py      # Token counting and aggregation
│   ├── session_watcher.py       # File watching with watchdog
│   ├── event_dispatcher.py      # Event handling and batching
│   ├── dashboard.py             # Terminal UI with rich
│   ├── formatters.py            # Token/time/color formatting
│   ├── alerts.py                # Alert detection logic
│   ├── analyzer.py              # Token analysis by role/operation
│   ├── compaction_detector.py   # Detect and measure compaction
│   ├── reports.py               # Markdown report generation
│   ├── metrics_exporter.py      # Historical metrics collection
│   ├── metrics_viewer.py        # Query and plot metrics
│   └── cli.py                   # Main CLI entry point
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py           # Parser unit tests
│   ├── test_watcher.py          # Watcher integration tests
│   ├── test_aggregator.py       # Token counting tests
│   ├── test_alerts.py           # Alert detection tests
│   ├── test_analyzer.py         # Analysis logic tests
│   ├── fixtures/                # Test session files
│   │   ├── sessions.json
│   │   └── test-session.jsonl
│   └── conftest.py              # Pytest configuration
│
├── scripts/
│   └── benchmark.py             # Performance benchmarking
│
└── docs/
    ├── ARCHITECTURE.md          # System design details
    ├── CONFIGURATION.md         # Config options
    └── TROUBLESHOOTING.md       # Common issues
```

## Dependencies

```toml
# pyproject.toml
[project]
name = "openclaw-session-monitor"
version = "0.1.0"
requires-python = ">=3.8"
dependencies = [
    "watchdog>=4.0.0",      # File monitoring
    "rich>=13.0.0",         # Terminal UI
    "jsonlines>=4.0.0",     # JSONL parsing
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
session-monitor = "src.cli:main"
```

## Configuration

**CLI Arguments**:
```bash
# Start live monitoring
session-monitor watch [--agent AGENT] [--simple] [--refresh-rate SECONDS]

# Analyze session
session-monitor analyze SESSION_ID [--report] [--output PATH]

# Export metrics
session-monitor metrics export [--interval MINUTES]

# View trends
session-monitor metrics view [--days N] [--agent AGENT]

# List sessions
session-monitor list [--agent AGENT] [--status STATUS]
```

**Environment Variables**:
```bash
# Override OpenClaw state directory
OPENCLAW_STATE_DIR=/path/to/.openclaw-primary

# Context window size (default: 200000)
OPENCLAW_CONTEXT_TOKENS=200000

# Alert thresholds (default: 0.8, 0.9)
OPENCLAW_WARN_THRESHOLD=0.8
OPENCLAW_CRIT_THRESHOLD=0.9
```

**Config File** (optional: `~/.openclaw/monitor-config.json`):
```json
{
  "stateDir": "/Users/kduane/.openclaw-primary",
  "contextTokens": 200000,
  "alerts": {
    "warnThreshold": 0.8,
    "critThreshold": 0.9,
    "spikeThreshold": 10000,
    "rapidGrowthWindow": 300,
    "rapidGrowthTokens": 50000
  },
  "display": {
    "refreshRate": 1,
    "messageLogSize": 20,
    "simpleMode": false
  },
  "metrics": {
    "enabled": true,
    "exportInterval": 300,
    "retentionDays": 30
  }
}
```

## Error Handling

### File System Issues

1. **Permission denied** reading session files:
   - Error message: "Cannot read session files. Check permissions for ~/.openclaw-primary/agents/"
   - Resolution: Suggest `chmod` or running as correct user

2. **Session file doesn't exist**:
   - Graceful skip, log warning
   - Continue monitoring other sessions

3. **Malformed JSONL**:
   - Skip invalid lines, log warning with line number
   - Don't crash entire parser

### Watchdog Issues

1. **inotify limit reached** (Linux):
   - Error message: "File watching limit reached. Increase fs.inotify.max_user_watches or use --polling mode"
   - Fallback: Switch to polling mode (5s interval)

2. **External volume unmounted**:
   - Detect filesystem change
   - Pause monitoring, show error
   - Resume when volume remounts

### OpenClaw Changes

1. **JSONL format change**:
   - Version check on startup (read OpenClaw version from CLI)
   - If unknown fields: log warning, continue with known fields
   - If critical fields missing: error, suggest upgrade

2. **Session file location change**:
   - Allow override via env var or CLI flag
   - Detect and suggest correct path

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **CPU usage** | <2% avg | Measured with `top` during monitoring |
| **Memory usage** | <30MB | RSS measured with `ps` |
| **File read latency** | <500ms for 8MB file | Benchmark script |
| **Event detection latency** | <1s | Integration test |
| **Dashboard refresh rate** | 1 Hz (1s) | UI renders per second |
| **Parse throughput** | 100+ messages/sec | Benchmark with 1000-message file |

## Testing Strategy

### Unit Tests (pytest)

- **Parser tests**: Verify token extraction, incremental reading
- **Aggregator tests**: Verify token summing, percentage calculations
- **Alert tests**: Verify threshold detection, formatting
- **Analyzer tests**: Verify role breakdown, operation identification

### Integration Tests

- **Watcher tests**: Verify event detection, no duplicates
- **End-to-end**: Create test session, append messages, verify dashboard updates

### Performance Tests

- **Benchmark script**: Measure parse time for various file sizes (1MB, 5MB, 10MB)
- **Load test**: Monitor 10+ sessions, verify no slowdown
- **Memory profiling**: Use `memory_profiler` to find leaks

### Manual Testing

- **Real session monitoring**: Run against actual OpenClaw sessions for 1 week
- **SSH compatibility**: Test dashboard over SSH connection
- **Compaction detection**: Trigger compaction, verify detection

## Deployment

### Installation

```bash
# Clone repo
git clone https://github.com/user/openclaw-session-monitor
cd openclaw-session-monitor

# Install with uv (preferred)
uv venv
source .venv/bin/activate
uv pip install -e .

# Or with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### System Requirements

- **Python**: 3.8+ (check: `python3 --version`)
- **OpenClaw**: 2026.4.0+ (check: `openclaw --version`)
- **OS**: macOS, Linux (inotify support), or Windows (experimental)
- **Disk**: 50MB for logs (monitoring.jsonl grows ~1MB/week)

### Systemd Service (Linux - Optional)

```ini
# /etc/systemd/system/openclaw-monitor.service
[Unit]
Description=OpenClaw Session Monitor
After=network.target

[Service]
Type=simple
User=kduane
WorkingDirectory=/home/kduane/.openclaw
ExecStart=/path/to/venv/bin/session-monitor watch
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### LaunchAgent (macOS - Optional)

```xml
<!-- ~/Library/LaunchAgents/ai.openclaw.monitor.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.openclaw.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/session-monitor</string>
        <string>watch</string>
        <string>--simple</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/kduane/.openclaw-primary/logs/monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/kduane/.openclaw-primary/logs/monitor.err.log</string>
</dict>
</plist>
```

## Risks & Mitigations

### Risk 1: Monitoring Adds to Memory Problem

**Likelihood**: Low  
**Impact**: High  
**Mitigation**:
- Enforce <30MB memory limit (test with `pytest-memprof`)
- No in-memory caching of full session history
- Incremental file reading only
- Kill switch: If >50MB RAM detected, exit with error

### Risk 2: OpenClaw Changes JSONL Format

**Likelihood**: Medium  
**Impact**: High  
**Mitigation**:
- Version check on startup
- Graceful degradation: work with subset of fields if format changes
- Unit tests with multiple JSONL format versions
- Document supported OpenClaw versions in README

### Risk 3: File Watching Breaks on Network Filesystems

**Likelihood**: Low (user's setup uses external volume but not network FS)  
**Impact**: Medium  
**Mitigation**:
- Detect unsupported filesystems (NFS, SMB)
- Automatic fallback to polling mode
- Error message with resolution steps

### Risk 4: Dashboard Unreadable Over SSH

**Likelihood**: Low  
**Impact**: Low  
**Mitigation**:
- `--simple` flag for plain text output
- Test over SSH during development
- Document terminal emulator requirements

### Risk 5: Abandoned After Implementation

**Likelihood**: Medium  
**Impact**: Medium  
**Mitigation**:
- Integrate into daily workflow (alias, cron job)
- Metrics export provides long-term value even if dashboard unused
- Document thoroughly for easy pickup after break

## Success Criteria

### MVP (Phases 1-3) Success

After 1 week of use:
1. ✅ Zero crashes or errors during monitoring
2. ✅ Session resets reduced by >50% (from 3-4/day to <2/day)
3. ✅ User can identify top 3 token consumers
4. ✅ Compaction events detected with >95% accuracy
5. ✅ Performance: <2% CPU, <30MB RAM
6. ✅ User uses tool daily without manual intervention

### Full Implementation Success

After 1 month of use:
1. ✅ Historical metrics identify optimization opportunities
2. ✅ At least 2 actionable changes made based on monitoring data
3. ✅ Session lifetime increased by >30% (2-3 hours → 3-4 hours)
4. ✅ User considers tool essential (would reinstall after OS wipe)
5. ✅ Community interest (if shared, 10+ stars/forks)

## Future Enhancements

**Phase 6+** (not in initial scope):
1. **OpenClaw Plugin**: Show token % in shell prompt
2. **Web UI**: Browser-based dashboard for remote monitoring
3. **Notifications**: Slack/Discord alerts for critical thresholds
4. **Auto-optimization**: Suggest compaction tuning, memory reduction
5. **Multi-user**: Support multiple OpenClaw installations
6. **Prediction**: ML-based prediction of when session will hit limit
7. **Comparison**: Compare token efficiency across agents/sessions

## Appendix

### A. Research Summary

**Existing OpenClaw Tools**:
- `openclaw usage-cost`: Historical token aggregates (not real-time)
- `openclaw dashboard`: Web UI (no token metrics)
- `oc-monitor.mjs`: Community tool (not token-focused)

**Key Findings**:
- Session files already track `total_tokens` per message (no estimation needed)
- Append-only JSONL is safe for concurrent reading
- File watching has near-zero overhead (<1% CPU)
- Gateway API doesn't expose real-time token streaming

**Performance Benchmarks** (from research):
- Reading 8.3MB session file: <500ms
- Watchdog event detection: <100ms
- Memory footprint: <30MB for monitoring 10 sessions

### B. Alternative Approaches Rejected

1. **Gateway API Polling**: Doesn't provide per-message granularity, higher overhead
2. **Shell Script**: Limited UI, harder to maintain complex logic
3. **Modify OpenClaw Core**: Requires upstream approval, weeks timeline
4. **Do Nothing**: Problem persists, productivity loss continues

### C. References

- OpenClaw Sessions CLI: https://docs.openclaw.ai/cli/sessions
- Gateway RPC API: https://docs.openclaw.ai/gateway/rpc
- Compaction Config: https://docs.openclaw.ai/config/compaction
- `watchdog` library: https://pypi.org/project/watchdog/
- `rich` library: https://rich.readthedocs.io/

### D. Implementation Sequence

```
Week 1:
  Day 1: Setup project, Phase 1 (Core Parser) - 6 hours
  Day 2: Phase 1 completion, performance testing - 2 hours
  Day 3: Phase 2 (File Watcher) - 4 hours
  
Week 2:
  Day 4-5: Phase 3 (Live Dashboard) - 8 hours
  Day 6: Testing, bug fixes, documentation - 4 hours
  
Week 3 (Optional):
  Day 7: Phase 4 (Analysis) - 6 hours
  Day 8: Phase 5 (Historical) - 6 hours
  Day 9: Polish, community sharing - 2 hours
```

**Total**: 18 hours MVP (Phases 1-3), 30 hours full (Phases 1-5)

## Commit Strategy

1. **Initial commit**: Project structure, README, PLAN.md
2. **Phase 1 commits**: Parser components, tests, benchmarks
3. **Phase 2 commits**: Watcher implementation, integration tests
4. **Phase 3 commits**: Dashboard UI, formatters, alerts
5. **Phase 4 commits**: Analysis features, reports
6. **Phase 5 commits**: Metrics export, viewer, trends

Each phase should be a working, testable unit. No "work in progress" commits to main branch.

## Conclusion

This implementation plan provides a clear path to solving the OpenClaw session memory problem. The phased approach allows for early validation (Phase 1 go/no-go), with each phase delivering incremental value. The technical approach (file watching + Python + terminal UI) is proven, low-risk, and fast to implement. Success criteria are measurable and achievable within the 18-30 hour timeline.

The architecture is extensible for future enhancements while maintaining simplicity for the MVP. With proper error handling and performance targets, the tool will be reliable and lightweight, suitable for always-on monitoring without impacting OpenClaw's performance.
