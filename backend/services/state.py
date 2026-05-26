_current_data = None

def set_current_data(df):
    global _current_data
    _current_data = df

def get_current_data():
    return _current_data