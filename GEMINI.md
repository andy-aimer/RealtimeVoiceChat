
# Gemini Project Analysis: Real-Time AI Voice Chat

## Project Overview

This project is a real-time AI voice chat application that enables users to have spoken conversations with a Large Language Model (LLM). The application consists of a Python backend powered by FastAPI and a frontend built with vanilla JavaScript. Real-time communication between the client and server is facilitated by WebSockets. The system is designed to be flexible, supporting various Speech-to-Text (STT) and Text-to-Speech (TTS) engines. For ease of deployment, the entire application is containerized using Docker.

The core functionality is orchestrated by a sophisticated pipeline manager that handles audio processing, LLM inference, and the synthesis of speech, ensuring a fluid conversational experience. The application also includes features for session management with reconnection capabilities, health checks, and performance monitoring.

## Building and Running

The application can be set up and run in two ways: using Docker (the recommended approach) or by a manual installation.

### Docker (Recommended)

1.  **Build the Docker images:**
    ```bash
    docker compose build
    ```
2.  **Start the application and services:**
    ```bash
    docker compose up -d
    ```
3.  **Pull the required Ollama model:**
    ```bash
    docker compose exec ollama ollama pull hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M
    ```
4.  **Stop the services:**
    ```bash
    docker compose down
    ```

### Manual Installation

1.  **Create and activate a Python virtual environment.**
2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Start the backend server:**
    ```bash
    python src/server.py
    ```

After starting the application, the voice chat interface is accessible at `http://localhost:8000`.

## Development Conventions

*   **Modular Architecture:** The backend is organized into distinct modules for handling audio I/O (`audio_in.py`, `audio_module.py`), LLM interactions (`llm_module.py`), and overall pipeline orchestration (`speech_pipeline_manager.py`).
*   **Web Framework:** The backend utilizes `FastAPI`, a modern, high-performance web framework for Python.
*   **Frontend:** The user interface is crafted with vanilla JavaScript, ensuring a lightweight and responsive experience. The frontend code is located in `src/static/app.js`.
*   **Real-time Communication:** `WebSockets` are used for low-latency, bidirectional communication between the frontend and the backend.
*   **Containerization:** A `Dockerfile` and `docker-compose.yml` are provided for building and running the application in a containerized environment, simplifying dependency management and deployment.
*   **Logging:** The application employs a custom logging middleware to generate structured JSON logs, which is beneficial for monitoring and debugging.
*   **Monitoring:** Health check (`/health`) and metrics (`/metrics`) endpoints are available for observing the application's status and performance.
*   **Session Management:** The frontend implements a `WebSocketClient` with automatic reconnection and session persistence, enhancing the user experience by maintaining the conversation context across interruptions.
*   **Code Style:** The codebase is well-documented with comments and docstrings, which aids in understanding and maintainability.
