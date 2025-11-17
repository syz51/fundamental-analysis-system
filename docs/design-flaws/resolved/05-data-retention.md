# Flaw #5: Data Retention Policy Conflict

**Status**: UNRESOLVED ⚠️
**Priority**: Medium
**Impact**: Patterns persist without supporting evidence after retention expiry

---

## 5. Data Retention Policy Conflict

### Problem Description

**Current State**: Patterns stored permanently but underlying evidence deleted after retention period, preventing pattern re-validation or investigation.

From merged v2.0:

**Traditional Data Retention**:

- Raw data: 5 years
- Processed data: 3 years

**Memory Data Retention**:

- Central Knowledge Graph: Permanent
- Patterns: Permanent with decay scoring

### The Conflict

```text
Timeline Example:

2020: Analyze Company XYZ
  - Raw SEC filings stored
  - Financial statements processed
  - Pattern discovered: "SaaS margin expansion in growth phase"
  - Pattern based on XYZ + 4 other companies (2015-2020 data)

2023: Re-validate pattern
  - Need 2015-2020 raw data to verify original analysis
  - Raw data available (within 5yr retention)
  - Pattern still valid ✓

2025: Pattern starts failing
  - Need to investigate why pattern broke
  - Want to review original 2015-2020 data
  - Data deleted! (beyond 5yr retention)
  - Cannot verify if pattern was originally valid
  - Cannot determine what changed

2026: Pattern completely invalid
  - Want to understand root cause
  - All original evidence gone
  - Pattern metadata says "SaaS margin expansion"
  - But cannot audit original analysis
  - Cannot learn from mistake
```

### Specific Issues

**Pattern Orphaning**:

- Pattern exists in knowledge graph
- Supporting evidence deleted
- Cannot re-validate pattern
- Cannot investigate pattern failure
- Cannot teach new agents why pattern existed

**Audit Trail Broken**:

```python
# Pattern stored permanently
{
  "pattern_id": "SAAS_MARGIN_EXPANSION_2020",
  "learned_from": ["XYZ_2020", "ABC_2019", "DEF_2018", ...],
  "evidence_refs": [
    "file://data/raw/sec_filings/XYZ_10K_2020.pdf",  # ← Deleted in 2025
    "file://data/processed/financial_statements/ABC_2019.json"  # ← Deleted in 2022
  ]
}
```

When pattern fails in 2025:

- Want to review original SEC filings
- Files deleted
- Want to review processed financials
- Files deleted
- Pattern is zombie knowledge - no source of truth

**Regulatory/Compliance Risk**:

- Investment decisions based on patterns
- Auditor asks: "Why did you recommend XYZ?"
- Answer: "Pattern SAAS_MARGIN_EXPANSION_2020"
- Auditor: "Show me the evidence"
- Evidence deleted
- Cannot justify historical decisions

### Impact Assessment

| Issue                       | Risk Level | Impact                                               |
| --------------------------- | ---------- | ---------------------------------------------------- |
| Cannot re-validate patterns | High       | Trust in patterns degraded over time                 |
| Cannot investigate failures | Critical   | Unable to learn from mistakes                        |
| Audit trail broken          | Critical   | Regulatory/compliance exposure                       |
| Orphaned patterns           | Medium     | Knowledge graph cluttered with unverifiable patterns |
| Cannot train new agents     | Medium     | Historical knowledge lost                            |

### Recommended Solution

#### Option 1: Pattern-Aware Retention (Recommended)

```python
class PatternAwareRetention:
    """Extend retention for data supporting active patterns"""

    def __init__(self):
        self.base_raw_retention_years = 5
        self.base_processed_retention_years = 3
        self.pattern_evidence_retention_years = 15  # Much longer

    def should_retain_file(self, file_path, current_date):
        """Determine if file should be kept beyond normal retention"""

        # Normal retention check
        file_age = self.get_file_age(file_path, current_date)

        if file_path.startswith('/data/raw/'):
            base_retention = self.base_raw_retention_years
        elif file_path.startswith('/data/processed/'):
            base_retention = self.base_processed_retention_years
        else:
            base_retention = 1  # Default

        # If within base retention, keep
        if file_age < base_retention:
            return True

        # Check if file supports active patterns
        supporting_patterns = self.kb.get_patterns_referencing_file(file_path)

        if len(supporting_patterns) > 0:
            # Check if any patterns are still active
            active_patterns = [p for p in supporting_patterns if p.status == 'active']

            if len(active_patterns) > 0:
                # Keep for pattern evidence retention period
                if file_age < self.pattern_evidence_retention_years:
                    self.log_retention_extension(
                        file_path,
                        reason='supports_active_patterns',
                        patterns=active_patterns
                    )
                    return True

        # Otherwise, safe to delete
        return False

    def archive_pattern_evidence(self, pattern):
        """When pattern created, archive its supporting evidence"""

        evidence_files = pattern.get_evidence_files()

        # Create pattern-specific archive
        archive_path = f"/data/memory/pattern_archives/{pattern.id}/"

        for file_path in evidence_files:
            # Copy to pattern archive (immutable)
            archived_path = self.copy_to_archive(file_path, archive_path)

            # Update pattern to reference archive
            pattern.add_archive_reference(file_path, archived_path)

        self.kb.update_pattern(pattern)

        # Mark files for extended retention
        for file_path in evidence_files:
            self.mark_for_extended_retention(
                file_path,
                reason=f"supports_pattern_{pattern.id}",
                extend_years=self.pattern_evidence_retention_years
            )
```

**Storage Structure**:

```text
/data/memory/pattern_archives/
├── SAAS_MARGIN_EXPANSION_2020/
│   ├── evidence/
│   │   ├── XYZ_10K_2020.pdf
│   │   ├── ABC_10K_2019.pdf
│   │   ├── DEF_10K_2018.pdf
│   ├── processed_data/
│   │   ├── XYZ_financials_2020.json
│   │   ├── ABC_financials_2019.json
│   ├── analysis_snapshots/
│   │   ├── XYZ_analysis_2020.json
│   ├── metadata.json
│   └── pattern_definition.yaml
```

#### Option 2: Summarization with Evidence Trails

```python
class EvidenceSummarization:
    """Summarize data before deletion, keep summaries permanently"""

    def prepare_for_deletion(self, file_path):
        """Before deleting old data, create summary"""

        # Check if file supports any patterns
        patterns = self.kb.get_patterns_referencing_file(file_path)

        if len(patterns) > 0:
            # Create detailed summary
            summary = self.create_evidence_summary(file_path, patterns)

            # Store summary permanently
            summary_path = file_path.replace('/data/raw/', '/data/memory/evidence_summaries/')
            summary_path = summary_path.replace('/data/processed/', '/data/memory/evidence_summaries/')

            self.store_summary(summary, summary_path)

            # Update pattern references
            for pattern in patterns:
                pattern.replace_file_reference(
                    old=file_path,
                    new=summary_path,
                    reference_type='summary'
                )
                self.kb.update_pattern(pattern)

    def create_evidence_summary(self, file_path, patterns):
        """Create comprehensive summary of file content"""

        # Load file
        content = self.load_file(file_path)

        summary = {
            'original_file': file_path,
            'file_type': self.detect_file_type(file_path),
            'date': self.extract_date(content),
            'company': self.extract_company(content),
            'key_metrics': self.extract_metrics(content),
            'pattern_relevance': []
        }

        # For each pattern, document why this file was relevant
        for pattern in patterns:
            relevance = {
                'pattern_id': pattern.id,
                'pattern_name': pattern.name,
                'relevant_sections': self.extract_relevant_sections(content, pattern),
                'key_data_points': self.extract_key_data(content, pattern),
                'why_relevant': pattern.get_file_relevance_reason(file_path)
            }
            summary['pattern_relevance'].append(relevance)

        # Add full-text excerpt (compressed)
        summary['excerpts'] = self.create_smart_excerpts(content, patterns)

        return summary
```

#### Option 3: Tiered Storage (Cost-Effective)

```python
class TieredStorageStrategy:
    """Move old data to cheaper storage instead of deleting"""

    STORAGE_TIERS = {
        'hot': {  # Fast access, expensive
            'retention_years': 2,
            'cost_per_gb_month': 0.023,
            'access_time_ms': 10
        },
        'warm': {  # Slower access, medium cost
            'retention_years': 5,
            'cost_per_gb_month': 0.010,
            'access_time_ms': 100
        },
        'cold': {  # Archive, cheap, slow
            'retention_years': 15,
            'cost_per_gb_month': 0.001,
            'access_time_ms': 3000
        }
    }

    def tier_data_lifecycle(self, file_path):
        """Move data through storage tiers over time"""

        file_age = self.get_file_age(file_path)
        current_tier = self.get_current_tier(file_path)

        # Determine appropriate tier
        if file_age < 2:
            target_tier = 'hot'
        elif file_age < 5:
            target_tier = 'warm'
        else:
            # Check if needed for patterns
            if self.kb.file_supports_active_patterns(file_path):
                target_tier = 'cold'  # Archive, don't delete
            else:
                target_tier = 'delete'

        # Migrate if needed
        if target_tier != current_tier and target_tier != 'delete':
            self.migrate_to_tier(file_path, target_tier)
        elif target_tier == 'delete':
            # Final check: create summary before deleting
            self.evidence_summarization.prepare_for_deletion(file_path)
            self.delete_file(file_path)

    def migrate_to_tier(self, file_path, target_tier):
        """Move file to different storage tier"""

        # Cloud storage example
        if target_tier == 'hot':
            storage_class = 'STANDARD'  # AWS S3, GCP Standard
        elif target_tier == 'warm':
            storage_class = 'STANDARD_IA'  # AWS S3 Infrequent Access
        elif target_tier == 'cold':
            storage_class = 'GLACIER'  # AWS Glacier, GCP Archive

        # Migrate
        self.cloud_storage.migrate(
            file_path,
            storage_class=storage_class
        )

        # Update metadata
        self.update_file_metadata(
            file_path,
            tier=target_tier,
            migrated_date=now()
        )
```

### Recommended Implementation

**Hybrid Approach**: Combine all three options

1. **Pattern Archive** (Option 1):

   - Archive complete evidence when pattern created
   - Keep archived evidence for 15 years

2. **Summarization** (Option 2):

   - Before any deletion, create summary
   - Store summaries permanently

3. **Tiered Storage** (Option 3):
   - Move data to cheaper storage instead of deleting
   - Hot → Warm → Cold → Summarize & Delete

**Storage Cost Estimate**:

```text
Assumptions:
- 1000 stocks analyzed per year
- Avg 50MB raw data per analysis
- 50GB/year new data

Year 1-2 (Hot): 100GB × $0.023 = $2.30/month
Year 3-5 (Warm): 150GB × $0.010 = $1.50/month
Year 6-15 (Cold): 500GB × $0.001 = $0.50/month

Total: ~$4.30/month for 750GB historical data
vs. losing pattern validation capability: Priceless
```

### Updated Data Storage Architecture

```text
/data
├── /raw (Hot: 0-2yr, Warm: 2-5yr, Cold: 5-15yr)
│   ├── /sec_filings
│   ├── /transcripts
│   ├── /market_data
│   └── /news_articles
├── /processed (Hot: 0-1yr, Warm: 1-3yr, Cold: 3-10yr)
│   ├── /financial_statements
│   ├── /ratios
│   ├── /sentiment_scores
│   └── /peer_comparisons
├── /memory
│   ├── /pattern_archives (Permanent)
│   │   ├── /{pattern_id}/
│   │   │   ├── /evidence
│   │   │   ├── /processed_data
│   │   │   └── metadata.json
│   ├── /evidence_summaries (Permanent)
│   │   ├── /{year}/{company}/
│   └── /knowledge_graph (Permanent)
```

---
