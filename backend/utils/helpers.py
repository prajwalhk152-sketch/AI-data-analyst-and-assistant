def success(message, data=None):
    return {
        "status": "success",
        "message": message,
        "data": data
    }

def error(message):
    return {
        "status": "error",
        "message": message
    }