import os
from upstash_redis import Redis
from fastapi import Request
from app.constants.constants import MAX_ANALYSIS_PER_HOUR_PER_IP, MAX_ANALYSIS_PER_DAY_PER_IP

URL = os.environ["UPSTASH_REDIS_REST_URL"]
TOKEN = os.environ["UPSTASH_REDIS_REST_TOKEN"]
redis_client = Redis(url=URL, token=TOKEN)

# TTL IN SECONDS
HOURLY_TTL = 60 * 60 # (1 hour)
DAILY_TTL = 24 * 60 * 60  # (24 hours)
ANALYSIS_LOCK_TTL = 5 * 60 # (5 minutes)

identifier_hour = f'loopholio:analysis:hour'
identifier_day = f'loopholio:analysis:day'

def getclientIp(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host

def can_process(request: Request):
    client_ip = getclientIp(request)
    analysis_lock_acquired = acquire_analysis_lock(client_ip)
    
    if not analysis_lock_acquired:
        return {'allow': False, "message": "Another analysis running"}

    can_access = check_limits(client_ip) # allow, message
    if not can_access["allow"]:
        return {'allow': False, "message": can_access["message"]}

    return {'allow': True, "message": "Processing Request"}

def check_limits(client_ip):
    key_hour = f'{identifier_hour}:{client_ip}'
    key_day = f'{identifier_day}:{client_ip}'
    total_analysis_day = redis_client.get(key_day)
    total_analysis_hour = redis_client.get(key_hour)

    if not total_analysis_day: # No analysis done today - first analysis of the day
        redis_client.incr(key_day)
        redis_client.incr(key_hour)
        redis_client.expire(key_hour, HOURLY_TTL)
        redis_client.expire(key_day, DAILY_TTL)
        return {'allow': True, 'message': ""}
    else: # some analysis done today
        if int(total_analysis_day) >= MAX_ANALYSIS_PER_DAY_PER_IP: # daily limit exceeded
            return {'allow': False, 'message': "Daily rate limit exceeded"}

        # daily limit remaining but need to check hourly limit as well
        if not total_analysis_hour: # no analysis done this hour
            redis_client.incr(key_day)
            redis_client.incr(key_hour)
            redis_client.expire(key_hour, HOURLY_TTL)
            return {'allow': True, 'message': ""}

        # some analysis done this hour need to check how many and if we can allow request for this hour
        if int(total_analysis_hour) >= MAX_ANALYSIS_PER_HOUR_PER_IP: # hourly limit exceeded
            return {'allow': False, 'message': "Hourly rate limit exceeded"}
        else:
            redis_client.incr(key_day)
            redis_client.incr(key_hour)
            return {'allow': True, 'message': ""}

def acquire_analysis_lock(client_ip: str) -> bool:
    key = f'loopholio:analysis:current:{client_ip}'
    result = redis_client.set(
        key,
        "1",
        nx=True,
        ex=ANALYSIS_LOCK_TTL,
    )
    return bool(result)

def remove_analysis_lock(request: Request):
    client_ip = getclientIp(request)
    key = f"loopholio:analysis:current:{client_ip}"
    
    redis_client.delete(key)