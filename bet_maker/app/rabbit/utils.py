from app.db.models import Status


def map_producer_to_consumer_status(producer_status):
    mapping = {
        "незавершённое": Status.IN_PROGRESS,
        "завершено выигрышем первой команды": Status.WIN,
        "завершено выигрышем второй команды": Status.FAIL
    }
    return mapping.get(producer_status, Status.IN_PROGRESS)