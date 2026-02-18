from app import app
import sys

print("Verifying app routes...")
rules = [str(p) for p in app.url_map.iter_rules()]
required_routes = ['/', '/detection', '/animation', '/video_feed', '/api/grok-key']

missing = []
for route in required_routes:
    if route not in rules:
        missing.append(route)

if missing:
    print(f"❌ Missing routes: {missing}")
    sys.exit(1)
else:
    print("✅ All required routes are present.")
    print(f"Total routes: {len(rules)}")
    sys.exit(0)
