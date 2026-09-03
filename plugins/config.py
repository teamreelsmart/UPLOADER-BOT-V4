import os
from os import environ, getenv
import logging

logging.basicConfig(
    format='%(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'),
              logging.StreamHandler()],
    level=logging.INFO
)


def required_env(name):
    """Return a required environment variable with a deployment-friendly error."""
    value = environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Add it in your deployment service's environment settings."
        )
    return value


def required_int_env(name):
    """Return a required integer environment variable with a clear validation error."""
    value = required_env(name)
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(
            f"Environment variable {name} must be a numeric value."
        ) from error


class Config(object):
    
    BOT_TOKEN = required_env("BOT_TOKEN")
    API_ID = required_int_env("API_ID")
    API_HASH = required_env("API_HASH")
    
    DOWNLOAD_LOCATION = "./DOWNLOADS"
    MAX_FILE_SIZE = 2194304000
    TG_MAX_FILE_SIZE = 2194304000
    FREE_USER_MAX_FILE_SIZE = 2194304000
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 128))
    DEF_THUMB_NAIL_VID_S = os.environ.get("DEF_THUMB_NAIL_VID_S", "https://placehold.it/90x90")
    HTTP_PROXY = os.environ.get("HTTP_PROXY", "")
    # Keep the API key in the deployment environment; never commit it to source.
    TERABOX_API_KEY = os.environ.get("TERABOX_API_KEY", "")
    TERABOX_API_URL = os.environ.get("TERABOX_API_URL", "https://xapiverse.com/api/terabox")
    
    OUO_IO_API_KEY = ""
    MAX_MESSAGE_LENGTH = 4096
    PROCESS_MAX_TIMEOUT = 3600
    DEF_WATER_MARK_FILE = "@OrvixNetworks"

    ADMIN = set(
        int(x) for x in environ.get("ADMIN", "").split()
        if x.isdigit()
    )

    BANNED_USERS = set(
        int(x) for x in environ.get("BANNED_USERS", "").split()
        if x.isdigit()
    )

    DATABASE_URL = os.environ.get("DATABASE_URL", "")

    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
    LOGGER = logging
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    SESSION_NAME = "UploaderXNTBot"
    UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", "")

    TG_MIN_FILE_SIZE = 2194304000
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "OrvixUploadBot")
    ADL_BOT_RQ = {}

    # Set False off else True
    TRUE_OR_FALSE = os.environ.get("TRUE_OR_FALSE", "False").lower() == "true"

    # Shortlink settings
    SHORT_DOMAIN = environ.get("SHORT_DOMAIN", "")
    SHORT_API = environ.get("SHORT_API", "")

    # Verification video link
    VERIFICATION = os.environ.get("VERIFICATION", "")

    
