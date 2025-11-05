# Discord Bot Performance Monitoring

## Overview

The Discord bot includes built-in performance monitoring to track query execution times and ensure compliance with success criteria (SC-001: 95% of queries respond < 3 seconds).

## Performance Metrics

### Execution Time Tracking

All commands log execution time with the following metrics:

- `execution_time_ms` - Execution time in milliseconds
- `execution_time_seconds` - Execution time in seconds (rounded to 2 decimal places)
- `performance_status` - Either "within_target" (< 3 seconds) or "exceeded_target" (>= 3 seconds)

### Success Criteria

**SC-001**: 95% of valid queries respond < 3 seconds

The bot tracks performance status for each query and logs warnings when queries exceed the 3-second target.

## Logged Metrics

### Query Command (`/archive query`)

**Success Log:**
```json
{
  "event": "query_command_executed",
  "user_id": "123456789",
  "username": "user123",
  "query_id": "uuid-123",
  "execution_time_ms": 2500,
  "execution_time_seconds": 2.5,
  "performance_status": "within_target",
  "evidence_found": true,
  "citation_count": 3
}
```

**Performance Warning:**
```json
{
  "event": "query_performance_exceeded_target",
  "query_id": "uuid-123",
  "execution_time_seconds": 4.2,
  "target_seconds": 3.0
}
```

### Topics Command (`/archive topics`)

**Success Log:**
```json
{
  "event": "topics_command_executed",
  "user_id": "123456789",
  "username": "user123",
  "topic": "governance",
  "meeting_count": 5,
  "execution_time_ms": 1800,
  "execution_time_seconds": 1.8,
  "performance_status": "within_target",
  "command": "archive topics"
}
```

### People Command (`/archive people`)

**Success Log:**
```json
{
  "event": "people_command_executed",
  "user_id": "123456789",
  "username": "user123",
  "person": "Stephen",
  "person_id": "uuid-456",
  "meeting_count": 8,
  "execution_time_ms": 2200,
  "execution_time_seconds": 2.2,
  "performance_status": "within_target",
  "command": "archive people"
}
```

### List Command (`/archive list`)

**Topics List Log:**
```json
{
  "event": "list_topics_executed",
  "user_id": "123456789",
  "username": "user123",
  "topic_count": 45,
  "execution_time_ms": 1500,
  "execution_time_seconds": 1.5,
  "performance_status": "within_target",
  "command": "archive list"
}
```

**Meetings List Log:**
```json
{
  "event": "list_meetings_executed",
  "user_id": "123456789",
  "username": "user123",
  "meeting_count": 12,
  "year": 2025,
  "month": 3,
  "execution_time_ms": 2800,
  "execution_time_seconds": 2.8,
  "performance_status": "within_target",
  "command": "archive list"
}
```

## Monitoring Performance

### Viewing Performance Logs

**Check all query executions:**
```bash
# Filter for query execution logs
grep "query_command_executed" bot.log | jq '.execution_time_seconds, .performance_status'
```

**Check performance warnings:**
```bash
# Find queries exceeding 3 seconds
grep "performance_exceeded_target" bot.log
```

**Calculate performance percentage:**
```python
# Example script to analyze performance
import json
import sys

within_target = 0
exceeded_target = 0

for line in sys.stdin:
    if 'query_command_executed' in line:
        data = json.loads(line)
        if data.get('performance_status') == 'within_target':
            within_target += 1
        else:
            exceeded_target += 1

total = within_target + exceeded_target
if total > 0:
    percentage = (within_target / total) * 100
    print(f"Performance: {percentage:.1f}% within target (3 seconds)")
    print(f"Within target: {within_target}/{total}")
    print(f"Exceeded target: {exceeded_target}/{total}")
```

### Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| 95% of queries < 3s | 95% | Tracked in logs |
| Average response time | < 2s | Tracked in logs |
| Timeout threshold | 30s | Enforced |

## Performance Optimization

### Common Performance Issues

1. **Large RAG Index**: Very large indexes may slow query processing
   - **Solution**: Use smaller, more focused indexes for faster queries

2. **Complex Queries**: Very complex queries may take longer
   - **Solution**: Query timeout is set to 30 seconds

3. **Entity Lookups**: Multiple entity lookups can add latency
   - **Solution**: Entity queries are cached in memory where possible

4. **Network Latency**: External API calls (if any) add delay
   - **Solution**: All operations are local; no external API dependencies

### Performance Best Practices

1. **Monitor Logs**: Regularly check performance logs for patterns
2. **Index Size**: Keep RAG indexes reasonably sized (< 100MB recommended)
3. **Query Complexity**: Encourage users to ask specific, focused questions
4. **System Resources**: Ensure adequate CPU and memory for bot process

## Bot Operations Logging

### Bot Startup

**Ready Event:**
```json
{
  "event": "bot_ready",
  "bot_user": "ArchiveRAGBot#1234",
  "bot_user_id": "123456789",
  "guild_count": 1,
  "guild_names": ["My Server"],
  "index_name": "indexes/meetings.faiss"
}
```

**Command Sync:**
```json
{
  "event": "bot_commands_synced",
  "synced_count": 4,
  "command_names": ["query", "topics", "people", "list"]
}
```

### Rate Limiter Cleanup

**Cleanup Event (every 5 minutes):**
```json
{
  "event": "rate_limiter_cleanup_completed",
  "entries_before": 15,
  "entries_after": 8,
  "entries_cleaned": 7
}
```

## Analyzing Performance Data

### Extract Performance Metrics

```bash
# Extract all execution times
grep "command_executed" bot.log | \
  jq -r '[.execution_time_seconds, .performance_status, .command // "archive query"] | @csv' \
  > performance_data.csv
```

### Calculate Statistics

```python
import json
import statistics

times = []
with open('bot.log') as f:
    for line in f:
        if 'command_executed' in line:
            data = json.loads(line)
            if 'execution_time_seconds' in data:
                times.append(data['execution_time_seconds'])

if times:
    print(f"Total queries: {len(times)}")
    print(f"Average: {statistics.mean(times):.2f}s")
    print(f"Median: {statistics.median(times):.2f}s")
    print(f"95th percentile: {sorted(times)[int(len(times) * 0.95)]:.2f}s")
    print(f"Max: {max(times):.2f}s")
    print(f"Min: {min(times):.2f}s")
    
    within_target = sum(1 for t in times if t < 3.0)
    percentage = (within_target / len(times)) * 100
    print(f"Within 3s target: {within_target}/{len(times)} ({percentage:.1f}%)")
```

## Performance Alerts

The bot automatically logs warnings when queries exceed the 3-second target:

```
[WARNING] query_performance_exceeded_target: query_id=uuid-123 execution_time_seconds=4.2 target_seconds=3.0
```

Set up log monitoring to alert on:
- Frequent performance warnings
- Average execution time trending upward
- Performance percentage dropping below 95%

## Related Documentation

- [Discord Bot Setup Guide](./discord-bot-setup.md)
- [Discord Bot Testing Guide](./discord-bot-testing.md)
- [Discord Bot Implementation Summary](./discord-bot-implementation-summary.md)

