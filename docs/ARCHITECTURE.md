# Architecture

## System Overview

```
Session JSONL Files → File Watcher → Incremental Parser → Live Dashboard
     (source)          (inotify)      (extract tokens)     (terminal UI)
```

## Components

### 1. Session Manager
- Reads `sessions.json` to discover active sessions
- Filters out archived sessions (`.reset`, `.deleted`)
- Returns metadata: sessionId, label, agent, updatedAt

### 2. JSONL Parser
- Incremental parsing: track file position, read only new lines
- Extract per-message data: timestamp, role, usage.totalTokens
- Handle malformed lines gracefully (skip, log warning)

### 3. File Watcher
- Event-driven monitoring with `watchdog` library
- Monitor directory: `~/.openclaw-primary/agents/*/sessions/*.jsonl`
- Emit events: SessionCreated, MessageAdded, SessionUpdated
- Fallback to polling if inotify unavailable

### 4. Token Aggregator
- Sum tokens per session (lifetime total)
- Calculate context window % (tokens / 200K)
- Break down by role: user, assistant, tool

### 5. Dashboard
- Terminal UI with `rich.live.Live`
- Three panels: Summary, Session Table, Message Stream
- Auto-refresh every 1 second
- Keyboard controls: q=quit, r=refresh, c=clear

### 6. Alert System
- Warning threshold: 80% (160K tokens)
- Critical threshold: 90% (180K tokens)
- Spike detection: >10K tokens single message
- Rapid growth: >50K tokens in 5 minutes

## Data Flow

1. **Startup**: Read `sessions.json`, build initial session list
2. **Watch**: Start file watcher on session directory
3. **Event**: File modified → read new lines → parse messages → update tokens
4. **Display**: Render dashboard with current state (every 1s)
5. **Alert**: Check thresholds → highlight warnings in UI

## Performance Considerations

- **Memory**: <30MB target (no full session caching)
- **CPU**: <2% target (event-driven, not polling)
- **I/O**: Incremental reads only (not full file rereads)
- **Latency**: <1s event detection to display update

## Error Handling

- **File access errors**: Skip file, log warning, continue monitoring
- **Malformed JSONL**: Skip line, log warning, continue parsing
- **Watchdog failures**: Fallback to polling mode (5s interval)
- **Version mismatches**: Detect, warn, work with available fields

## Extensibility

Future enhancements can add:
- Web UI (Flask/FastAPI backend, React frontend)
- Notifications (Slack, Discord webhooks)
- ML prediction (when session will hit limit)
- OpenClaw plugin integration (show token % in prompt)
