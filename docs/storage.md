# Storage Guide

PromptBeacon uses DuckDB for local-first historical data storage. This guide covers setup, usage, and advanced storage patterns.

## Why DuckDB?

DuckDB provides:

- **Local-First**: All data stays on your machine
- **No Setup**: Embedded database, no server required
- **Fast**: Optimized for analytical queries
- **Single File**: Easy to backup and share
- **SQL Support**: Query your data with standard SQL
- **Zero Cost**: No cloud storage fees

## Quick Start

### Enable Storage

```python
from promptbeacon import Beacon

beacon = (
    Beacon("Nike")
    .with_storage("~/.promptbeacon/nike.db")
)

# This scan will be automatically saved
report = beacon.scan()
```

### Default Storage Location

If not specified, PromptBeacon uses:

```
~/.promptbeacon/data.db
```

### CLI Usage

```bash
# Enable storage
promptbeacon scan "Nike" --storage ~/.promptbeacon/nike.db

# Uses default location
promptbeacon scan "Nike" --storage ~/.promptbeacon/data.db
```

---

## Storage Basics

### First Scan with Storage

```python
from promptbeacon import Beacon

beacon = Beacon("Nike").with_storage("./nike.db")

# Run scan - automatically saved to database
report = beacon.scan()

print(f"Scan saved at: {report.timestamp}")
```

### Retrieving History

```python
# Get 30 days of history
history = beacon.get_history(days=30)

print(f"Trend: {history.trend_direction}")  # up, down, stable
print(f"Average score: {history.average_score:.1f}")
print(f"Data points: {len(history.data_points)}")
```

### Comparing Scans

```python
# Run multiple scans over time
beacon = Beacon("Nike").with_storage("./nike.db")

# First scan
report1 = beacon.scan()

# ... time passes ...

# Second scan
report2 = beacon.scan()

# Compare with previous
comparison = beacon.compare_with_previous()
if comparison:
    print(f"Score change: {comparison.score_change:+.1f}")
    print(f"Direction: {comparison.change_direction}")
```

---

## Data Schema

### Tables

PromptBeacon creates these tables automatically:

#### `scans`

Stores complete scan reports.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| brand | TEXT | Brand name |
| visibility_score | REAL | Score (0-100) |
| mention_count | INTEGER | Total mentions |
| timestamp | TIMESTAMP | Scan time |
| scan_duration | REAL | Duration (seconds) |
| total_cost | REAL | Cost (USD) |
| data | JSON | Full report data |

#### `provider_results`

Stores individual provider query results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| scan_id | INTEGER | Foreign key to scans |
| provider | TEXT | Provider name |
| model | TEXT | Model used |
| prompt | TEXT | Prompt sent |
| response | TEXT | Response received |
| latency_ms | REAL | Latency |
| cost_usd | REAL | Cost |
| timestamp | TIMESTAMP | Query time |

#### `mentions`

Stores individual brand mentions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| result_id | INTEGER | Foreign key to provider_results |
| brand_name | TEXT | Brand mentioned |
| sentiment | TEXT | positive/neutral/negative |
| position | INTEGER | Position in response |
| context | TEXT | Surrounding text |
| confidence | REAL | Confidence (0-1) |
| is_recommendation | BOOLEAN | Explicitly recommended |

---

## Historical Analysis

### Trend Detection

```python
history = beacon.get_history(days=30)

if history.trend_direction == "up":
    print("✓ Visibility improving")
elif history.trend_direction == "down":
    print("✗ Visibility declining")
else:
    print("→ Visibility stable")

# Volatility indicates consistency
print(f"Volatility: {history.volatility:.2f}")
```

### Time-Based Analysis

```python
history = beacon.get_history(days=90)

# Extract scores over time
scores = [dp.visibility_score for dp in history.data_points]
dates = [dp.timestamp for dp in history.data_points]

# Plot with matplotlib
import matplotlib.pyplot as plt

plt.plot(dates, scores)
plt.xlabel("Date")
plt.ylabel("Visibility Score")
plt.title(f"{beacon.brand} Visibility Trend")
plt.show()
```

### Statistical Analysis

```python
history = beacon.get_history(days=30)

import statistics

scores = [dp.visibility_score for dp in history.data_points]

print(f"Mean: {statistics.mean(scores):.1f}")
print(f"Median: {statistics.median(scores):.1f}")
print(f"Std Dev: {statistics.stdev(scores):.2f}")
print(f"Min: {min(scores):.1f}")
print(f"Max: {max(scores):.1f}")
```

---

## Multi-Brand Tracking

### Single Database for Multiple Brands

```python
from promptbeacon import Beacon

# Use same database for all brands
db_path = "~/.promptbeacon/brands.db"

brands = ["Nike", "Adidas", "Puma"]

for brand in brands:
    beacon = Beacon(brand).with_storage(db_path)
    report = beacon.scan()
    print(f"{brand}: {report.visibility_score:.1f}")
```

### Brand Comparison Across Time

```python
def compare_brands(brands: list[str], days: int = 30):
    """Compare multiple brands over time."""
    db_path = "~/.promptbeacon/brands.db"

    for brand in brands:
        beacon = Beacon(brand).with_storage(db_path)
        history = beacon.get_history(days)

        print(f"\n{brand}:")
        print(f"  Average: {history.average_score:.1f}")
        print(f"  Trend: {history.trend_direction}")
        print(f"  Volatility: {history.volatility:.2f}")

compare_brands(["Nike", "Adidas", "Puma"])
```

---

## Advanced Queries

### Direct SQL Access

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Raw SQL queries
query = """
    SELECT
        brand,
        DATE(timestamp) as date,
        AVG(visibility_score) as avg_score,
        COUNT(*) as scan_count
    FROM scans
    WHERE timestamp >= datetime('now', '-30 days')
    GROUP BY brand, DATE(timestamp)
    ORDER BY date
"""

results = db.connection.execute(query).fetchall()

for row in results:
    print(f"{row[1]}: {row[2]:.1f} ({row[3]} scans)")
```

### Custom Analytics

#### Weekly Averages

```python
query = """
    SELECT
        strftime('%Y-W%W', timestamp) as week,
        AVG(visibility_score) as avg_score,
        MIN(visibility_score) as min_score,
        MAX(visibility_score) as max_score
    FROM scans
    WHERE brand = ?
    GROUP BY week
    ORDER BY week DESC
    LIMIT 12
"""

results = db.connection.execute(query, ["Nike"]).fetchall()

for week, avg, min_score, max_score in results:
    print(f"{week}: {avg:.1f} (range: {min_score:.1f}-{max_score:.1f})")
```

#### Sentiment Trends

```python
query = """
    SELECT
        DATE(timestamp) as date,
        sentiment,
        COUNT(*) as count
    FROM mentions m
    JOIN provider_results pr ON m.result_id = pr.id
    JOIN scans s ON pr.scan_id = s.id
    WHERE s.brand = ?
        AND timestamp >= datetime('now', '-30 days')
    GROUP BY date, sentiment
    ORDER BY date
"""

results = db.connection.execute(query, ["Nike"]).fetchall()
```

#### Provider Performance

```python
query = """
    SELECT
        provider,
        COUNT(*) as total_queries,
        AVG(latency_ms) as avg_latency,
        SUM(CASE WHEN error IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
    FROM provider_results pr
    JOIN scans s ON pr.scan_id = s.id
    WHERE s.brand = ?
        AND s.timestamp >= datetime('now', '-30 days')
    GROUP BY provider
"""

results = db.connection.execute(query, ["Nike"]).fetchall()

for provider, total, latency, success_rate in results:
    print(f"{provider}:")
    print(f"  Queries: {total}")
    print(f"  Avg Latency: {latency:.0f}ms")
    print(f"  Success Rate: {success_rate:.1f}%")
```

---

## Data Export

### Export to CSV

```python
from promptbeacon.storage.database import Database
import csv

db = Database("~/.promptbeacon/nike.db")

query = """
    SELECT
        timestamp,
        brand,
        visibility_score,
        mention_count
    FROM scans
    ORDER BY timestamp DESC
"""

results = db.connection.execute(query).fetchall()

with open("history.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "brand", "visibility_score", "mention_count"])
    writer.writerows(results)
```

### Export to pandas

```python
import pandas as pd
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Load scans into DataFrame
df_scans = pd.read_sql("SELECT * FROM scans", db.connection)

# Load mentions into DataFrame
df_mentions = pd.read_sql("SELECT * FROM mentions", db.connection)

# Analysis with pandas
print(df_scans.groupby("brand")["visibility_score"].agg(["mean", "std"]))
```

### Export to JSON

```python
import json
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

query = "SELECT * FROM scans ORDER BY timestamp DESC LIMIT 10"
results = db.connection.execute(query).fetchdf()

results.to_json("scans.json", orient="records", date_format="iso")
```

---

## Backup and Restore

### Manual Backup

DuckDB databases are single files - just copy them:

```bash
# Backup
cp ~/.promptbeacon/nike.db ~/.promptbeacon/backups/nike_$(date +%Y%m%d).db

# Restore
cp ~/.promptbeacon/backups/nike_20260116.db ~/.promptbeacon/nike.db
```

### Automated Backup Script

```python
import shutil
from datetime import datetime
from pathlib import Path

def backup_database(db_path: str, backup_dir: str = "~/.promptbeacon/backups"):
    """Backup PromptBeacon database."""
    db_path = Path(db_path).expanduser()
    backup_dir = Path(backup_dir).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{db_path.stem}_{timestamp}.db"
    backup_path = backup_dir / backup_name

    shutil.copy2(db_path, backup_path)
    print(f"Backed up to: {backup_path}")

    return backup_path

# Usage
backup_database("~/.promptbeacon/nike.db")
```

### Backup Rotation

```python
from pathlib import Path
import time

def rotate_backups(backup_dir: str = "~/.promptbeacon/backups", keep_days: int = 30):
    """Remove backups older than keep_days."""
    backup_dir = Path(backup_dir).expanduser()
    cutoff_time = time.time() - (keep_days * 86400)

    for backup_file in backup_dir.glob("*.db"):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            print(f"Removed old backup: {backup_file.name}")

# Run after backup
backup_database("~/.promptbeacon/nike.db")
rotate_backups(keep_days=30)
```

---

## Data Retention

### Delete Old Scans

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Delete scans older than 90 days
query = """
    DELETE FROM scans
    WHERE timestamp < datetime('now', '-90 days')
"""

deleted = db.connection.execute(query).fetchall()
print(f"Deleted {deleted} old scans")

# Vacuum to reclaim space
db.connection.execute("VACUUM")
```

### Archive Old Data

```python
from promptbeacon.storage.database import Database

# Create archive database
archive_db = Database("~/.promptbeacon/archive_2025.db")
current_db = Database("~/.promptbeacon/nike.db")

# Copy old scans to archive
query = """
    INSERT INTO archive_db.scans
    SELECT * FROM current_db.scans
    WHERE timestamp < datetime('2026-01-01')
"""

# Then delete from current
current_db.connection.execute("""
    DELETE FROM scans
    WHERE timestamp < datetime('2026-01-01')
""")
```

---

## Database Maintenance

### Check Database Size

```bash
# Linux/Mac
du -h ~/.promptbeacon/nike.db

# Or in Python
from pathlib import Path

db_path = Path("~/.promptbeacon/nike.db").expanduser()
size_mb = db_path.stat().st_size / (1024 * 1024)
print(f"Database size: {size_mb:.2f} MB")
```

### Optimize Database

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Analyze tables for query optimization
db.connection.execute("ANALYZE")

# Reclaim unused space
db.connection.execute("VACUUM")

print("Database optimized")
```

### Check Database Integrity

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

result = db.connection.execute("PRAGMA integrity_check").fetchone()
print(f"Integrity: {result[0]}")  # Should be "ok"
```

---

## Performance Optimization

### Indexing

PromptBeacon creates necessary indexes automatically. To verify:

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

indexes = db.connection.execute("""
    SELECT name, sql
    FROM sqlite_master
    WHERE type = 'index'
""").fetchall()

for name, sql in indexes:
    print(f"{name}: {sql}")
```

### Query Performance

```python
from promptbeacon.storage.database import Database
import time

db = Database("~/.promptbeacon/nike.db")

query = """
    SELECT
        brand,
        AVG(visibility_score) as avg_score
    FROM scans
    WHERE timestamp >= datetime('now', '-30 days')
    GROUP BY brand
"""

start = time.time()
results = db.connection.execute(query).fetchall()
duration = time.time() - start

print(f"Query took {duration*1000:.2f}ms")
```

---

## Migration Guide

### Migrating from Older Versions

If database schema changes between versions:

```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Check current schema version
version = db.connection.execute(
    "SELECT value FROM metadata WHERE key = 'schema_version'"
).fetchone()

print(f"Schema version: {version}")

# PromptBeacon handles migrations automatically on first connection
```

### Merging Databases

```python
from promptbeacon.storage.database import Database

# Attach second database
db1 = Database("~/.promptbeacon/nike.db")
db1.connection.execute("ATTACH DATABASE '~/.promptbeacon/old_nike.db' AS old")

# Copy scans
db1.connection.execute("""
    INSERT INTO scans
    SELECT * FROM old.scans
    WHERE id NOT IN (SELECT id FROM scans)
""")

db1.connection.execute("DETACH DATABASE old")
print("Databases merged")
```

---

## Monitoring and Alerts

### Automated Monitoring Script

```python
from promptbeacon import Beacon
from datetime import datetime

def monitor_brand(brand: str, alert_threshold: float = 5.0):
    """Monitor brand and alert on significant changes."""
    beacon = Beacon(brand).with_storage("~/.promptbeacon/data.db")

    # Run scan
    report = beacon.scan()

    # Check for significant changes
    comparison = beacon.compare_with_previous()

    if comparison and abs(comparison.score_change) > alert_threshold:
        send_alert(
            brand=brand,
            current=comparison.current_score,
            previous=comparison.previous_score,
            change=comparison.score_change
        )

def send_alert(brand: str, current: float, previous: float, change: float):
    """Send alert (email, slack, etc.)"""
    message = f"""
    Brand Visibility Alert: {brand}

    Current Score: {current:.1f}
    Previous Score: {previous:.1f}
    Change: {change:+.1f} points

    Time: {datetime.now()}
    """
    print(message)
    # Add email/Slack integration here

# Run daily
monitor_brand("Nike", alert_threshold=5.0)
```

---

## Troubleshooting

### Database Locked

**Problem:** `database is locked` error

**Solution:**
```python
# Ensure you close connections
with Beacon("Nike").with_storage("nike.db") as beacon:
    report = beacon.scan()
# Connection automatically closed

# Or manually close
beacon = Beacon("Nike").with_storage("nike.db")
report = beacon.scan()
beacon.close()
```

### Corrupted Database

**Problem:** Database appears corrupted

**Solution:**
```python
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")

# Check integrity
result = db.connection.execute("PRAGMA integrity_check").fetchone()

if result[0] != "ok":
    print("Database corrupted. Restore from backup.")
    # Restore from backup
else:
    print("Database is healthy")
```

### Disk Space

**Problem:** Running out of disk space

**Solution:**
```python
# 1. Delete old data
from promptbeacon.storage.database import Database

db = Database("~/.promptbeacon/nike.db")
db.connection.execute("DELETE FROM scans WHERE timestamp < datetime('now', '-90 days')")
db.connection.execute("VACUUM")

# 2. Archive to separate database
# (see Data Retention section)

# 3. Export and delete
# Export to CSV, then clear database
```

---

## Best Practices

### Storage Location

**Recommended:**
```python
# User home directory
beacon = Beacon("Nike").with_storage("~/.promptbeacon/nike.db")

# Project-specific
beacon = Beacon("Nike").with_storage("./data/nike.db")
```

**Not recommended:**
```python
# Temporary directory (may be cleared)
beacon = Beacon("Nike").with_storage("/tmp/nike.db")

# System directories (permission issues)
beacon = Beacon("Nike").with_storage("/var/lib/nike.db")
```

### Naming Conventions

```python
# Per-brand databases
"~/.promptbeacon/nike.db"
"~/.promptbeacon/adidas.db"

# Centralized database
"~/.promptbeacon/brands.db"

# Environment-specific
"~/.promptbeacon/production.db"
"~/.promptbeacon/staging.db"
```

### Regular Maintenance

```python
from promptbeacon.storage.database import Database
from datetime import datetime

def weekly_maintenance(db_path: str):
    """Weekly database maintenance."""
    db = Database(db_path)

    print(f"Maintenance started: {datetime.now()}")

    # 1. Backup
    backup_database(db_path)

    # 2. Optimize
    db.connection.execute("ANALYZE")
    db.connection.execute("VACUUM")

    # 3. Check integrity
    result = db.connection.execute("PRAGMA integrity_check").fetchone()
    print(f"Integrity: {result[0]}")

    # 4. Cleanup old data (optional)
    db.connection.execute("DELETE FROM scans WHERE timestamp < datetime('now', '-90 days')")

    print(f"Maintenance completed: {datetime.now()}")

# Run weekly
weekly_maintenance("~/.promptbeacon/nike.db")
```

---

## See Also

- [API Reference](api-reference.md) - Database-related API
- [Advanced Usage](advanced.md) - Advanced analytics patterns
- [Examples](examples.md) - Real-world storage examples
- [CLI Reference](cli.md) - CLI storage options
