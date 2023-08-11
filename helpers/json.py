def default(obj):
    if not hasattr(obj, 'to_json'):
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
    return obj.to_json()
