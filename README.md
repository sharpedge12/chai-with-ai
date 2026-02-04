# Chai with AI

An automated Python system for creating and distributing daily AI and software news digests with seamless Telegram integration.

---

## 📋 Description

**Chai with AI** is your personal, automated system for creating and distributing daily AI and software news digests. It intelligently curates over 200 articles daily, provides audio summaries for on-the-go listening, and delivers everything in a beautifully clean format directly to your Telegram.

---

## 🚀 Features

-   **🎧 Audio Summaries:** Listen to a summary of your entire news digest, perfect for multitasking and catching up on the go.
-   **📈 Comprehensive Coverage:** Fetches and processes an average of over 200 articles daily, so you get a complete picture of the latest trends.
-   **💡 Intelligent Insights:** Every article comes with a concise summary and a "Why it Matters" section, giving you the key takeaways instantly.
-   **⭐ Rich Engagement Metrics:** See the source, likes, dislikes, comments, and a star-based rating for each article to gauge community sentiment and quality.
-   **🏷️ Smart Tagging:** Save time with relevant tags on every article, helping you to quickly filter and find the news that matters most to you.
-   **✨ Clean & Beautiful Display:** All information is presented in a beautifully designed and clean interface for an exceptional user experience.
-   **⚡ High-Performance Processing:** Engineered for speed and efficiency, using batching, multiprocessing, and other optimizations to deliver your digest faster.
-   **🤖 AI-Powered:** Leverages LLM capabilities for intelligent content processing, summarization, and tagging.
-   **📲 Seamless Telegram Integration:** Distributes the final digest automatically through your configured Telegram channels.
-   **🔧 Modular & Scalable:** Built with a well-organized and modular architecture that allows for easy maintenance and future expansion.

---

## 🛠️ Technologies Used

-   **Python:** Core programming language
-   **Telegram API:** For news distribution
-   **LLM Integration:** AI-powered content processing
-   **Database Management:** Data storage and retrieval
-   **Caching Services:** Performance optimization

---

## 📁 Project Structure


```

AI-DIGEST-SYSTEM/
├── main.py                 # Main application entry point
├── config.py               # Configuration settings
├── database.py             # Database management
├── requirements.txt        # Python dependencies
├── services/
│   ├── llm_client.py       # LLM integration service
│   ├── cache_service.py    # Caching functionality
│   └── memory_optimizer.py # Memory management
├── tools/
│   ├── evaluators.py       # Content evaluation tools
│   └── adapters/           # Various adapters
└── workflows/
    └── digest_builder.py   # Digest creation workflow

```



---

## ⚙️ Installation & Setup

1. **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AI-DIGEST-SYSTEM
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure the application:**
    - Update `config.py` with your specific settings.
    - Add your Telegram API credentials.
    - Configure any required API keys.

---

## 🚀 Usage

1. **Run the main application:**
    ```bash
    python main.py
    ```

2. **Monitor the process:**
    - Check logs for digest creation status.
    - Verify Telegram distribution.
    - Monitor performance metrics.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch:
    ```bash
    git checkout -b feature/amazing-feature
    ```
3. Commit your changes:
    ```bash
    git commit -m 'Add some amazing feature'
    ```
4. Push to the branch:
    ```bash
    git push origin feature/amazing-feature
    ```
5. Open a Pull Request.

---

## 📝 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

If you encounter any issues or have questions, please:

- Open an issue on GitHub.
- Check the logs for error details.
- Review the configuration settings.

---
