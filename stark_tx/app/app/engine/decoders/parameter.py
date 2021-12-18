from app.engine.providers.semantics import get_semantics


def decode_parameters(parameters, parameters_abi):
    decoded_parameters = []
    parameters_index = 0
    abi_index = 0

    # TODO: check me, dunno why i took len - 1, without it it fails
    while parameters_index < len(parameters) - 1:
        raw_input = parameters[parameters_index]
        parameter_type = (
            "address"
            if "address" in parameters_abi[abi_index]["name"]
            else parameters_abi[abi_index]["type"]
        )

        if parameter_type == 'struct':
            value = decode_struct(parameters[parameters_index:], parameters_abi[abi_index]['struct_members'])
        else:
            value = decode_atomic_parameter(raw_input, parameter_type)

        if (
            abi_index + 1 < len(parameters_abi)
            and parameters_abi[abi_index + 1]["type"] == "felt*"
            and parameters_abi[abi_index]["name"] == parameters_abi[abi_index + 1]["name"] + "_len"
        ):
            array_len = value
            value = [
                array_element
                for array_element in parameters[
                    parameters_index + 1: parameters_index + array_len + 1
                ]
            ]
            name = parameters_abi[abi_index + 1]["name"]
            parameters_index += array_len + 1
            abi_index += 2
        else:
            name = parameters_abi[abi_index]["name"]
            if parameter_type == 'struct':
                parameters_index += len(parameters_abi[abi_index]['struct_members'])
            else:
                parameters_index += 1
            abi_index += 1
        decoded_parameters.append(dict(name=name, value=value))

    if (
        len(decoded_parameters) == 3
        and decoded_parameters[0]["name"] in ("contract_address", "to")
        and decoded_parameters[1]["name"] in ("function_selector", "selector")
        and decoded_parameters[2]["name"] == "calldata"
    ):
        semantics = get_semantics(hex(decoded_parameters[0]["value"]))
        if semantics:
            function_abi = (
                semantics["abi"]["functions"][hex(decoded_parameters[1]["value"])]
                if hex(decoded_parameters[1]["value"]) in semantics["abi"]["functions"]
                else None
            )
            if function_abi:
                function_name = function_abi["name"]
                function_inputs = decode_parameters(
                    decoded_parameters[2]["value"], function_abi["inputs"]
                )
                input_string = create_parameters_string(function_inputs)
                decoded_parameters = [
                    dict(
                        name="call",
                        value=f"{semantics['name']}.{function_name}({input_string})",
                    )
                ]

    return decoded_parameters


def create_parameters_string(parameters):
    parameters_string = ", ".join(
        [
            f"{_input['name']}={_input['value'] if type(_input['value']) != list else '['+create_parameters_string(_input['value'])+']'}"
            for _input in parameters
        ]
    )
    return parameters_string


def decode_struct(raw_values, members):
    values = []
    for i, member in enumerate(members):
        values.append(dict(name=member['name'], value=decode_atomic_parameter(raw_values[i], member['type'])))

    return values


def decode_atomic_parameter(raw_value, parameter_type):
    if parameter_type == "felt":
        parameter_value = int(raw_value)
    elif parameter_type == "address":
        parameter_value = hex(int(raw_value))
    elif parameter_type == "string":
        parameter_value = bytes.fromhex(hex(int(raw_value))[2:]).decode("utf-8").replace("\x00", "")
    else:
        parameter_value = raw_value

    return parameter_value
