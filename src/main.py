from webpanel import app as web_app
import config
import uvicorn

if __name__ == "__main__":
    uvicorn.run(web_app, host=config.WEB_HOST, port=config.WEB_PORT, log_level="info")
