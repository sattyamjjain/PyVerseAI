import re
from collections import defaultdict, namedtuple

# Define a class to store module information
Module = namedtuple("Module", ["name", "instances", "primitives"])


def parse_verilog(content):
    _modules = {}
    current_module = None
    instance_pattern = re.compile(r"(\w+)\s+(\w+)\s*\((.*?)\);", re.DOTALL)

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("module"):
            module_name = line.split()[1]
            current_module = Module(
                name=module_name,
                instances=defaultdict(list),
                primitives=defaultdict(int),
            )
            _modules[module_name] = current_module
        elif line.startswith("endmodule"):
            current_module = None
        elif current_module and instance_pattern.match(line):
            module_name, instance_name, pins = instance_pattern.match(line).groups()
            if (
                "invN1" in module_name
                or "nand2N1" in module_name
                or "nor2N1" in module_name
            ):
                current_module.primitives[module_name] += 1
            else:
                current_module.instances[module_name].append(instance_name)
    return _modules


def count_instances(_modules, module_name):
    def _count_instances(module, _counts):
        for sub_module_name, instances in module.instances.items():
            _counts[sub_module_name] += len(instances)
            if sub_module_name in _modules:
                _count_instances(_modules[sub_module_name], _counts)
        for primitive, count in module.primitives.items():
            _counts[primitive] += count

        for sub_module_name in module.instances:
            if sub_module_name in _modules:
                _count_instances(_modules[sub_module_name], _counts)

    counts = defaultdict(int)
    if module_name in _modules:
        _count_instances(_modules[module_name], counts)
    return counts


if __name__ == "__main__":
    file_path = "input.v"

    with open(file_path, "r") as file:
        verilog_file_content = file.read()

    try:
        top_cell_instance_counts = dict(
            count_instances(parse_verilog(verilog_file_content), "TopCell")
        )
        print(top_cell_instance_counts)
    except Exception as e:
        print(f"Failed to parse verilog due to {str(e)}")
