from System import Environment


def get_user_name():
    try:
        user_name = str(Environment.UserName)
    except Exception as e:
        user_name = None
    return user_name
