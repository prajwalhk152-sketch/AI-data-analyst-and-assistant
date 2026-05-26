# Streamlit Access Guide

## Run on this computer

Double-click:

```text
run_streamlit.bat
```

The app opens at:

```text
http://localhost:8501
```

Other devices on the same Wi-Fi/network can use the network link printed in the terminal, for example:

```text
http://192.168.0.133:8501
```

If another device cannot connect, allow Python or Streamlit through Windows Firewall, or allow inbound TCP port `8501`.

## Make it public for any user

To let anyone access the app with a public internet link:

1. Push this project to GitHub.
2. Go to `https://share.streamlit.io`.
3. Sign in with GitHub.
4. Choose this repository.
5. Set the app file to:

```text
streamlit_app.py
```

6. Deploy.

Streamlit Cloud will install dependencies from the root `requirements.txt` file and give you a public URL.

## Files Added

- `streamlit_app.py` - Streamlit version of the dashboard.
- `run_streamlit.bat` - local launcher with a network link.
- `.streamlit/config.toml` - binds Streamlit to all network interfaces.
- `requirements.txt` - dependencies for Streamlit Cloud.
