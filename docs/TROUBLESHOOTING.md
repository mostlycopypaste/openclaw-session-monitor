# Troubleshooting

## Common Issues

### Dashboard not updating

**Symptoms**: Dashboard shows no sessions or doesn't update when messages sent

**Diagnosis**:
```bash
# Check OpenClaw is running
openclaw gateway health

# Verify session files exist
ls ~/.openclaw-primary/agents/main/sessions/

# Check for active sessions
cat ~/.openclaw-primary/agents/main/sessions/sessions.json
```

**Solutions**:
- Ensure OpenClaw gateway is running
- Verify state directory path is correct
- Try `--state-dir` flag to override path

### Permission denied errors

**Symptoms**: Error message "Cannot read session files"

**Diagnosis**:
```bash
ls -la ~/.openclaw-primary/agents/main/sessions/
```

**Solutions**:
- Ensure user has read permission on session files
- Don't run as different user than OpenClaw
- Check if external volume is mounted (if using symlinks)

### Can't find sessions

**Symptoms**: "No sessions found"

**Diagnosis**:
```bash
# Find actual state directory
openclaw config get state

# Check if symlinked
ls -la ~/.openclaw
```

**Solutions**:
```bash
# Override state directory
session-monitor watch --state-dir /path/to/.openclaw-primary

# Or set environment variable
export OPENCLAW_STATE_DIR=/path/to/.openclaw-primary
```

### High CPU usage

**Symptoms**: `session-monitor` using >5% CPU

**Diagnosis**:
```bash
# Check number of sessions
ls ~/.openclaw-primary/agents/*/sessions/*.jsonl | wc -l

# Check session file sizes
du -sh ~/.openclaw-primary/agents/*/sessions/*.jsonl
```

**Solutions**:
- Reduce refresh rate: `--refresh-rate 2` (update every 2 seconds)
- Monitor specific agent only: `--agent main`
- Archive old sessions (manually move `.jsonl` files to backup)

### Watchdog not working

**Symptoms**: Events delayed by 5+ seconds, or "inotify limit reached" error

**Diagnosis**:
```bash
# Check inotify limits (Linux)
cat /proc/sys/fs/inotify/max_user_watches
```

**Solutions**:
```bash
# Increase inotify limit (Linux)
sudo sysctl fs.inotify.max_user_watches=524288

# Or use polling mode
# (automatically enabled if watchdog fails)
```

### Dashboard garbled over SSH

**Symptoms**: Colors/formatting broken in terminal

**Solutions**:
```bash
# Use simple mode
session-monitor watch --simple

# Or check terminal type
echo $TERM  # Should be xterm-256color or similar
```

### Version mismatch errors

**Symptoms**: "JSONL format not recognized" or missing fields

**Diagnosis**:
```bash
openclaw --version
```

**Solutions**:
- Upgrade OpenClaw to 2026.4.0+
- Check PLAN.md for supported versions
- Report issue if format changed unexpectedly

## Getting Help

1. Check logs: `~/.openclaw-primary/logs/monitor.log`
2. Enable debug mode: `session-monitor watch --debug` (future feature)
3. Report issues: https://github.com/user/openclaw-session-monitor/issues

Include:
- OpenClaw version (`openclaw --version`)
- Python version (`python3 --version`)
- OS and version
- Error messages and logs
