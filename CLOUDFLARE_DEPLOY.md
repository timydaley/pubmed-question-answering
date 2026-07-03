# Cloudflare Tunnel deployment for family access

Goal: let a trusted family member use the local PubMed QA tool in a browser while
all retrieval and LLM work still runs on this Mac.

Architecture:

```text
Dad's browser
  -> Cloudflare Access login
  -> Cloudflare Tunnel
  -> 127.0.0.1:8000 on this Mac
  -> local PubMed QA web app
```

Do **not** expose the app directly through router port forwarding.

## 1. Run the local web app

Install web dependencies:

```bash
cd /Users/timothydaley/personal_projects/pubmed_question_answering/pubmed-question-answering
./.venv/bin/pip install -r requirements.txt
```

Start the app, bound to localhost only:

```bash
cd /Users/timothydaley/personal_projects/pubmed_question_answering/pubmed-question-answering
PUBMEDQA_DATA="/Volumes/Macintosh HD/Users/timothydaley/Documents/pubmed_qa_full" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
./.venv/bin/python -m uvicorn pubmedqa.web:app \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000
```

Open locally:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/healthz
```

The app handles one answer-generation request at a time and returns HTTP 429 if
another request is already running.

## 2. Install cloudflared

On macOS with Homebrew:

```bash
brew install cloudflare/cloudflare/cloudflared
```

Authenticate with Cloudflare:

```bash
cloudflared tunnel login
```

This opens a browser and lets you pick the Cloudflare zone/domain to use.

## 3. Create a tunnel

Example tunnel name:

```bash
cloudflared tunnel create pubmedqa-mac
```

Note the tunnel UUID printed by Cloudflare.

Create a DNS route for a hostname you control, for example:

```bash
cloudflared tunnel route dns pubmedqa-mac pubmedqa.yourdomain.com
```

## 4. Configure the tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL-UUID-FROM-CREATE-COMMAND>
credentials-file: /Users/timothydaley/.cloudflared/<TUNNEL-UUID-FROM-CREATE-COMMAND>.json

ingress:
  - hostname: pubmedqa.yourdomain.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Test foreground tunnel:

```bash
cloudflared tunnel run pubmedqa-mac
```

Then open:

```text
https://pubmedqa.yourdomain.com
```

## 5. Add Cloudflare Access login

In the Cloudflare dashboard:

1. Go to **Zero Trust**.
2. Go to **Access** -> **Applications**.
3. Add an application.
4. Choose **Self-hosted**.
5. Application domain: `pubmedqa.yourdomain.com`.
6. Add an allow policy for only the intended email address(es), e.g. dad's email.
7. Choose login method, commonly one-time PIN by email or Google login.

After this, visiting `https://pubmedqa.yourdomain.com` should require login before
Cloudflare forwards traffic to the Mac.

## 6. Run the tunnel as a background service

After foreground testing works:

```bash
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

Useful commands:

```bash
sudo launchctl list | grep cloudflared
cloudflared tunnel list
cloudflared tunnel info pubmedqa-mac
```

## 7. Optional GitHub Pages link

GitHub Pages should only be a link/front door. It should not hold secrets or proxy
requests.

Add a link on `timydaley.github.io` such as:

```html
<a href="https://pubmedqa.yourdomain.com">Open PubMed QA</a>
```

Cloudflare Access handles authentication.

## Operational notes

- The Mac must be awake and online.
- Keep the local app bound to `127.0.0.1`, not `0.0.0.0`.
- Do not disable Cloudflare Access on the hostname.
- The app is for evidence lookup/summarization, not medical advice.
- The local model may take 10-30 seconds per answer.
