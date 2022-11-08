import os
import sys

sys.path.append("/django/scraper")

# Scrapy settings for scrapy_app project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "scrapy_app"

SPIDER_MODULES = ["scraper.scrapy_app.spiders"]
NEWSPIDER_MODULE = "scraper.scrapy_app.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'scrapy_app (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

RETRY_HTTP_CODES = [429]

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'scrapy_app.middlewares.ScrapyAppSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "scrapy_app.middlewares.TooManyRequestsRetryMiddleware": 543,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "scraper.scrapy_app.pipelines.ScrapyAppPipeline": 300,
}

FILES_STORE = os.environ["SCRAPY_FILES_FOLDER"] + "files/"
# Since files are uploaded to minio, clear the local files folder after 1 day
FILES_EXPIRES = 1

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 0
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 16.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = '/var/lib/scrapy/httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
# HTTPCACHE_POLICY = 'scrapy.extensions.httpcache.RFC2616Policy'
# HTTPCACHE_GZIP = True

# Exit on first error (TEMP DISABLED)
CLOSESPIDER_ERRORCOUNT = 0

COMPRESSION_ENABLED = True

LOG_LEVEL = "DEBUG"

# Follow redirect on http://publications.europa.eu/resource/celex/32018D1720
# Still got errors downloading, implemented workaround in:
# https://stackoverflow.com/questions/37368030/error-302-downloading-file-in-scrapy/38783648
MEDIA_ALLOW_REDIRECTS = True
HTTPERROR_ALLOWED_CODES = [301, 302]
CONCURRENT_REQUESTS_PER_DOMAIN = 16


# # Export feeds
# FEEDS = {
#     '/var/lib/scrapy/feeds/items-%(name)s-%(time)s.jsonl': {
#         'format': 'jsonlines',
#         'encoding': 'utf8',
#         'store_empty': False,
#         'fields': None,
#     }
# }


AWS_ACCESS_KEY_ID = os.environ["MINIO_ACCESS_KEY"]
AWS_SECRET_ACCESS_KEY = os.environ["MINIO_SECRET_KEY"]

AWS_ENDPOINT_URL = "http://" + os.environ["MINIO_STORAGE_ENDPOINT"]

AWS_USE_SSL = False
AWS_VERIFY = False
