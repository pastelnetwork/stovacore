def ensure_type(obj, required_type, name=None):
    if isinstance(obj, required_type):
        return obj
    else:
        if name is None:
            raise TypeError("Invalid type, should be: %s!" % required_type)
        else:
            raise TypeError("Invalid type for field %s, should be %s, was %s" % (name, required_type, type(obj)))


def ensure_type_of_field(container, name, required_type):
    obj = container[name]
    return ensure_type(obj, required_type, name)
