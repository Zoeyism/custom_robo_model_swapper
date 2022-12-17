import os
import base64
import PySimpleGUI as GUI


def open_sfd(file_name):
    """
    Opens an SFD file (AKA, a BIN file with "SFD " in the first four bytes).
    Returns the data as a Byte Array. Does NOT check if "SFD " is at start!
    :param file_name: File's name and directory, string.
    :return: Byte Array of file's data. If file_name is not found, returns None instead.
    """

    try:
        file = open(file_name, "rb")
    except FileNotFoundError:
        file = None
        return file

    # SFD (StudioFake Data) files start with 4 bytes: SFD, and a space.
    file_data = file.read()
    file.close()

    # if not file_data.startswith(b"SFD"):
    # print("Error: File is not an SFD file.")
    # file_data = None

    return file_data


def get_uint32(byte_list, index=0):
    """
    Takes a list of bytes, the index you wish to start at, and then reads
    the 4 bytes from your starting index onward in Big Endian format.
    :param byte_list: The byte list.
    :param index: Index that your uint32 starts at.
    :return: Converted value from Big Endian format. If index is invalid, returns None instead.
    """
    try:
        value = int.from_bytes(byte_list[index:(index + 4)], 'big')
    except IndexError:
        value = None
    return value


def print_object_locations(file_data):
    """
    Prints locations of objects in an SFD file. Used in development
    :param file_data: Full SFD file loaded in binary format.
    :return: None
    """
    # Bytes 4-8 are an uint32 that refers to how many 'objects' are in the file.
    total_objects = get_uint32(file_data[4:8], 0)

    model_offsets = []
    model_lengths = []
    model_gaps = []

    # After the 4 bytes showing how many objects are in the file, the next 4 bytes are the
    # offset of an object; then 4 bytes are the length of the object. Then the next object's
    # offset is listed, then the length of said object, repeating until all object's offsets
    # and lengths are listed. The first object's offset appears to always be 32768, or 0x8000

    for i in range(0, total_objects):
        model_offsets.append(get_uint32(file_data[8 + (i * 8):(i * 8) + 12]))

        model_lengths.append(get_uint32(file_data[(i * 8) + 12:(i * 8) + 16]))

    for i in range(0, total_objects):
        if i != total_objects - 1:
            gap = model_offsets[i + 1] - (model_offsets[i] + model_lengths[i])
        else:
            gap = len(file_data) - (model_offsets[i] + model_lengths[i])
        model_gaps.append(gap)

    for j in range(0, total_objects):
        print("Object " + str(j + 1) + ": ")
        print(model_offsets[j], "\t", model_lengths[j], "\t", model_gaps[j], "\n")


def is_model_smaller(model_one, model_two):
    """
    Checks if first model is smaller than (or = to) first model;
    Returns bool from that check.
    :param model_one: First model's file path, string. INCLUDE DIRECTORY.
    :param model_two: Second model's file path, string. INCLUDE DIRECTORY.
    :return: Bool; True if first model is smaller or equal to second, False otherwise.
    """

    size_one = os.path.getsize(model_one)
    size_two = os.path.getsize(model_two)

    if size_one <= size_two:
        boolean = True
    else:
        boolean = False

    return boolean


def get_file_names(directory="models"):
    """
    Returns all files in models folder, as a list of strings.
    :param directory: Directory to get files from. String.
    :return: List of strings, all of a folder's file names sorted.
    """

    all_files = []

    for entry in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, entry)):
            all_files.append(entry)

    all_files.sort()

    return all_files


def write_bytes_to_file(byte_array, name_of_file, file_type=".BIN"):
    """
    Writes file data to the name of the file, but in the result_files folder.
    If the file already exists in that folder, the file name is appended with
    (1) or a higher number until it is a new file name.
    :param byte_array: An array of bytes.
    :param name_of_file: File's name, without directory; uses "result_files" directory.
    :param file_type: String of characters for file's identifier. Includes ".", like in ".BIN".
    :return: None
    """

    folder_files = get_file_names("result_files")

    num = 1
    og_name = name_of_file[:]

    while name_of_file in folder_files:
        name_of_file = og_name
        name_of_file = name_of_file[:-(len(file_type))]
        name_of_file += ("(" + str(num) + ")" + file_type)
        num += 1

    file = open(os.path.join("result_files", name_of_file), "wb")
    file.write(byte_array[:])
    file.close()


def replace_models(file_names, target_names, new_names):
    """
    Full process of replacing models in selected files.
    :param file_names: List of file names (strings), which each include their directory!
    :param target_names: List of models to be replaced; strings, names from the 'models' folder, no directory!
    :param new_names: List of models to put in game; strings, names from the 'models' folder, no directory!
    :return: None
    """
    for i in range(0, len(file_names)):
        # Opens the file and reads all data as a byte array.
        name_of_file = file_names[i]
        file_data = open_sfd(os.path.join("source_files", name_of_file))
        new_file = bytearray(file_data[:])

        # After the 4 bytes showing how many objects are in the file, the next 4 bytes are the
        # offset of an object; then 4 bytes are the length of the object. Then the next object's
        # offset is listed, then the length of said object, repeating until all object's offsets
        # and lengths are listed. The first object's offset appears to always be 32768, or 0x8000

        # Confirms # of models to replace;
        #   if unequal # of models, goes with lower # to prevent index errors
        model_num = min(len(target_names), len(new_names))

        for j in range(0, model_num):
            target_data = open_sfd(
                os.path.join("models", target_names[j]))
            new_model = open_sfd(
                os.path.join("models", new_names[j]))

            # Searches for all bytes of a model's data to find the starting index of the model;
            # the large search data size is to guarantee that correct model is found.
            current_index = 0
            finding_models = True

            while finding_models:
                target_index = file_data[current_index:].find(target_data[:])

                if target_index < 0:
                    finding_models = False
                    continue

                target_index += current_index  # corrects for slicing file_data during .find()
                current_index = target_index + 128  # moves index beyond to continue search
                target_length = get_uint32(target_data[4:8])

                # print(target_index)

                new_file[target_index:(target_index + len(new_model))] = new_model[:]

                gap = target_length - len(new_model)

                gap_filler = bytearray(gap)

                new_file[(target_index + len(new_model)):(target_index + target_length)] = gap_filler[:]

        # Writes the data of the new file to the result_files folder
        write_bytes_to_file(new_file, name_of_file)


def find_texture_data(model_name, directory="models", robo=False, weapon=False):
    """
    Finds a model's texture index location.
    :param model_name: Model's name, string.
    :param directory: Model's directory, string.
    :param robo: Bool, if the model is a robo. For correctly determining index location.
    :param weapon: Bool, if the model is a weapon. For correctly determining index location.
    :return: None
    """
    model = open_sfd(os.path.join(directory, model_name))

    if not robo:
        pointers_index = get_uint32(model, 24)
    else:
        pointers_index = get_uint32(model, 24) + 8

    if weapon:
        pointers_index = get_uint32(model, 24) + 64 + 8

    # Finding image header index to find image start, length, width, and encoding of texture file.
    img_header_index = get_uint32(model, pointers_index) + 64
    length = model[img_header_index + 4:img_header_index + 6]
    width = model[img_header_index + 6:img_header_index + 8]
    encoding_bytes = model[img_header_index + 8:img_header_index + 12]

    image_index = get_uint32(model, img_header_index) + 64

    # Image end index; varies for unclear reasons, consistent among types of model (weapon, pod, robo, etc.)
    if not weapon:
        image_end_index = get_uint32(model, 8) + 64
        # image_end_index = get_uint32(model, 8) + 48  # For Pods, is the exact image_end_index, not a pointer
    else:
        image_end_index = get_uint32(model, 24) + 36
    image_end_index = get_uint32(model, image_end_index) + 64

    image_data = model[image_index:image_end_index]

    # Creates new header for texture file to create a proper TPL image.
    new_bin_data = bytearray(bytes.fromhex('00 20 AF 30 00 00 00 01 00 00 00 0C 00 00 00 14 00 00 00 00'))
    new_bin_data += length
    new_bin_data += width
    new_bin_data += encoding_bytes
    new_bin_data += bytes.fromhex('00 00 00 40 00 00 00 00 00 00 00 00 00 00 00 01'
                                  '00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
    new_bin_data += image_data[:]

    write_bytes_to_file(new_bin_data, (model_name[:-4] + " Texture.tpl"), ".tpl")


def split_sfd(file_name, directory="source_files"):
    """
    Splits an SFD file into separate objects. Gets each object from the set of pointers at the beginning
    of the file to determine each object's start, and length, and creates individual files for each object.
    :param file_name: File's name, string.
    :param directory: File's directory, also string.
    :return: None
    """
    file_data = open_sfd(os.path.join(directory, file_name))

    objects = get_uint32(file_data, 4)

    for i in range(0, objects):
        index = get_uint32(file_data, (8 + (i * 8)))
        length = get_uint32(file_data, (12 + (i * 8)))

        write_bytes_to_file(file_data[index:(index + length)], "Object " + str(i) + ".BIN")


def check_index(new_index, some_list):
    """
    Checks to make sure that the index is within the list's length to prevent errors.
    Shifts to 0 if less than 0, shifts to length-1 if over length.
    :param new_index: Index to be checked
    :param some_list: List to be compared with
    :return: Index that is valid for said list
    """
    if new_index < 0:
        new_index = len(some_list) - 1
    elif new_index >= len(some_list):
        new_index = 0
    return new_index


def main():
    files = ["rpg_t_models.BIN", "rpg_f_models.BIN"]
    GUI.theme("Dark Purple")

    model_names = list(get_file_names())
    model_options_one = model_names.copy()
    model_options_two = model_names.copy()
    selected_models_one = []
    selected_models_two = []

    box_header_one = GUI.Text("In-Game Character Selection")
    box_header_two = GUI.Text("Model to Replace Selection With")
    add_button_one = GUI.Button("Add", key="ADD_ONE")
    add_button_two = GUI.Button("Add", key="ADD_TWO")
    remove_button_one = GUI.Button("Remove", key="REM_ONE")
    remove_button_two = GUI.Button("Remove", key="REM_TWO")
    up_button_one = GUI.Button("Move Up", key="UP_ONE")
    up_button_two = GUI.Button("Move Up", key="UP_TWO")
    down_button_one = GUI.Button("Move Down", key="DOWN_ONE")
    down_button_two = GUI.Button("Move Down", key="DOWN_TWO")

    swap_models_button = GUI.Button("Swap Models", key="SWAP")
    error_text = GUI.Text("", text_color="red", key="ERROR_TEXT")
    success_text = GUI.Text("", text_color="green", key="SUCCESS_TEXT")

    # File names, are set when option is selected in a menu
    add_option_one, add_option_two, remove_option_one, remove_option_two = "", "", "", ""

    char_menu_one = GUI.Listbox(
        model_options_one,
        select_mode=GUI.LISTBOX_SELECT_MODE_SINGLE,
        size=(40, 10),
        enable_events=True,
        key="CHAR_MENU_ONE"
    )

    char_menu_two = GUI.Listbox(
        model_options_two,
        select_mode=GUI.LISTBOX_SELECT_MODE_SINGLE,
        size=(40, 10),
        enable_events=True,
        key="CHAR_MENU_TWO"
    )

    selected_menu_one = GUI.Listbox(
        selected_models_one,
        select_mode=GUI.LISTBOX_SELECT_MODE_SINGLE,
        size=(40, 10),
        enable_events=True,
        key="SLCT_MENU_ONE"
    )

    selected_menu_two = GUI.Listbox(
        selected_models_two,
        select_mode=GUI.LISTBOX_SELECT_MODE_SINGLE,
        size=(40, 10),
        enable_events=True,
        key="SLCT_MENU_TWO"
    )

    column_one = [[box_header_one], [char_menu_one], [add_button_one, remove_button_one], [selected_menu_one],
                  [up_button_one, down_button_one]]
    column_two = [[box_header_two], [char_menu_two], [add_button_two, remove_button_two], [selected_menu_two],
                  [up_button_two, down_button_two]]

    icon_file = open("icon.txt", "r")
    icon_data = base64.b64decode(icon_file.read())
    icon_file.close()

    window = GUI.Window(
        title="Custom Robo Model Swapper",
        layout=[
            [
                GUI.Column(column_one),
                GUI.VSeparator(),
                GUI.Column(column_two)
            ],
            [
                swap_models_button,
                success_text,
                error_text
            ]
        ],
        margins=(100, 50),
        icon=icon_data
    )

    while True:  # WINDOW LOOP #
        event, values = window.read()
        if event == GUI.WIN_CLOSED:
            break

        if event == "CHAR_MENU_ONE" and len(model_options_one) > 0:
            add_option_one = values["CHAR_MENU_ONE"][0]  # File name that was selected

        if event == "CHAR_MENU_TWO" and len(model_options_two) > 0:
            add_option_two = values["CHAR_MENU_TWO"][0]

        if event == "SLCT_MENU_ONE" and len(selected_models_one) > 0:
            remove_option_one = values["SLCT_MENU_ONE"][0]

        if event == "SLCT_MENU_TWO" and len(selected_models_two) > 0:
            remove_option_two = values["SLCT_MENU_TWO"][0]

        if event == "ADD_ONE" and add_option_one in model_options_one:
            new_index = check_index(model_options_one.index(add_option_one) - 1, model_options_one)
            model_options_one.remove(add_option_one)
            selected_models_one.append(add_option_one)
            char_menu_one.update(values=model_options_one, set_to_index=new_index)
            selected_menu_one.update(values=selected_models_one)

        if event == "ADD_TWO" and add_option_two in model_options_two:
            selected_models_two.append(add_option_two)
            selected_menu_two.update(values=selected_models_two)

        if event == "REM_ONE" and remove_option_one in selected_models_one:
            selected_models_one.remove(remove_option_one)
            model_options_one.append(remove_option_one)
            model_options_one.sort()
            char_menu_one.update(values=model_options_one)
            selected_menu_one.update(values=selected_models_one)

        if event == "REM_TWO" and remove_option_two in selected_models_two:
            index = selected_menu_two.get_indexes()[0]
            selected_models_two.pop(index)
            selected_menu_two.update(values=selected_models_two)

        if event == "UP_ONE" and remove_option_one in selected_models_one:
            index = selected_models_one.index(remove_option_one)
            new_index = check_index(index - 1, selected_models_one)

            # Switching the values in each index (Probably should have written a function, but meh)
            selected_models_one[new_index], selected_models_one[index] = \
                selected_models_one[index], selected_models_one[new_index]
            selected_menu_one.update(values=selected_models_one, set_to_index=index-1)

        if event == "UP_TWO" and remove_option_two in selected_models_two:
            index = selected_menu_two.get_indexes()[0]
            new_index = check_index(index - 1, selected_models_two)

            # Switching the values in each index
            selected_models_two[new_index], selected_models_two[index] = \
                selected_models_two[index], selected_models_two[new_index]
            selected_menu_two.update(values=selected_models_two, set_to_index=new_index)

        if event == "DOWN_ONE" and remove_option_one in selected_models_one:
            index = selected_models_one.index(remove_option_one)
            new_index = check_index(index + 1, selected_models_one)

            # Switching the values in each index
            selected_models_one[new_index], selected_models_one[index] = \
                selected_models_one[index], selected_models_one[new_index]
            selected_menu_one.update(values=selected_models_one, set_to_index=new_index)

        if event == "DOWN_TWO" and remove_option_two in selected_models_two:
            index = selected_menu_two.get_indexes()[0]
            new_index = check_index(index + 1, selected_models_two)

            # Switching the values in each index
            selected_models_two[new_index], selected_models_two[index] = \
                selected_models_two[index], selected_models_two[new_index]
            selected_menu_two.update(values=selected_models_two, set_to_index=new_index)

        if event == "SWAP":
            error_text.update(value="")
            success_text.update(value="")
            if len(selected_models_two) != len(selected_models_one) or 0 == len(selected_models_one):
                error_text.update(value="Error: Not enough models selected, double check selections!")
            else:
                selections_valid = True
                for i in range(0, len(selected_models_one)):
                    # Check to make sure each new model is smaller than the source model #
                    if is_model_smaller(os.path.join("models", selected_models_one[i]),
                                        os.path.join("models", selected_models_two[i])):
                        error_text.update(
                            value="Error: {} is larger than {}, cannot be swapped!".format(selected_models_two[i],
                                                                                           selected_models_one[i]))
                        selections_valid = False
                if selections_valid:
                    # If event gets to this point, then all checks are satisfied and swap can begin. #
                    replace_models(files, selected_models_one, selected_models_two)
                    success_text.update(value="Models Successfully Swapped!")

    window.close()


if __name__ == "__main__":
    main()
