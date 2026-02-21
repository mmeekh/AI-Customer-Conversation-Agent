# Email-Automation-with-AI
An entirely autonomous email tracking and answering engine. It uses the Gmail API and the latest Google Gemini AI to analyze incoming emails, extract visible text by safely ignoring historical email quotes, and securely manage conversation histories with SQLite. Finally, it constructs a fully HTML-enabled email format featuring an inline transparent PNG signature, making sure the replies look authentic without appearing repetitive or machine-generated.

### Features
* **Auto-Respond via Gmail API** automatically marks unread emails.
* **Smart Parsing**: Uses `email-reply-parser` and custom regex rules to strip away quote threads and prevent the AI agent from getting distracted by old context.
* **Inline Image Signature**: Attaches a flawless, transparent PNG as an inline CID attachment to complete an authentic-looking professional email.
* **Context Control**: SQLite integration to keep track of AI conversations to ensure precise answers.
* **Rate Limits Guarantee**: Bounded by 120-150 words inside System Prompt rules allowing large operations within Google’s Free Tier token quota without triggering limitations.
