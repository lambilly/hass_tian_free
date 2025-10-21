"""Constants for Tian API integration."""

DOMAIN = "tian_free"
NAME = "天聚数行免费版"
VERSION = "1.1.0"

CONF_API_KEY = "api_key"
CONF_SCROLL_INTERVAL = "scroll_interval"  # 新增：滚动间隔配置

# API endpoints
JOKE_API_URL = "https://apis.tianapi.com/joke/index"
MORNING_API_URL = "https://apis.tianapi.com/zaoan/index"
EVENING_API_URL = "https://apis.tianapi.com/wanan/index"
POETRY_API_URL = "https://apis.tianapi.com/poetry/index"
SONG_CI_API_URL = "https://apis.tianapi.com/zmsc/index"
YUAN_QU_API_URL = "https://apis.tianapi.com/yuanqu/index"
HISTORY_API_URL = "https://apis.tianapi.com/pitlishi/index"
SENTENCE_API_URL = "https://apis.tianapi.com/gjmj/index"
COUPLET_API_URL = "https://apis.tianapi.com/duilian/index"
MAXIM_API_URL = "https://apis.tianapi.com/enmaxim/index"

# Device info
DEVICE_NAME = "天聚信息查询"
DEVICE_MANUFACTURER = "天聚数行"
DEVICE_MODEL = "信息查询免费版"

# 新增：轮换内容列表
SCROLL_CONTENT_TYPES = [
    "joke", "morning", "evening", "poetry", "songci", 
    "yuanqu", "history", "sentence", "couplet", "maxim"
]