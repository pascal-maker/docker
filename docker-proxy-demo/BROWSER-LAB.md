# Browser Lab: Demo Requests (No Terminal Needed)

This lab is designed for students to use only a browser.

## Before You Start

Make sure both compose projects are running:
- Main stack (`compose.yaml`)
- External stack (`external-web/compose.yaml`)

Then open this base URL:
- http://localhost:8080

## Part 1 — Main App Through Proxy + Load Balancer

Open these URLs in your browser:

1. Home page (load-balanced)
   - http://localhost:8080/
   - Refresh 8–10 times and observe changing instance names/colors.

2. Load-balanced API endpoint
   - http://localhost:8080/webapp-api
   - Refresh a few times and observe `instance` / `hostname` changes.

## Part 2 — Reverse Proxy to Private Service

3. Private API through proxy (allowed)
   - http://localhost:8080/internal-api/data
   - Expected: JSON response from `internal-api`.

4. Private API direct from host (blocked)
   - http://localhost:5000/data
   - Expected: browser connection error / unreachable.

## Part 3 — Separate Compose Project (External Network Demo)

5. Separate project via proxy
   - http://localhost:8080/external-project/info
   - Expected: JSON from `External-Web` with proxy headers.

6. Same service direct (published host port)
   - http://localhost:5050/info
   - Expected: JSON from the same `External-Web` service.

## Part 4 — Compare Proxy vs Direct Access

Open both tabs side-by-side:
- Proxied: http://localhost:8080/external-project/info
- Direct:  http://localhost:5050/info

What to compare:
- `proxy_headers` values (present on proxied path)
- Same service identity (`service`, `hostname`)
- Different access path (`:8080` via nginx vs `:5050` direct)

## Part 5 — Quick Explainers Endpoints

7. Proxy role summary
   - http://localhost:8080/proxy-info

8. Proxy vs load balancer summary
   - http://localhost:8080/proxy-vs-lb

## Student Questions

- Which URLs are only possible through the proxy?
- Which URL demonstrates direct access to a service?
- Which endpoints are load-balanced?
- Why does `http://localhost:5000/data` fail while `http://localhost:8080/internal-api/data` works?
