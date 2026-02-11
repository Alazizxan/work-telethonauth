import time

_last_requests = {}
COOLDOWN = 60  # 1 minut


def can_request(user_id: int):
    now = time.time()
    last = _last_requests.get(user_id)

    if last and now - last < COOLDOWN:
        return False

    _last_requests[user_id] = now
    return True
