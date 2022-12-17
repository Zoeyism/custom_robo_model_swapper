import os
import sys
import PySimpleGUI as GUI


def open_sfd(file_name):
    # Opens an SFD file and returns the data as a Byte Array.
    #
    # Opens a .BIN file and converts file data into a
    #   byte array, and returns it.

    try:
        file = open(file_name, "rb")
    except FileNotFoundError:
        file = None
    # SFD (StudioFake Data) files start with 4 bytes: SFD, and a space.
    file_data = file.read()
    file.close()

    # if not file_data.startswith(b"SFD"):
    # print("Error: File is not an SFD file.")
    # file_data = None

    return file_data


def get_uint32(byte_list, index=0):
    # Takes a list of bytes, the index you wish to start at, and then reads
    # the 4 bytes from your starting index onward in Big Endian format.
    try:
        value = int.from_bytes(byte_list[index:(index + 4)], 'big')
    except IndexError:
        value = None
    return value


def print_object_locations(file_data):
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
    # Checks if second model is smaller than (or = to) first model;
    # Returns bool based on that check.

    size_one = os.path.getsize(model_one)
    size_two = os.path.getsize(model_two)

    if size_one >= size_two:
        boolean = True
    else:
        boolean = False

    return boolean


def get_file_names(directory="models"):
    # Returns all files in models folder, as list of strings.

    all_files = []

    for entry in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, entry)):
            all_files.append(entry)

    all_files.sort()

    return all_files


def write_bytes_to_file(byte_array, name_of_file, file_type=".BIN"):
    # Writes file data to the name of the file, but in the result_files folder.
    # If the file already exists in that folder, the file name is appended with
    # (1) or a higher number until it is a new file name.
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
        model_num = len(target_names)
        if model_num > len(new_names):
            model_num = len(new_names)

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

                print(target_index)

                new_file[target_index:(target_index + len(new_model))] = new_model[:]

                gap = target_length - len(new_model)

                gap_filler = bytearray(gap)

                new_file[(target_index + len(new_model)):(target_index + target_length)] = gap_filler[:]

        # Writes the data of the new file to the result_files folder
        write_bytes_to_file(new_file, name_of_file)


def find_texture_data(model_name, directory="models", robo=False, weapon=False):
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

    # Image end index
    if not weapon:
        image_end_index = get_uint32(model, 8) + 64
        #image_end_index = get_uint32(model, 8) + 48  # For Pods, is the exact image_end_index, not a pointer
    else:
        image_end_index = get_uint32(model, 24) + 36
    image_end_index = get_uint32(model, image_end_index) + 64

    image_data = model[image_index:image_end_index]

    new_bin_data = bytearray(bytes.fromhex('00 20 AF 30 00 00 00 01 00 00 00 0C 00 00 00 14 00 00 00 00'))
    new_bin_data += length
    new_bin_data += width
    new_bin_data += encoding_bytes
    new_bin_data += bytes.fromhex('00 00 00 40 00 00 00 00 00 00 00 00 00 00 00 01'
                                  '00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
    new_bin_data += image_data[:]

    write_bytes_to_file(new_bin_data, (model_name[:-4] + " Texture.tpl"), ".tpl")


def split_sfd(file_name, directory="source_files"):
    file_data = open_sfd(os.path.join(directory, file_name))

    objects = get_uint32(file_data, 4)

    for i in range(0, objects):
        index = get_uint32(file_data, (8 + (i * 8)))
        length = get_uint32(file_data, (12 + (i * 8)))

        write_bytes_to_file(file_data[index:(index + length)], "Object " + str(i) + ".BIN")


def main():
    files = ["rpg_t_models.BIN", "rpg_f_models.BIN"]
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

    column_one = [[box_header_one], [char_menu_one], [add_button_one, remove_button_one], [selected_menu_one]]
    column_two = [[box_header_two], [char_menu_two], [add_button_two, remove_button_two], [selected_menu_two]]

    window = GUI.Window(
        title="Custom Robo Model Swapper",
        layout=[
            [
                GUI.Column(column_one),
                GUI.VSeparator(),
                GUI.Column(column_two)
            ]
        ],
        margins=(400, 200))

    add_option_one, add_option_two, remove_option_one, remove_option_two = "", "", "", ""

    while True:  # WINDOW LOOP #
        event, values = window.read()
        if event == GUI.WIN_CLOSED:
            break

        if event == "CHAR_MENU_ONE":
            add_option_one = values["CHAR_MENU_ONE"][0]  # File name that was selected

        if event == "CHAR_MENU_TWO":
            add_option_two = values["CHAR_MENU_TWO"][0]

        if event == "SLCT_MENU_ONE":
            remove_option_one = values["SLCT_MENU_ONE"][0]

        if event == "SLCT_MENU_TWO":
            remove_option_two = values["SLCT_MENU_TWO"][0]

        if event == "ADD_ONE" and add_option_one in model_options_one:
            model_options_one.remove(add_option_one)
            selected_models_one.append(add_option_one)
            char_menu_one.update(values=model_options_one)
            selected_menu_one.update(values=selected_models_one)

        if event == "ADD_TWO" and add_option_two in model_options_two:
            model_options_two.remove(add_option_two)
            selected_models_two.append(add_option_two)
            char_menu_two.update(values=model_options_two)
            selected_menu_two.update(values=selected_models_two)

        if event == "REM_ONE" and remove_option_one in selected_models_one:
            selected_models_one.remove(remove_option_one)
            model_options_one.append(remove_option_one)
            model_options_one.sort()
            char_menu_one.update(values=model_options_one)
            selected_menu_one.update(values=selected_models_one)

        if event == "REM_TWO" and remove_option_two in selected_models_two:
            selected_models_two.remove(remove_option_two)
            model_options_two.append(remove_option_two)
            model_options_two.sort()
            char_menu_two.update(values=model_options_two)
            selected_menu_two.update(values=selected_models_two)


    window.close()


if __name__ == "__main__":
    main()
