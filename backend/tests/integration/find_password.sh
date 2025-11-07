#!/bin/bash
for pwd in password testpass testpass123 test123 password123; do
  echo "Trying: $pwd"
  RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"testuser@example.com\",\"password\":\"$pwd\"}")
  SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('success', False))" 2>/dev/null || echo "False")
  if [ "$SUCCESS" = "True" ]; then
    echo "SUCCESS! Password is: $pwd"
    exit 0
  fi
done
echo "None of the common passwords worked"
