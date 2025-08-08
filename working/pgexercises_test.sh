#!/bin/bash

echo "🔍 Testing connectivity to pg.pgexercises.com"
echo "============================================="

# Test DNS resolution
echo "1. Testing DNS resolution..."
if nslookup pg.pgexercises.com > /dev/null 2>&1; then
    echo "✅ DNS resolution successful"
    IP=$(nslookup pg.pgexercises.com | awk '/^Address: / { print $2 }' | tail -1)
    echo "   IP Address: $IP"
else
    echo "❌ DNS resolution failed"
    echo "   Trying with different DNS servers..."
    
    # Try with Google DNS
    echo "   Testing with Google DNS (8.8.8.8)..."
    if nslookup pg.pgexercises.com 8.8.8.8 > /dev/null 2>&1; then
        echo "✅ DNS works with Google DNS"
    else
        echo "❌ DNS still fails with Google DNS"
    fi
fi

# Test ping
echo ""
echo "2. Testing ping connectivity..."
if ping -c 3 pg.pgexercises.com > /dev/null 2>&1; then
    echo "✅ Ping successful"
else
    echo "❌ Ping failed"
fi

# Test port connectivity
echo ""
echo "3. Testing PostgreSQL port (5432)..."
if timeout 10 bash -c "</dev/tcp/pg.pgexercises.com/5432" > /dev/null 2>&1; then
    echo "✅ Port 5432 is reachable"
else
    echo "❌ Port 5432 is not reachable"
fi

# Test with telnet if available
echo ""
echo "4. Testing with telnet (if available)..."
if command -v telnet &> /dev/null; then
    timeout 5 telnet pg.pgexercises.com 5432 2>&1 | head -3
else
    echo "   telnet not available"
fi

# Check current DNS configuration
echo ""
echo "5. Current DNS configuration:"
if [ -f /etc/resolv.conf ]; then
    echo "   DNS servers:"
    grep nameserver /etc/resolv.conf
else
    echo "   Could not read /etc/resolv.conf"
fi

# Test with direct PostgreSQL connection
echo ""
echo "6. Testing direct PostgreSQL connection..."
if command -v psql &> /dev/null; then
    echo "   Attempting psql connection..."
    timeout 10 psql -h pg.pgexercises.com -U demo -d pagila -c "SELECT 1;" 2>&1 | head -3
else
    echo "   psql not available for testing"
fi

echo ""
echo "📋 Summary:"
echo "If DNS resolution fails, try:"
echo "1. sudo systemctl restart systemd-resolved"
echo "2. Change DNS to 8.8.8.8: echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf"
echo "3. Check firewall: sudo ufw status"
echo "4. Check if you're behind a proxy/corporate firewall"