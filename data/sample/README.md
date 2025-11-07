# Sample Data Directory

## Official Sample Data Source

This directory previously contained local sample files for testing. **All sample data is now sourced from the official SingularityNET Archive GitHub repository:**

**URL**: `https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`

## Usage

To index sample data, use the GitHub URL directly:

```bash
archive-rag index "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/sample-meetings.faiss --no-redact-pii
```

This URL contains:
- **120+ meetings** from various workgroups
- Archives Workgroup format
- Multiple workgroups (Archives, Governance, Education, African Guild, etc.)
- Regularly updated with new meeting summaries

See [../README.md](../README.md) for more details.







