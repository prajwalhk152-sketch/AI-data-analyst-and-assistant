# Deployment Guide

This project is ready to deploy as a Streamlit app.

## Best Option: Streamlit Community Cloud

1. Create a GitHub repository.
2. Push this project to that repository.
3. Open `https://share.streamlit.io`.
4. Choose the repository.
5. Set the main file path to:

```text
streamlit_app.py
```

6. Deploy.

Streamlit Cloud will install packages from `requirements.txt`.

## Render

1. Push this project to GitHub.
2. Open `https://render.com`.
3. Create a new Blueprint.
4. Select this repository.
5. Render will read `render.yaml`.

The start command is:

```text
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

## Docker

Build:

```bash
docker build -t ai-data-analyst-assistant .
```

Run:

```bash
docker run -p 8501:8501 ai-data-analyst-assistant
```

Open:

```text
http://localhost:8501
```

## Local Public Link

For same Wi-Fi access only, run:

```text
run_streamlit.bat
```

Then open the network URL printed in the terminal.
