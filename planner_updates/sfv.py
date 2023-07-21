# Simple Expo SFV encoder, without validation.

def encode_bare_value(v):
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    else:
        return str(v)


def encode(d):
    items = []
    for key in d:
        item, params = d[key]
        out_item = key
        if item != True:
            out_item += '=' + encode_bare_value(item)
        out_params = []
        for pkey in params:
            pval = params[pkey]
            out_param = pkey
            if pval != True:
                out_param += '=' + encode_bare_value(pval)
            out_params.append(out_param)
        if len(out_params) > 0:
            out_item += '; ' + '; '.join(out_params)
        items.append(out_item)
    return ', '.join(items)
