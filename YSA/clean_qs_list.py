

def open_file(filepath):
    with open(filepath, 'r') as infile:
        content = infile.read()
    return content


def remove_items_from_list(content, removable):
    
    for line in content.splitlines():
        if line.split()[0] in removable.splitlines():
