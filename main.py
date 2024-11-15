from math import log2, ceil
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
        self.value = b""
        self.dict = {}
        self.vars = {}
        self.funcs = {}
        self.struct = {}
    def assign_var(self, name, value):
        self.vars[name] = value
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
def double_size(data):
    a = size_of(len(data))
    b = size_of(a)
    c = b.to_bytes(2,'big')+a.to_bytes(b,'big')
    return c
def file(data, name):
    if "/" in name:
        raise NameError("Name should not contain slashes")
    if len(name) > 254:
        raise NameError("Name should not be more than 254 charactors")
    if len(data) > 1024**3:
        raise ValueError("Data should not be more than 1GB")
    s = Structure()
    s.assign_var("name",name.encode('utf-8'))
    s.assign_var("data",data)
    s.assign_var("type",b"\x00")
    s.assign_var("name_size",len(name))
    s.assign_var("data_size",double_size(data))
    s.struct_values(["type","name_size","name","data_size","data"])
    return s.value
def directory(files,name):
    if "/" in name:
        raise NameError("Name should not contain slashes")
    if len(name) > 254:
        raise NameError("Name should not be more than 254 charactors")
    if size_of(len(files)) > 10**5:
        raise ValueError("There should not be more than 10,000 files")
    s = Structure()
    s.assign_var("name",name.encode('utf-8'))
    s.assign_var("file_len",len(files).to_bytes(2,'big'))
    s.assign_var("files",b"".join(files))
    s.assign_var("type",b"\x01")
    s.assign_var('name_size',len(name))
    s.struct_values(["type","name_size","name","file_len","files"])
    return s.value
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
def to_files(root):
    out = []
    for type,name,data in root:
        if type:
            out.append(directory(to_files(data),name))
        else:
            out.append(file(data,name))
    return out
def archive(root):
    return directory(to_files(root),'~')
root = [(0,"meow.txt",b"meow"),(1,"meow",[(0,"meow2.txt",b"meow2")])]
#file format: type(0), name, data
#dir format: type(1), name, list of files or dirs
print(archive(root)) #bytes object
#output file format: type(\x00), name_len(1byte),name,len_len(2bytes),file_len(1-256 bytes),file
#output dir format: type(\x01),name_len(1byte),name,number_of_things_inside(2bytes),things_inside
