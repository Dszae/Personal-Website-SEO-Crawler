import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

def load_settings(path: str = "config/settings.yaml") -> dict:
    load_dotenv()
    with open(path, encoding="utf-8") as handle: settings = yaml.safe_load(handle)
    settings["database"] = os.getenv("SEO_CRAWLER_DATABASE", settings["database"])
    settings["output_dir"] = os.getenv("SEO_CRAWLER_OUTPUT_DIR", settings["output_dir"])
    settings["user_agent"] = os.getenv("SEO_CRAWLER_USER_AGENT", settings["user_agent"])
    settings["pagespeed_api_key"] = os.getenv("SEO_CRAWLER_PAGESPEED_API_KEY", settings.get("pagespeed_api_key", ""))
    return settings
