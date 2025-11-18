# DD-021: Neo4j High Availability Architecture

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**:

- [Memory System](../architecture/02-memory-system.md#neo4j-high-availability-architecture)
- [Flaw #21: Scalability Architecture](../design-flaws/resolved/21-scalability.md)
- [Tech Requirements](../implementation/02-tech-requirements.md)

**Related Decisions**: DD-005 (Memory Scalability), DD-019 (Data Tier Operations)

---

## Context

### Problem Statement

**Single Point of Failure in Central Knowledge Graph**: The memory system relies on a single Neo4j instance for the central knowledge graph (L3 tier). This creates unacceptable availability risk for production operations:

- **High Downtime Risk**: Single instance availability ~99.4% = ~50 hours annual downtime
- **No Failover**: Server failure blocks entire analysis pipeline until manual recovery
- **Recovery Latency**: Backup restoration requires 2-6 hours, blocking all operations
- **No Read Scaling**: Single instance becomes read bottleneck at high query volumes
- **Data Loss Risk**: Crash during write operations could corrupt graph state

### Concrete Examples

**Example 1: Neo4j Server Crash During Analysis**

```text
Scenario: Neo4j crashes during debate resolution (memory sync in progress)
Current State: All 5 active analyses blocked waiting for L3 memory queries
Human Gate: 3 pending decisions cannot load historical context
Recovery Time: 2-6 hours to restore from backup, validate integrity
Impact: Pipeline fully blocked, 4-8 hour analysis delay
Expected: Automatic failover within 10 seconds, zero data loss
```

**Example 2: Planned Maintenance Window**

```text
Scenario: Apply Neo4j security patch (requires server restart)
Current State: Schedule 2-hour downtime window, pause all analyses
Human Impact: Cannot review pending gates during maintenance
Opportunity Cost: 8+ analyses delayed by 2 hours (16 analysis-hours lost)
Impact: Coordination overhead, reduced throughput
Expected: Rolling restart across cluster, zero downtime
```

**Example 3: Read Query Bottleneck at Scale**

```text
Scenario: 10 concurrent analyses each querying patterns, precedents, history
Current State: 50 parallel read queries to single Neo4j instance
Result: Graph query latency spikes 500ms → 2000ms (p95)
Memory Budget: Violates <500ms uncached retrieval target
Impact: Analysis pipeline slows, human gates delayed
Expected: Read replicas distribute load, maintain <500ms latency
```

**Example 4: Backup Corruption Detection**

```text
Scenario: Weekly backup restore test reveals corruption in previous week
Current State: No redundant backup source, must restore from 2-week-old backup
Data Loss: 2 weeks of analyses, patterns, outcomes (14 stocks worth of work)
Re-Analysis Cost: 14 stocks × 12-day cycle = 168 analysis-days lost
Impact: Significant rework, pattern learning regression
Expected: Cross-region backup redundancy, multiple restore points
```

### Why Address Now

- **Phase 4 Production Requirement**: Cannot launch production with single point of failure
- **Uptime Target**: 99.95% availability required for 24/7 operation (vs 99.4% current)
- **Cost Justified**: $1,600/mo premium saves ~46 hours downtime annually
- **Before Scale**: Easier to deploy HA before production workload (200+ stocks)
- **Risk Mitigation**: Investment decisions require reliable historical context access
- **Regulatory Compliance**: Audit trail accessibility must be guaranteed

---

## Decision

**Deploy Neo4j Causal Clustering with 3 core servers (quorum-based writes) + 2 read replicas (read scaling) in Phase 4 (Months 7-8) before production launch.**

Primary approach uses Raft consensus protocol for automatic leader election and failover (<10s), supplemented by cross-region backups (AWS S3 + GCP Cloud Storage) for disaster recovery, achieving 99.95% availability target.

---

## Options Considered

### Option 1: Single Instance + Enhanced Backups (Status Quo)

**Description**: Keep single Neo4j instance, improve backup frequency to hourly

**Pros**:

- Low cost ($500/mo vs $2,100/mo)
- Simple architecture (no clustering complexity)
- Easy to operate (no cluster management)

**Cons**:

- Still single point of failure (99.4% uptime)
- No automatic failover (2-6hr recovery)
- No read scaling (bottleneck at high load)
- Planned maintenance requires downtime
- Production deployment risk unacceptable

**Estimated Cost**: $500/mo infrastructure + $50/mo backups = $550/mo

---

### Option 2: Active-Passive Failover (Warm Standby)

**Description**: Run primary Neo4j + warm standby replica, manual failover on primary failure

**Pros**:

- Cheaper than full cluster ($1,200/mo: primary + standby)
- Faster recovery than backup restore (~15min manual failover)
- Read replica available for load distribution

**Cons**:

- Manual failover required (human on-call, 15min response)
- Still has downtime window during failover
- No automatic leader election
- Standby lag risk (async replication)
- Doesn't meet 99.95% target (manual failover too slow)

**Estimated Cost**: $1,200/mo (2 nodes) + $100/mo backups = $1,300/mo

---

### Option 3: Neo4j Causal Clustering (3 Core + 2 Replicas) - **CHOSEN**

**Description**: 3 core servers with Raft consensus + 2 read replicas for load distribution

**Pros**:

- Automatic failover (<10s via Raft leader election)
- Zero data loss (quorum writes)
- Read scaling (2× read capacity via replicas)
- No downtime for maintenance (rolling restarts)
- Meets 99.95% availability target
- Production-grade reliability

**Cons**:

- Higher cost ($2,100/mo vs $500/mo single instance)
- Operational complexity (cluster management)
- Write latency +5ms (quorum coordination overhead)

**Estimated Cost**: $2,100/mo (3 cores + 2 replicas) + $150/mo backups = $2,250/mo
**Premium**: $1,700/mo over single instance

---

### Option 4: Sharded Neo4j (Horizontal Partitioning)

**Description**: Partition graph across multiple independent Neo4j instances by domain

**Pros**:

- Horizontal write scaling (not just reads)
- Higher aggregate throughput
- Fault isolation (shard failure doesn't affect others)

**Cons**:

- Very high complexity (cross-shard queries, graph partitioning logic)
- Not needed (read-heavy 80/20 workload, single leader writes sufficient)
- Expensive ($3,000+/mo for 3 shards)
- Over-engineering for current scale
- Implementation effort: 6+ weeks

**Estimated Cost**: $3,000+/mo + significant engineering overhead

**Rejected**: Over-engineered for read-heavy workload, unnecessary complexity

---

## Rationale for Chosen Option

**Option 3 (Causal Clustering) Selected** because:

1. **Automatic Failover**: <10s recovery vs 15min (Option 2) or 2-6hr (Option 1)
2. **Zero Data Loss**: Quorum writes guarantee durability
3. **Read Scaling**: 2× read capacity supports concurrent analysis growth
4. **Production-Ready**: Meets 99.95% availability target required for 24/7 operation
5. **Cost Justified**: $1,700/mo premium saves ~46 hours downtime annually
6. **Right-Sized**: Sufficient for read-heavy workload, simpler than sharding (Option 4)

---

## Implementation Plan

### Phase 4 (Months 7-8) Deployment

**Week 1-2: Cluster Setup**

- Provision infrastructure: 3 × r5.2xlarge (cores), 2 × r5.xlarge (replicas)
- Configure Raft clustering, validate internal communication (ports 6000/7000/7474/7687)
- Set up Application Load Balancer with routing rules (writes → leader, reads → replicas)
- Configure backup pipelines (hourly incremental, daily/weekly/monthly full)

**Week 3: Data Migration (Maintenance Window)**

- Take final full backup of single instance
- Restore to core-1, let Raft replicate to core-2/core-3
- Validate data consistency across cores (checksum verification)
- Configure read replicas to follow core cluster
- Validate replication lag <1 minute

**Week 4: Testing & Cutover**

- Failover testing: Kill core-1, verify 5-10s leader election
- Load testing: Read replica distribution, write quorum latency
- Backup restore testing: Verify hourly/daily backups functional
- DNS cutover: Update application connection strings to load balancer
- 24-hour monitoring period (rollback plan: revert DNS to single instance)

### Rollback Plan

- Keep single instance running (standby) for 7 days post-migration
- If critical issues: Revert DNS to single instance (<5min switchover)
- Cluster data can be exported back to single instance if needed

---

## Architecture Details

### Cluster Topology

```text
┌─────────────────────────────────────────────────────┐
│               Load Balancer                          │
│  Routes: Writes → Core Leader, Reads → Replicas      │
└─────────────────────────────────────────────────────┘
          │                           │
          ▼ (writes)                  ▼ (reads)
┌──────────────────────┐    ┌──────────────────────┐
│   Core Cluster       │    │   Read Replicas      │
│  ┌─────────────┐     │    │  ┌─────────────┐    │
│  │ Core-1      │     │    │  │ Replica-1   │    │
│  │ (Leader)    │◄────┼────┼─►│             │    │
│  └─────────────┘     │    │  └─────────────┘    │
│  ┌─────────────┐     │    │  ┌─────────────┐    │
│  │ Core-2      │     │    │  │ Replica-2   │    │
│  │ (Follower)  │◄────┼────┼─►│             │    │
│  └─────────────┘     │    │  └─────────────┘    │
│  ┌─────────────┐     │    │                      │
│  │ Core-3      │     │    │  Async replication   │
│  │ (Follower)  │     │    │  from core cluster   │
│  └─────────────┘     │    └──────────────────────┘
│                      │
│  Raft consensus      │
│  Quorum writes       │
└──────────────────────┘
```

### Backup Strategy

**Multi-Tier Backup Architecture**:

- **Hourly Incremental**: From core-1, 24-hour retention, ~5min duration
- **Daily Full**: 30-day retention, ~30min duration, S3 Standard cross-region
- **Weekly Full**: 12-week retention, S3 Standard-IA
- **Monthly Full**: 12-month retention, S3 Glacier

**Backup Storage**:

- **Primary**: AWS S3 us-west-2 (cross-region from production us-east-1)
- **Secondary**: GCP Cloud Storage us-central1 (provider-level DR)

**Recovery Objectives**:

- **RTO**: <1 hour (time to restore)
- **RPO**: <1 hour (hourly backup granularity)

### Infrastructure Costs

```yaml
Core Servers (3 nodes):
  Instance: r5.2xlarge (8 vCPU, 64GB RAM, 1TB SSD)
  Cost: $500/mo × 3 = $1,500/mo

Read Replicas (2 nodes):
  Instance: r5.xlarge (4 vCPU, 32GB RAM, 1TB SSD)
  Cost: $300/mo × 2 = $600/mo

Backups:
  S3 Standard (daily/weekly): ~$100/mo
  S3 Glacier (monthly): ~$20/mo
  GCP Cloud Storage (DR): ~$30/mo

Total: $2,250/mo
Premium: $1,700/mo over single instance ($550/mo)
```

---

## Monitoring & Alerts

**Cluster Health Metrics** (Prometheus/Grafana):

| Metric          | Alert Threshold           | Action                        |
| --------------- | ------------------------- | ----------------------------- |
| Core node down  | Any core unreachable >30s | Page on-call                  |
| Leader election | >2 elections/hour         | Investigate network stability |
| Replication lag | >5 minutes or >1000 ops   | Alert ops team                |
| Quorum lost     | <2 cores available        | Critical: Page on-call        |
| Backup failure  | Any backup job fails      | High: Alert ops team          |

**Integration with DD-019**:

- Cluster health checks added to hourly integrity monitoring
- Backup validation added to weekly comprehensive checks
- Replication lag alerts added to real-time alert routing

---

## Performance Characteristics

**Read/Write Latency**:

- **Write Operations**: +5ms overhead (quorum coordination)
  - Single Instance: ~10ms
  - Cluster: ~15ms
- **Read Operations**: No overhead (replica local reads)
  - Both: ~10ms
  - Benefit: 2× read capacity

**Memory Retrieval Impact**:

- Target: <500ms uncached, <200ms cached
- Cluster Overhead: ~5ms per query
- Impact: <1% of budget (acceptable)

**Scaling**:

- Read capacity scales linearly with replicas
- Write capacity fixed (single leader bottleneck)
- Sufficient for read-heavy workload (80/20 read/write ratio)

---

## Testing Requirements

**Failover Testing Scenarios**:

1. **Leader Failure**: Kill core-1, verify 5-10s election, zero data loss
2. **Follower Failure**: Kill core-2, verify writes continue (2/3 quorum)
3. **Network Partition**: Simulate split (2 vs 1), verify majority continues
4. **Replica Lag**: Introduce network delay, verify lag alerts
5. **Backup Restore**: Restore from hourly backup, validate consistency

**Success Criteria**:

- All failover scenarios complete within SLA (10s election, <1hr RTO)
- Zero data loss in all scenarios
- Application connection resilience (automatic retry)
- Monitoring alerts trigger correctly
- Backup validation passes (weekly restore test)

---

## Success Criteria

### Availability Metrics (Phase 4 Post-Deployment)

- ✅ Cluster operational (3 core + 2 replica)
- ✅ Automatic failover <10s (measured during testing)
- ✅ Availability 99.95% (measured over 30 days post-deployment)
- ✅ Backup restoration tested (<1hr RTO)

### Operational Metrics

- ✅ Zero unplanned downtime from Neo4j failures (30-day window)
- ✅ Read query latency <500ms p95 (unchanged from single instance)
- ✅ Write query latency <20ms p95 (+5ms overhead acceptable)
- ✅ Replication lag <5 minutes p95

### Business Impact

- ✅ Production deployment unblocked
- ✅ 24/7 operation enabled (no maintenance windows)
- ✅ Analysis pipeline continuity (no multi-hour outages)
- ✅ Downtime reduction: 50hr → 4hr annually

---

## Risks & Mitigations

**Risk 1: Cluster Configuration Complexity**

- **Mitigation**: Hire Neo4j consultant for initial setup validation (1 week, $10K)
- **Mitigation**: Comprehensive runbooks for cluster operations
- **Mitigation**: Automated cluster health checks (DD-019)

**Risk 2: Cost Overrun ($2,250/mo ongoing)**

- **Mitigation**: Cost justified by downtime reduction (46hr annually)
- **Mitigation**: Budget approved for Phase 4 infrastructure
- **Mitigation**: Consider smaller instances if workload allows (post-Phase 4 optimization)

**Risk 3: Migration Downtime (Week 3 maintenance window)**

- **Mitigation**: Schedule migration during low-usage period
- **Mitigation**: Rollback plan (revert to single instance <5min)
- **Mitigation**: 24-hour monitoring period before full cutover

**Risk 4: Application Compatibility (Connection String Changes)**

- **Mitigation**: Test connection failover logic in staging environment
- **Mitigation**: Update all application components to use load balancer endpoint
- **Mitigation**: Gradual rollout (1 agent at a time, validate before proceeding)

---

## Related Documentation

- [Memory System](../architecture/02-memory-system.md#neo4j-high-availability-architecture) - Full architecture details
- [Flaw #21: Scalability Architecture](../design-flaws/resolved/21-scalability.md) - Problem context
- [DD-019: Data Tier Operations](DD-019_DATA_TIER_OPERATIONS.md) - Integrity monitoring integration
- [Tech Requirements](../implementation/02-tech-requirements.md) - Infrastructure specifications
- [Roadmap Phase 4](../implementation/01-roadmap.md#phase-4-optimization--learning-months-7-8) - Implementation timeline

---

_Last Updated: 2025-11-18_
