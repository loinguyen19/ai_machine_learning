.PHONY: provision-app
provision-app:
	@ python3 -m venv venv && source venv/bin/activate
	@ pip install fastapi uvicorn anthropic gTTS moviepy matplotlib pillow pytest httpx python-dotenv

.PHONY: run-app
run-app:
	@ bash demo_script.sh
