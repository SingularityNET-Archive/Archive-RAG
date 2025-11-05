# Discord Bot Testing Examples

This guide provides comprehensive testing examples for all three Discord bot commands.

## Prerequisites

- Bot is running and online in Discord
- Bot has been invited to your server
- RAG index is available at `indexes/meetings.faiss` (or configured path)
- Entity data is available in `entities/` directory (for topics/people commands)

## Quick Reference: Available Commands

| Command | Access Level | Description |
|---------|-------------|-------------|
| `/archive query` | Public | Ask natural language questions about archived meetings |
| `/archive topics` | Contributor+ | Search for topics/tags in archived meetings |
| `/archive people` | Contributor+ | Search for people/participants in archived meetings |

---

## 1. Testing `/archive query` Command (Public Access)

### Basic Query Examples

**General Questions:**
```
/archive query query:"What is this archive about?"
/archive query query:"What decisions were made last January?"
/archive query query:"What is the tag taxonomy?"
/archive query query:"Tell me about recent meetings"
```

**Workgroup-Specific Queries:**
```
/archive query query:"What meetings discussed the Archives Workgroup?"
/archive query query:"What decisions were made in the Governance workgroup?"
/archive query query:"Show me information about the Education workgroup"
/archive query query:"What happened in the African Guild meetings?"
```

**Decision-Related Queries:**
```
/archive query query:"What decisions were made about budget allocation?"
/archive query query:"What decisions affected other people?"
/archive query query:"List all decisions made this year"
```

**Document-Related Queries:**
```
/archive query query:"What documents were discussed in meetings?"
/archive query query:"List all working documents for meetings"
/archive query query:"What documents are linked to the Archives workgroup?"
```

**Action Item Queries:**
```
/archive query query:"What action items were assigned?"
/archive query query:"What action items are still pending?"
/archive query query:"Who has action items assigned to them?"
```

### Expected Responses

**Successful Query Response:**
```
Processing your query...

[Answer text with relevant information about the query]

Citations:
[meeting_id_1 | 2025-01-08 | Archives Workgroup]
[meeting_id_2 | 2025-02-15 | Governance Workgroup]
[meeting_id_3 | 2025-03-20 | Education Workgroup]
```

**No Results Response:**
```
Processing your query...

No relevant archive data found. Try rephrasing your question or check the archive index.
```

**Rate Limit Response:**
```
Rate limit exceeded. Please wait 45s.
```

### Testing Scenarios

#### Test 1: Basic Functionality
1. Type: `/archive query query:"What is this archive about?"`
2. **Expected**: Bot responds with "Processing your query..." then provides answer with citations
3. **Verify**: Citations are formatted as `[meeting_id | date | workgroup_name]`

#### Test 2: Specific Workgroup Query
1. Type: `/archive query query:"What decisions were made in the Archives Workgroup?"`
2. **Expected**: Bot returns relevant decisions from Archives meetings
3. **Verify**: Citations reference Archives Workgroup meetings

#### Test 3: Date-Based Query
1. Type: `/archive query query:"What happened in meetings last January?"`
2. **Expected**: Bot returns meetings from January with dates in citations
3. **Verify**: Date format in citations matches ISO format

#### Test 4: No Results Query
1. Type: `/archive query query:"xyzabc123nonexistentquery"`
2. **Expected**: Bot responds with "No relevant archive data found..."
3. **Verify**: User-friendly error message is displayed

#### Test 5: Rate Limiting
1. Send 10 queries rapidly (within 1 minute)
2. **Expected**: First 10 queries succeed
3. **Expected**: 11th query returns "Rate limit exceeded. Please wait Xs."
4. Wait 60 seconds
5. **Expected**: Query works again

---

## 2. Testing `/archive topics` Command (Contributor+ Access)

### Prerequisites for Testing
- Your Discord user must have a role named "contributor" or "admin" (case-insensitive)
- If you don't have the role, you'll get: "This command requires contributor role. Contact an admin if you need access."

### Topic Search Examples

**General Topics:**
```
/archive topics topic:"RAG ethics"
/archive topics topic:"governance"
/archive topics topic:"budget"
/archive topics topic:"collaboration"
/archive topics topic:"education"
```

**Specific Topic Searches:**
```
/archive topics topic:"ambassador program"
/archive topics topic:"meeting documentation"
/archive topics topic:"decision making"
/archive topics topic:"workgroup management"
```

**Tag-Based Searches:**
```
/archive topics topic:"African Guild"
/archive topics topic:"Archives"
/archive topics topic:"Governance"
```

### Expected Responses

**Successful Topic Search:**
```
Processing your topic search...

Topic: RAG ethics

References:
1. [meeting_id_1 | 2025-01-08 | Archives Workgroup]
2. [meeting_id_2 | 2025-02-15 | Governance Workgroup]
3. [meeting_id_3 | 2025-03-20 | Archives Workgroup]
4. [meeting_id_4 | 2025-04-10 | Education Workgroup]
5. [meeting_id_5 | 2025-05-05 | Archives Workgroup]

(Showing top 5 results)
```

**No Topics Found:**
```
Processing your topic search...

No topics found matching 'xyzabc123'. Try a different search term.
```

**Permission Denied (Public User):**
```
Processing your topic search...

This command requires contributor role. Contact an admin if you need access.
```

### Testing Scenarios

#### Test 1: Basic Topic Search
1. Type: `/archive topics topic:"governance"`
2. **Expected**: Bot responds with "Processing your topic search..." then lists top 5 meetings
3. **Verify**: Citations are formatted correctly
4. **Verify**: Results are limited to top 5 with indicator message

#### Test 2: Case-Insensitive Search
1. Type: `/archive topics topic:"GOVERNANCE"`
2. **Expected**: Same results as lowercase "governance"
3. **Verify**: Case-insensitive matching works

#### Test 3: Partial Match
1. Type: `/archive topics topic:"govern"`
2. **Expected**: Returns results matching "governance", "government", etc.
3. **Verify**: Partial string matching works

#### Test 4: No Results
1. Type: `/archive topics topic:"nonexistenttopic123"`
2. **Expected**: "No topics found matching 'nonexistenttopic123'. Try a different search term."
3. **Verify**: User-friendly error message

#### Test 5: Permission Check (Public User)
1. Ensure your Discord user does NOT have "contributor" or "admin" role
2. Type: `/archive topics topic:"governance"`
3. **Expected**: Permission denied message
4. **Verify**: Public users cannot access contributor commands

---

## 3. Testing `/archive people` Command (Contributor+ Access)

### Prerequisites for Testing
- Your Discord user must have a role named "contributor" or "admin" (case-insensitive)
- Entity data must include people entities in `entities/people/` directory

### People Search Examples

**Search by Display Name:**
```
/archive people person:"André"
/archive people person:"Stephen"
/archive people person:"CallyFromAuron"
/archive people person:"Gorga"
```

**Search by Partial Name:**
```
/archive people person:"Steph"
/archive people person:"And"
/archive people person:"Cal"
```

**Search by Alias:**
```
/archive people person:"QADAO"
/archive people person:"alice"
```

### Expected Responses

**Successful People Search:**
```
Processing your people search...

Person: Stephen
Alias: QADAO
Role: host

Mentions:
1. [meeting_id_1 | 2025-01-08 | Archives Workgroup]
2. [meeting_id_2 | 2025-02-15 | Governance Workgroup]
3. [meeting_id_3 | 2025-03-20 | Archives Workgroup]
4. [meeting_id_4 | 2025-04-10 | Education Workgroup]
5. [meeting_id_5 | 2025-05-05 | Archives Workgroup]

(Showing top 5 results)
```

**Person with Minimal Info:**
```
Processing your people search...

Person: André

Mentions:
1. [meeting_id_1 | 2025-01-08 | Archives Workgroup]
2. [meeting_id_2 | 2025-02-15 | Governance Workgroup]

(Showing top 5 results)
```

**No Person Found:**
```
Processing your people search...

No person found matching 'xyzabc123'. Try a different search term.
```

**Permission Denied (Public User):**
```
Processing your people search...

This command requires contributor role. Contact an admin if you need access.
```

### Testing Scenarios

#### Test 1: Basic People Search
1. Type: `/archive people person:"Stephen"`
2. **Expected**: Bot responds with person info (name, alias if available, role if available)
3. **Expected**: Lists up to 5 meetings where person participated
4. **Verify**: Citations are formatted correctly

#### Test 2: Case-Insensitive Search
1. Type: `/archive people person:"stephen"`
2. **Expected**: Same results as "Stephen"
3. **Verify**: Case-insensitive matching works

#### Test 3: Partial Name Match
1. Type: `/archive people person:"Steph"`
2. **Expected**: Returns results for people with "Steph" in name (e.g., "Stephen")
3. **Verify**: Partial matching works

#### Test 4: Search by Alias
1. Type: `/archive people person:"QADAO"`
2. **Expected**: Returns person whose alias is "QADAO"
3. **Verify**: Alias search works

#### Test 5: No Results
1. Type: `/archive people person:"nonexistentperson123"`
2. **Expected**: "No person found matching 'nonexistentperson123'. Try a different search term."
3. **Verify**: User-friendly error message

#### Test 6: Person with No Meetings
1. Type: `/archive people person:"[person with no meetings]"`
2. **Expected**: Person info displayed but "No meetings found for this person."
3. **Verify**: Handles edge case gracefully

---

## 4. Comprehensive Test Scenarios

### Scenario 1: End-to-End User Journey

**As a Public User:**
1. ✅ Test `/archive query` - Should work
2. ❌ Test `/archive topics` - Should get permission denied
3. ❌ Test `/archive people` - Should get permission denied

**As a Contributor:**
1. ✅ Test `/archive query` - Should work
2. ✅ Test `/archive topics` - Should work
3. ✅ Test `/archive people` - Should work

**As an Admin:**
1. ✅ Test `/archive query` - Should work
2. ✅ Test `/archive topics` - Should work
3. ✅ Test `/archive people` - Should work

### Scenario 2: Rate Limiting Across Commands

1. Send 5 `/archive query` commands
2. Send 5 `/archive topics` commands (as contributor)
3. **Expected**: All 10 succeed
4. Send 1 more `/archive query` command
5. **Expected**: Rate limit exceeded (10 queries/minute limit applies across all commands)

### Scenario 3: Error Handling

**Test Invalid Queries:**
```
/archive query query:""
/archive topics topic:""
/archive people person:""
```

**Expected**: Bot should handle empty strings gracefully (may vary based on Discord validation)

**Test Special Characters:**
```
/archive query query:"What's the status? (with parens)"
/archive topics topic:"R&D topics"
/archive people person:"O'Brien"
```

**Expected**: Bot should handle special characters correctly

### Scenario 4: Response Formatting

**Verify all responses include:**
- ✅ Immediate acknowledgment ("Processing...")
- ✅ Properly formatted citations: `[meeting_id | date | workgroup_name]`
- ✅ Clear error messages when applicable
- ✅ Rate limit messages with remaining time
- ✅ Permission denied messages with helpful guidance

---

## 5. Role Configuration for Testing

### Setting Up Roles in Discord

1. **Go to Server Settings** → **Roles**
2. **Create a role named "contributor"** (or "admin")
3. **Assign the role to your test user**
4. **Verify role name is lowercase** (bot checks lowercase role names)

### Role Names to Test

The bot checks for these role names (case-insensitive):
- `contributor` - Grants access to `/archive topics` and `/archive people`
- `admin` - Grants access to all commands (same as contributor for now)

### Testing Role Changes

1. Assign "contributor" role to your user
2. Test `/archive topics` - Should work
3. Remove "contributor" role
4. Test `/archive topics` - Should get permission denied
5. Re-add "contributor" role
6. Test `/archive topics` - Should work again

**Note**: Discord may cache role information briefly. If role changes don't take effect immediately, wait a few seconds and try again.

---

## 6. Monitoring and Verification

### Check Bot Logs

While testing, monitor your bot's terminal output:

**Success Indicators:**
```
[INFO] bot_ready: bot_user=YourBotName#1234 guild_count=1
[INFO] bot_commands_synced: synced_count=3
[INFO] query_command_executed: user_id=123456 query_id=uuid-123
[INFO] topics_command_executed: user_id=123456 topic=governance meeting_count=5
[INFO] people_command_executed: user_id=123456 person=Stephen meeting_count=8
```

**Error Indicators:**
```
[WARNING] topics_permission_denied: user_id=123456 username=testuser
[WARNING] topics_rate_limit_exceeded: user_id=123456 remaining_seconds=45
[ERROR] topics_search_failed: user_id=123456 topic=governance error=...
```

### Verify Audit Logging

Check that commands are being logged:
- Queries should appear in audit logs
- Topics and people searches should be logged
- Execution times should be recorded

---

## 7. Troubleshooting Common Issues

### Issue: Commands Not Appearing

**Symptoms**: Typing `/` in Discord doesn't show `/archive` commands

**Solutions**:
1. Wait up to 1 hour for Discord to sync commands globally
2. Re-invite bot with OAuth2 URL including `applications.commands` scope
3. Check bot logs for "bot_commands_synced" message
4. Restart bot if needed

### Issue: Permission Denied When You Have Role

**Symptoms**: Getting permission denied even though you have "contributor" role

**Solutions**:
1. Verify role name is exactly "contributor" or "admin" (case-insensitive)
2. Check that bot has "Server Members Intent" enabled (required to read roles)
3. Re-invite bot with correct intents
4. Wait a few seconds for Discord to sync role information

### Issue: "No topics found" or "No person found"

**Symptoms**: Commands work but return no results

**Solutions**:
1. Verify entity data exists in `entities/` directory
2. Check that topics/people data was ingested correctly
3. Try different search terms
4. Check bot logs for specific errors

### Issue: Rate Limit Errors During Testing

**Symptoms**: Getting rate limit errors frequently

**Solutions**:
1. This is normal behavior - 10 queries/minute limit
2. Wait 60 seconds between test batches
3. Consider temporarily increasing rate limit for testing (edit `.env`)

---

## 8. Quick Test Checklist

Use this checklist to verify all functionality:

### Public User Tests
- [ ] `/archive query` command appears in Discord
- [ ] `/archive query` returns results with citations
- [ ] `/archive topics` shows permission denied
- [ ] `/archive people` shows permission denied
- [ ] Rate limiting works (11th query gets rate limit error)
- [ ] Error messages are user-friendly

### Contributor User Tests
- [ ] `/archive query` works (public command)
- [ ] `/archive topics` works and returns results
- [ ] `/archive people` works and returns results
- [ ] All commands show proper citations
- [ ] Rate limiting applies across all commands
- [ ] Permission checks work correctly

### General Tests
- [ ] Bot responds with "Processing..." acknowledgment
- [ ] Responses are formatted correctly
- [ ] Citations include meeting_id, date, workgroup_name
- [ ] Bot logs show successful execution
- [ ] Error scenarios are handled gracefully
- [ ] Commands sync within 1 hour

---

## 9. Example Test Session

Here's a complete example test session:

```
[You have contributor role]

You: /archive query query:"What is this archive about?"
Bot: Processing your query...
Bot: [Answer about the archive system]

Citations:
[meeting_001 | 2025-01-08 | Archives Workgroup]
[meeting_002 | 2025-02-15 | Governance Workgroup]

---

You: /archive topics topic:"governance"
Bot: Processing your topic search...
Bot: 
Topic: governance

References:
1. [meeting_002 | 2025-02-15 | Governance Workgroup]
2. [meeting_005 | 2025-03-10 | Governance Workgroup]
3. [meeting_008 | 2025-04-20 | Governance Workgroup]
4. [meeting_012 | 2025-05-05 | Governance Workgroup]
5. [meeting_015 | 2025-06-15 | Governance Workgroup]

(Showing top 5 results)

---

You: /archive people person:"Stephen"
Bot: Processing your people search...
Bot:
Person: Stephen
Alias: QADAO
Role: host

Mentions:
1. [meeting_001 | 2025-01-08 | Archives Workgroup]
2. [meeting_003 | 2025-02-20 | Archives Workgroup]
3. [meeting_007 | 2025-04-10 | Archives Workgroup]
4. [meeting_010 | 2025-05-20 | Archives Workgroup]
5. [meeting_014 | 2025-06-25 | Archives Workgroup]

(Showing top 5 results)

---

[Send 10 more queries rapidly]

You: /archive query query:"Test query 11"
Bot: Rate limit exceeded. Please wait 45s.
```

---

## 10. Next Steps After Testing

Once basic functionality is verified:

1. **Test with real data**: Use your actual meeting archive data
2. **Monitor performance**: Check response times in logs
3. **Test edge cases**: Very long queries, special characters, etc.
4. **Verify audit logs**: Ensure all queries are being logged
5. **Test with multiple users**: Verify rate limiting works per-user
6. **Test role changes**: Verify permission checks update correctly

---

## Support

If you encounter issues:
- Check bot logs for detailed error messages
- Review [Discord Bot Setup Guide](./discord-bot-setup.md)
- Check [Troubleshooting Section](./discord-bot-setup.md#troubleshooting)
- Verify all prerequisites are met
- Check [Discord Bot Checklist](./discord-bot-checklist.md)

