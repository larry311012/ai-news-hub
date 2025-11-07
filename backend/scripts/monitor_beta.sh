#!/bin/bash
#
# Beta Monitoring Script - AI News Hub
# Purpose: Monitor API health, error rates, and performance during beta testing
# Frequency: Run every hour via cron
# Author: Development Team
# Last Updated: 2025-11-04
#

set -e

# Configuration
BACKEND_URL="http://localhost:8000"
LOG_FILE="/tmp/backend.log"
METRICS_FILE="/tmp/beta_metrics.log"
ALERT_FILE="/tmp/beta_alerts.log"
DB_NAME="ai_news_local"

# Thresholds
ERROR_THRESHOLD=10          # Alert if >10 errors in last hour
RESPONSE_TIME_THRESHOLD=2000  # Alert if avg response time >2s (2000ms)
CRASH_THRESHOLD=5            # Alert if >5 crashes in last hour

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Timestamp for logs
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "====================================="
echo "Beta Monitoring - $TIMESTAMP"
echo "====================================="

#
# 1. Check API Health
#
echo -e "\n${GREEN}[1/7] Checking API Health...${NC}"

health_check() {
    response=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/api/health" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 200 ]; then
        echo "✅ API Health: OK (HTTP $http_code)"
        echo "$TIMESTAMP,api_health,ok,$http_code" >> "$METRICS_FILE"
        return 0
    else
        echo "❌ API Health: FAILED (HTTP $http_code)"
        echo "[$TIMESTAMP] ALERT: API health check failed (HTTP $http_code)" >> "$ALERT_FILE"
        echo "$TIMESTAMP,api_health,failed,$http_code" >> "$METRICS_FILE"
        return 1
    fi
}

health_check || echo -e "${RED}⚠️  API may be down!${NC}"

#
# 2. Check Critical Endpoints
#
echo -e "\n${GREEN}[2/7] Testing Critical Endpoints...${NC}"

test_endpoint() {
    local method=$1
    local path=$2
    local name=$3

    start=$(date +%s%N)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BACKEND_URL$path" 2>/dev/null)
    end=$(date +%s%N)
    duration=$(( ($end - $start) / 1000000 ))  # Convert to milliseconds

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 500 ]; then
        echo "  ✅ $name: HTTP $http_code (${duration}ms)"
        echo "$TIMESTAMP,$name,ok,$http_code,$duration" >> "$METRICS_FILE"

        # Alert if slow
        if [ "$duration" -gt "$RESPONSE_TIME_THRESHOLD" ]; then
            echo "[$TIMESTAMP] WARNING: $name slow (${duration}ms)" >> "$ALERT_FILE"
        fi
    else
        echo "  ❌ $name: HTTP $http_code"
        echo "$TIMESTAMP,$name,error,$http_code,$duration" >> "$METRICS_FILE"
        echo "[$TIMESTAMP] ALERT: $name failed (HTTP $http_code)" >> "$ALERT_FILE"
    fi
}

# Test key endpoints (public ones that don't require auth)
test_endpoint "GET" "/api/health" "Health"
test_endpoint "GET" "/docs" "API Docs"
test_endpoint "POST" "/api/auth/login" "Login Endpoint"

echo "  ℹ️  Note: Auth endpoints expected to return 401/422 without credentials"

#
# 3. Count Recent Errors
#
echo -e "\n${GREEN}[3/7] Analyzing Error Logs...${NC}"

if [ -f "$LOG_FILE" ]; then
    # Count errors in last hour
    one_hour_ago=$(date -u -v-1H '+%Y-%m-%d %H' 2>/dev/null || date -u -d '1 hour ago' '+%Y-%m-%d %H' 2>/dev/null)

    if [ -n "$one_hour_ago" ]; then
        error_count=$(grep -c "ERROR\|CRITICAL" "$LOG_FILE" 2>/dev/null | grep "$one_hour_ago" | wc -l || echo "0")
        error_count=$(echo "$error_count" | tr -d ' ')

        echo "  📊 Errors in last hour: $error_count"
        echo "$TIMESTAMP,error_count,$error_count" >> "$METRICS_FILE"

        if [ "$error_count" -gt "$ERROR_THRESHOLD" ]; then
            echo -e "  ${RED}⚠️  High error rate detected!${NC}"
            echo "[$TIMESTAMP] ALERT: High error rate ($error_count errors in last hour)" >> "$ALERT_FILE"

            # Show recent errors
            echo "  Recent errors:"
            tail -20 "$LOG_FILE" | grep "ERROR\|CRITICAL" | tail -5
        else
            echo "  ✅ Error rate: Normal"
        fi
    else
        echo "  ⚠️  Could not parse date (check date command)"
    fi
else
    echo "  ⚠️  Log file not found: $LOG_FILE"
    echo "  ℹ️  Ensure backend is running and logging to $LOG_FILE"
fi

#
# 4. Check Database Connectivity
#
echo -e "\n${GREEN}[4/7] Checking Database...${NC}"

if command -v psql &> /dev/null; then
    # Check if database is accessible
    if psql -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
        echo "  ✅ Database: Connected"

        # Get basic stats
        user_count=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
        post_count=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts;" 2>/dev/null | tr -d ' ')

        echo "  📊 Users: $user_count"
        echo "  📊 Posts: $post_count"

        echo "$TIMESTAMP,db_connected,yes" >> "$METRICS_FILE"
        echo "$TIMESTAMP,user_count,$user_count" >> "$METRICS_FILE"
        echo "$TIMESTAMP,post_count,$post_count" >> "$METRICS_FILE"

        # Check for slow queries (if pg_stat_statements available)
        slow_queries=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_stat_statements WHERE mean_exec_time > 1000;" 2>/dev/null | tr -d ' ' || echo "N/A")

        if [ "$slow_queries" != "N/A" ] && [ "$slow_queries" -gt 0 ]; then
            echo "  ⚠️  Slow queries detected: $slow_queries"
            echo "[$TIMESTAMP] WARNING: $slow_queries slow queries (>1s)" >> "$ALERT_FILE"
        fi
    else
        echo "  ❌ Database: Connection failed"
        echo "[$TIMESTAMP] ALERT: Database connection failed" >> "$ALERT_FILE"
        echo "$TIMESTAMP,db_connected,no" >> "$METRICS_FILE"
    fi
else
    echo "  ⚠️  psql not found (skipping database checks)"
    echo "  ℹ️  Install PostgreSQL client tools for database monitoring"
fi

#
# 5. Check Disk Space
#
echo -e "\n${GREEN}[5/7] Checking Disk Space...${NC}"

disk_usage=$(df -h /Users/ranhui/ai_post 2>/dev/null | awk 'NR==2 {print $5}' | sed 's/%//')

if [ -n "$disk_usage" ]; then
    echo "  📊 Disk usage: ${disk_usage}%"
    echo "$TIMESTAMP,disk_usage,$disk_usage" >> "$METRICS_FILE"

    if [ "$disk_usage" -gt 90 ]; then
        echo -e "  ${RED}⚠️  Disk space critical!${NC}"
        echo "[$TIMESTAMP] ALERT: Disk usage critical (${disk_usage}%)" >> "$ALERT_FILE"
    elif [ "$disk_usage" -gt 80 ]; then
        echo -e "  ${YELLOW}⚠️  Disk space warning${NC}"
        echo "[$TIMESTAMP] WARNING: Disk usage high (${disk_usage}%)" >> "$ALERT_FILE"
    else
        echo "  ✅ Disk space: OK"
    fi
else
    echo "  ⚠️  Could not check disk usage"
fi

#
# 6. Check Process Status
#
echo -e "\n${GREEN}[6/7] Checking Backend Process...${NC}"

# Check if uvicorn/backend is running
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "  ✅ Backend process: Running"
    echo "$TIMESTAMP,backend_running,yes" >> "$METRICS_FILE"

    # Get process info
    pid=$(pgrep -f "uvicorn main:app" | head -1)
    mem_usage=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{print $1/1024}' || echo "N/A")

    if [ "$mem_usage" != "N/A" ]; then
        echo "  📊 Memory usage: ${mem_usage} MB"
        echo "$TIMESTAMP,backend_memory,$mem_usage" >> "$METRICS_FILE"
    fi
else
    echo "  ❌ Backend process: Not running"
    echo "[$TIMESTAMP] ALERT: Backend process not running" >> "$ALERT_FILE"
    echo "$TIMESTAMP,backend_running,no" >> "$METRICS_FILE"
fi

#
# 7. Performance Summary
#
echo -e "\n${GREEN}[7/7] Performance Summary...${NC}"

if [ -f "$METRICS_FILE" ]; then
    # Calculate average response time from last hour
    avg_response=$(tail -100 "$METRICS_FILE" | grep "Health\|Login" | awk -F',' '{sum+=$5; count++} END {if(count>0) print sum/count; else print "N/A"}')

    if [ "$avg_response" != "N/A" ]; then
        avg_response_int=$(echo "$avg_response" | awk '{print int($1)}')
        echo "  📊 Average API response time: ${avg_response_int}ms"

        if [ "$avg_response_int" -gt "$RESPONSE_TIME_THRESHOLD" ]; then
            echo -e "  ${YELLOW}⚠️  API responses slower than threshold (${RESPONSE_TIME_THRESHOLD}ms)${NC}"
        else
            echo "  ✅ API performance: Good"
        fi
    fi
else
    echo "  ℹ️  No historical metrics available yet"
fi

#
# Summary & Alerts
#
echo -e "\n====================================="
echo "Summary"
echo "====================================="

# Count alerts in last hour
if [ -f "$ALERT_FILE" ]; then
    recent_alerts=$(grep "$TIMESTAMP" "$ALERT_FILE" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$recent_alerts" -gt 0 ]; then
        echo -e "${RED}⚠️  $recent_alerts alerts this hour${NC}"
        echo ""
        echo "Recent alerts:"
        grep "$TIMESTAMP" "$ALERT_FILE" 2>/dev/null | tail -5
    else
        echo -e "${GREEN}✅ No alerts - all systems normal${NC}"
    fi
else
    echo "  ℹ️  No alerts file yet"
fi

echo ""
echo "Metrics logged to: $METRICS_FILE"
echo "Alerts logged to: $ALERT_FILE"
echo "Backend logs: $LOG_FILE"

#
# Optional: Send notifications (email, Slack, etc.)
#
# Uncomment and configure if you want automated alerts
#
# if [ "$recent_alerts" -gt 0 ]; then
#     # Example: Send email alert
#     # echo "Subject: Beta Alert - $recent_alerts issues detected" | mail -s "Beta Alert" your-email@example.com
#
#     # Example: Send Slack notification
#     # curl -X POST -H 'Content-type: application/json' \
#     #   --data '{"text":"Beta Alert: '"$recent_alerts"' issues detected"}' \
#     #   YOUR_SLACK_WEBHOOK_URL
# fi

echo ""
echo "====================================="
echo "Monitoring complete - $(date '+%Y-%m-%d %H:%M:%S')"
echo "====================================="

# Exit with error code if critical alerts
if [ -f "$ALERT_FILE" ] && grep -q "ALERT" "$ALERT_FILE" 2>/dev/null | grep "$TIMESTAMP"; then
    exit 1
else
    exit 0
fi
