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
class DeprecatedStructure:
    def __init__(self):
        self.value = b""
        self.dict = {}
        self.vars = {}
        self.funcs = {}
        self.struct = {}
    def assign_var(self, name, value):
        self.vars[name] = value
    def assign_vars(self, pairs):
        for name, value in pairs:
            self.assign_var(name, value)
    def assign_calculation(self, names, function, function_name, out_name=None):
        if out_name is None:
            out_name = function_name
        self.funcs[function_name] = (function, names, out_name)
    def calculate(self, *, log=True, struct=True):
        for key, val in self.funcs.items():
            func = val[0]
            names = val[1]
            vars = []
            for i in names:
                vars.append(self.vars[i])
            out = func(*vars)
            self.vars[val[2]] = out
            if log:
                print("function",key, "Completed.")
        if struct:
            self.struct_values()
    def add_structs(self, names):
        self.struct = names
    def struct_values(self, names=None):
        if names is None:
            names = self.struct
        for i in names:
            if isinstance(i, tuple):
                key, val = i
            else:
                key = val = i
            self.assign_value(key, self.vars[val])
    def assign_value(self, name, value):
        if isinstance(value, int):
            a = size_of(value)
            if value < 0:
                value = 256**a+value
            value = value.to_bytes(a, 'big')
        elif isinstance(value, bytes):
            pass
        elif isinstance(value, list):
            if len(value):
                a = value[0]
                if isinstance(a, bytes):
                    value = b"".join(value)
                else:
                    value = bytearray(value)
        elif not isinstance(value, bytearray):
            value = bytearray([value])
        self.dict[name]=(len(self.value),len(value))
        self.value += value
    def get_value(self, name):
        start, size = self.dict[name]
        return self.value[start:start+size]
    def get_values(self):
        out = {}
        for key in self.dict.keys():
            out[key] = self.get_value(key)
        return out
class Structure:
    def __init__(self):
        self.funcs = {}
        self.struct = {} #{name, required=True}
        self.frozen = False
    def freeze(self):
        self.frozen = True
    def update_struct(self, pairs):
        if self.frozen:
            raise AttributeError("This object is frozen")
        for i in pairs:
            if isinstance(i, tuple):
                self.struct[i[0]] = i[1]
            else:
                self.struct[i] = True
    def add_func(self, input_names, func, output_name, name=None):
        if self.frozen:
            raise AttributeError("This object is frozen")
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


FILE = Structure()
FILE.update_struct(["type","name_len","name","len_len","data_len","data"])
FILE_NAME_LEN = lambda x: len(x).to_bytes(1,'big')
FILE_LEN_LEN = lambda x: x.to_bytes(1,'big')
FILE_DATA_LEN_INT = lambda x: len(x)
FILE_DATA_LEN = lambda x, y: x.to_bytes(y,'big')
FILE_TYPE = lambda : b'\x00'
FILE.add_func([],FILE_TYPE,"type")
FILE.add_func(["name"],FILE_NAME_LEN,"name_len")
FILE.add_func(["data"],FILE_DATA_LEN_INT,"data_len_int")
FILE.add_func(["data_len_int"],size_of,"len_len_int")
FILE.add_func(["len_len_int"],FILE_LEN_LEN,"len_len")
FILE.add_func(["data_len_int","len_len_int"],FILE_DATA_LEN,"data_len")
FILE.freeze()

file = lambda vars: FILE.run_funcs(variables=vars)

DIR = Structure()
DIR.update_struct(["type","name_len","name","file_count","file_bytes"])
DIR_NAME_LEN = lambda x: len(x).to_bytes(1,'big')
DIR_TYPE = lambda : b'\x01'
DIR_JOIN_FILES = lambda x: b''.join(x)
DIR_COUNT_FILES = lambda x: len(x).to_bytes(2,'big')
DIR.add_func([],DIR_TYPE,"type")
DIR.add_func(["name"],DIR_NAME_LEN,"name_len")
DIR.add_func(["files"],DIR_JOIN_FILES,"file_bytes")
DIR.add_func(["files"],DIR_COUNT_FILES,"file_count")
DIR.freeze()

dir = lambda vars: DIR.run_funcs(variables=vars)

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