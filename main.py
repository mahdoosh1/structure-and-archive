from math import log2, ceil
from types import NoneType


def size_of(value):
    if not isinstance(value, int):
        return len(value)
    if value < 0:
        a = ceil(log2(-value))
    else:
        a = ceil(log2(value+1))
    return max(ceil(a/8),1)
class Structure:
    def __init__(self):
        self.funcs = {}
        self.struct = {} #{name, required=True}
    def update_struct(self, pairs):
        for i in pairs:
            if isinstance(i, tuple):
                self.struct[i[0]] = i[1]
            else:
                self.struct[i] = True
    def add_func(self, input_names, func, output_name, name=None):
        if name is None:
            name = output_name
        self.funcs.update({name: [func, input_names, output_name]})
    def run_funcs(self, variables, *, log=True):
        for name, (func, input_names, output_name) in self.funcs.items():
            inputs = [variables[i] for i in input_names]
            output = func(*inputs)
            if not output is None:
                variables[output_name] = output
            if log:
                print(f"Function {name} success")
        struct = []
        for name, req in self.struct.items():
            if name in variables.keys():
                if not any([isinstance(variables[name], bytes),
                            isinstance(variables[name], bytearray),
                            isinstance(variables[name], NoneType),
                            isinstance(variables[name], str)]):
                    raise TypeError(f"Variable {name} Should return bytes or bytearray object")
                if isinstance(variables[name], str):
                    struct.append(variables[name].encode('utf-8'))
                else:
                    struct.append(variables[name])
            elif req:
                raise EOFError("Required Structure Variable {name} missing")
        return b"".join(struct)

class FILE(Structure):
    def __init__(self):
        super().__init__()
        self.struct = ["type", "name_len", "name", "len_len", "data_len", "data"]
        self.funcs = {}
        self.add_func([], lambda: b'\x00', "type")
        self.add_func(["name"], lambda x: len(x).to_bytes(1, 'big'), "name_len")
        self.add_func(["data"], len, "data_len_int")
        self.add_func(["data_len_int"], size_of, "len_len_int")
        self.add_func(["len_len_int"], lambda x: x.to_bytes(1, 'big'), "len_len")
        self.add_func(["data_len_int", "len_len_int"], lambda x, y: x.to_bytes(y, 'big'), "data_len")
    def update_struct(self, pairs):
        raise NotImplementedError("This is a frozen class")
    def add_func(self, input_names, func, output_name, name=None):
        raise NotImplementedError("This is a frozen class")
FILE = FILE()
file = FILE.run_funcs

class DIR(Structure):
    def __init__(self):
        super().__init__()
        self.struct = ["type", "name_len", "name", "file_count", "file_bytes"]
        self.funcs = {}
        self.add_func([], lambda: b'\x01', "type")
        self.add_func(["name"],lambda x: len(x).to_bytes(1,'big'),"name_len")
        self.add_func(["files"],lambda x: b''.join(x),"file_bytes")
        self.add_func(["files"],lambda x: len(x).to_bytes(2,'big'),"file_count")
    def update_struct(self, pairs):
        raise NotImplementedError("This is a frozen class")
    def add_func(self, input_names, func, output_name, name=None):
        raise NotImplementedError("This is a frozen class")
DIR = DIR()
dir = DIR.run_funcs


def append_to_nested_list(main_list, target_list, data):
    def recursive_search(sub_list, target_index):
        if target_index == len(target_list):
            if isinstance(sub_list, list):
                sub_list.append(data)
                return True
            return False
        for item in sub_list:
            if isinstance(item, tuple) and item[0] == target_list[target_index]:
                if recursive_search(item[1], target_index + 1):
                    return True
        return False

    for item in main_list:
        if isinstance(item, tuple) and item[0] == target_list[0]:
            if recursive_search(item[1], 1):
                return main_list
    return main_list
def to_files(root, _archive=True):
    out = []
    for type,name,data in root:
        if type:
            out.append(dir({
                "name":name,
                "files":to_files(data,False)
            }))
        else:
            out.append(file({
                "name":name,
                "data":data
            }))
    if _archive:
        return b''.join(out)
    return out