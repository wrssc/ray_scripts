

def update_window_key_dict(window, keys):
    for key in keys:
        if key not in window.key_dict:
            window.key_dict[key] = None


def merge_dicts(dict1, dict2):
    merged = dict1.copy()  # Start with a copy of dict1

    for key, value in dict2.items():
        if key in merged:
            # Merge unique items from dict2[key] into merged[key]
            merged[key] = [x for x in merged[key] if x not in value] + value
        else:
            # Add key and value from dict2 if not in dict1
            merged[key] = value

    # Remove outer level keys with empty lists
    merged = {k: v for k, v in merged.items() if v}

    return merged
