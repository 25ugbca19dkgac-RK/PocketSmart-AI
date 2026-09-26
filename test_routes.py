from fastapi.testclient import TestClient
from main import app
c = TestClient(app)

# Test pages
pages = ['/', '/login', '/register']
for p in pages:
    r = c.get(p)
    print(f'{p}: {r.status_code}')

# Test protected pages redirect
protected = ['/dashboard', '/home-planner', '/party-planner', '/jewelry-planner', '/history']
for p in protected:
    r = c.get(p, follow_redirects=False)
    loc = r.headers.get("location", "")
    print(f'{p}: {r.status_code} -> {loc}')

# Test register
r = c.post('/register', data={'username': 'testuser', 'email': 'test@test.com', 'password': 'test123'}, follow_redirects=False)
print(f'Register: {r.status_code}')

# Test login
r = c.post('/login', data={'username': 'testuser', 'password': 'test123'}, follow_redirects=False)
cookie_set = "access_token" in str(r.cookies)
print(f'Login: {r.status_code}, cookie set: {cookie_set}')

# Access protected page with cookie
if cookie_set:
    cookies = dict(r.cookies)
    r2 = c.get('/dashboard', cookies=cookies)
    print(f'Dashboard (authed): {r2.status_code}')
    r3 = c.get('/home-planner', cookies=cookies)
    print(f'Home Planner (authed): {r3.status_code}')

print("All tests passed!")
