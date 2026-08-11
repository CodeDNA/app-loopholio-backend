# CONSTANTS

# INPUT: FILE/TEXT LIMITS
MAX_FILE_SIZE_MB = 5 # max allowed document file size(Mb)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024 # max allowed document file size(bytes)
MIN_REQUIRED_TEXT_LENGTH = 100 # min required length for tosText
MAX_ALLOWED_TEXT_LENGTH = 50000 # max allowed length for tosText
MAX_SECTIONS_ALLOWED_PER_DOCUMENT = 25 # max chunk limit: to prevent too many llm calls during fanouts

# API RATE LIMITS
MAX_ANALYSIS_PER_HOUR_PER_IP = 2
MAX_ANALYSIS_PER_DAY_PER_IP = 5
MAX_CONCURRENT_REQUESTS_PER_IP = 1

# CORRESPONDING ERRORS
MAX_FILE_SIZE_ERROR = f'Max file size exceeded! File must be smaller than {MAX_FILE_SIZE_MB} Mb'
MIN_REQUIRED_TEXT_LENGTH_ERROR = f'Input text length must be at least {MIN_REQUIRED_TEXT_LENGTH} characters'
MAX_ALLOWED_TEXT_LENGTH_ERROR = f'Input text length must be less than {MAX_ALLOWED_TEXT_LENGTH} characters'

MAX_ANALYSIS_PER_HOUR_PER_IP_ERROR = f'You have hit your hourly analysis limit of {MAX_ANALYSIS_PER_HOUR_PER_IP}'
MAX_ANALYSIS_PER_DAY_PER_IP_ERROR = f'You have hit your daily analysis limit of {MAX_ANALYSIS_PER_DAY_PER_IP}'
MAX_CONCURRENT_REQUESTS_PER_IP_ERROR = f'You have hit max concurrent request limit. Please close other browsers/tabs running LooopHolio analysis'