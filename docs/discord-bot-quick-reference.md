# Discord Bot Quick Reference

Quick reference card for Archive-RAG Discord bot commands.

## Commands

### `/archive query` (Public)
**Access**: Everyone  
**Purpose**: Ask natural language questions about archived meetings

**Examples:**
```
/archive query query:"What decisions were made last January?"
/archive query query:"What is the tag taxonomy?"
/archive query query:"What meetings discussed budget allocation?"
```

**Response Format:**
```
Processing your query...

[Answer text]

Citations:
[meeting_id | date | workgroup_name]
```

---

### `/archive topics` (Contributor+)
**Access**: Users with "contributor" or "admin" role  
**Purpose**: Search for topics/tags in archived meetings

**Examples:**
```
/archive topics topic:"RAG ethics"
/archive topics topic:"governance"
/archive topics topic:"budget"
```

**Response Format:**
```
Processing your topic search...

Topic: governance

References:
1. [meeting_id | date | workgroup_name]
2. [meeting_id | date | workgroup_name]
...
(Showing top 5 results)
```

---

### `/archive people` (Contributor+)
**Access**: Users with "contributor" or "admin" role  
**Purpose**: Search for people/participants in archived meetings

**Examples:**
```
/archive people person:"Stephen"
/archive people person:"Gorga"
/archive people person:"André"
```

**Response Format:**
```
Processing your people search...

Person: Stephen
Alias: QADAO
Role: host

Mentions:
1. [meeting_id | date | workgroup_name]
2. [meeting_id | date | workgroup_name]
...
(Showing top 5 results)
```

---

## Rate Limiting

- **Limit**: 10 queries per minute per user
- **Applies to**: All commands (shared limit)
- **Message**: "Rate limit exceeded. Please wait Xs."

---

## Error Messages

| Error | Message | Cause |
|-------|---------|-------|
| Rate Limit | "Rate limit exceeded. Please wait Xs." | Too many queries (10/minute limit) |
| Permission Denied | "This command requires contributor role. Contact an admin if you need access." | User doesn't have contributor/admin role |
| No Results | "No relevant archive data found..." | Query didn't match any content |
| Service Unavailable | "RAG service temporarily unavailable..." | Index file not found or inaccessible |

---

## Role Setup

### To Test Contributor Commands:
1. Go to **Server Settings** → **Roles**
2. Create role named **"contributor"** (or **"admin"**)
3. Assign role to your user
4. Bot checks role names case-insensitively

---

## Quick Test Checklist

- [ ] Bot appears online (green status)
- [ ] `/archive query` works
- [ ] `/archive topics` works (with contributor role)
- [ ] `/archive people` works (with contributor role)
- [ ] Rate limiting works (11th query gets error)
- [ ] Error messages are clear and helpful

---

## Troubleshooting

**Commands not appearing?**
- Wait up to 1 hour for Discord to sync
- Re-invite bot with OAuth2 URL

**Permission denied with role?**
- Verify role name is "contributor" or "admin"
- Check bot has "Server Members Intent" enabled
- Wait a few seconds for Discord to sync roles

**No results?**
- Try different search terms
- Check entity data exists in `entities/` directory
- Verify RAG index is available

---

## Full Documentation

- [Testing Guide](./discord-bot-testing.md) - Basic testing instructions
- [Testing Examples](./discord-bot-testing-examples.md) - Comprehensive test scenarios
- [Setup Guide](./discord-bot-setup.md) - Bot setup and configuration
- [Checklist](./discord-bot-checklist.md) - Setup checklist

