# Kroolo_assignment

Build a comprehensive AI-powered workflow automation platform that intelligently processes user requests and automates communications across multiple channels. Here's what it is : 

Core System Built:

1. FastAPI Backend ( ask_anything_fastapi.py ) - Main server with AI request processing, smart action detection, and entity extraction
2. Beautiful Web Interface ( ask_anything_ai_interface.html ) - Modern HTML/CSS/JS frontend with real-time previews and examples
3. Gmail Integration ( gmail_service.py ) - Automated email composition and sending via Pipedream API
4. Slack Integration ( slack_service.py ) - Smart message generation with channel routing and formatting
5. Telegram Integration ( telegram_service.py ) - Community message generation with bot integration
6. Calendar Service ( calendar_service.py ) - Google Calendar event creation and scheduling
7. Pipedream Connector ( PipedreamConnector.py ) - OAuth authentication and API proxy for 2,700+ integrations
8. AI Workflow Engine - Intelligent message parsing, date extraction, priority detection, and dynamic content generation
9. Multi-Service Preview System - Real-time message previews for Email, Slack, Telegram, and Calendar before sending
10. Complete Documentation - Setup guides, API documentation, and integration examples for seamless deployment
Tools Used: FastAPI, HTML5/CSS3/JavaScript, Pipedream Connect API, OAuth 2.0, Gmail API, Slack API, Telegram Bot API, Google Calendar API, Python regex patterns, and advanced AI text processing algorithms.

<b>STEPS TO RUN THE PROJECT </b>
1. Create a python virtual environment and install requirements.txt
2. Set your environment variables
    - GEMINI_API_KEY
    - GMAIL TOKEN
    - SLACK BOT TOKEN
    - PIPEDREAM API KEY
3. Run the server:
`uvicorn ask_anything_fastapi:app --reload`
