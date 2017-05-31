import sys
import json

from PySide.QtGui import *
import PySide.QtCore as Core

import DEFAULTS


# converts a tuple that holds rgb values into
# its respective hex value
def convert_color_to_hex(color):
    if type(color) == tuple:
        value = "#"
        for i in range(0, 3):
            value += str(hex(color[i]))[2:]
        return value
    else:
        raise TypeError("Color provided has to be a tuple.. got '{}' instead".format(str(type(color))))


# represents the canvas scene
class Scene(QGraphicsScene):
    def __init__(self, designer):
        super(Scene, self).__init__()

        with open("platforms.json") as filename:
            self.data = json.load(filename)

        # General attributes used by all tools
        self.designer = designer
        self.designer.canvas.setScene(self)
        self.outlinepen = QPen(QColor(convert_color_to_hex(DEFAULTS.BLACK)))
        self.design = None

        # Used by the placer tool
        self.snap_on = True
        self.snap_strength = 10
        self.shadow = None
        self.placer_selected_platform = None

        # Used by the selector tool
        self.hovered_over_platform = None
        self.selector_selected_platform = None
        self.selector_old_colors = {}  # stores the old color of the platform after the mouse is no longer on it
        self.selector_SELECTED_COLOR = '#990000'
        self.mouse_pressed = False
        self.prev_mouse_pos = None

        # General Initialization
        self.reset_design()
        self.initialize_scene()

    # function does the math that snaps a coordinate to the grid
    def snap_to_nearest(self, number):
        difference = number % self.snap_strength
        if difference <= 2:
            return number - difference
        else:
            return number + (self.snap_strength - difference)

    # takes in an x and a y which is given by a mouse event and
    # returns the new "snapped to" coordinates
    def get_snap_coordinates(self, x, y):

        if self.snap_on:
            x = self.snap_to_nearest(x)
            y = self.snap_to_nearest(y)

        return x, y

    # takes in an x and a y and returns a QPointF
    def return_pos(self, x, y):
        return Core.QPointF(x, y)

    # resets the dictionary that holds all of information about the design
    def reset_design(self):

        self.design = self.create_initial_design()

    def initialize_json_design(self):

        design = {
            "platforms": [],
            "rules": {}
        }

        return design

    def create_initial_design(self):
        default_design = self.initialize_json_design()
        self.add_initial_rules_to_design(default_design)
        self.add_platform_to_design(default_design,
                                    "FloorPlatform",
                                    0, DEFAULTS.world_size[1] - DEFAULTS.floor_height,
                                    default_design["rules"]["world-size"][0], default_design["rules"]["world-size"][1],
                                    DEFAULTS.platform_color)
        return default_design

    def add_initial_rules_to_design(self, design):

        design["rules"].update(
            {
                "background-color": DEFAULTS.SKY_BLUE,
                "world-size": DEFAULTS.world_size
            }
        )

    def add_rules_to_design(self, design, rules):

        design["rules"].update(rules)

    # removes all items from the list of canvas items and resets the dictionary
    # that holds the current design
    def remove_all_items(self):

        for item in self.items():
            self.removeItem(item)

        self.design = self.initialize_json_design()

    # takes in a dictionary filled with platform data and adds all of them
    # to the list of items being drawn by the canvas and also adding them
    # to the dictionary holding the data of the current design
    # this is useful for opening pre-existing files to edit them
    def add_all_items(self, new_data):

        self.add_rules_to_design(self.design, new_data["rules"])
        self.add_background()

        for platform in new_data["platforms"]:

            self.add_platform(platform["x"],
                              platform["y"],
                              platform["width"],
                              platform["height"],
                              convert_color_to_hex(tuple(platform["color"])))
            self.add_platform_to_design(self.design, platform["type"],
                                        platform["x"], platform["y"],
                                        platform["width"], platform["height"],
                                        platform["color"])

    # function that adds the default floor as to speed up the designing process
    def add_default_floor(self):

        # adding the default floor
        self.floor = QGraphicsRectItem(0, 0,
                                       self.design["rules"]["world-size"][0],
                                       self.design["rules"]["world-size"][1])
        self.floor.setPos(0, DEFAULTS.world_size[1] - DEFAULTS.floor_height)
        self.floor.setPen(self.outlinepen)
        self.floor.setBrush(QBrush(QColor(convert_color_to_hex(tuple(DEFAULTS.platform_color)))))
        self.addItem(self.floor)

    # adds the background to the list of items being drawn by the canvas
    def add_background(self):

        # sets the scene rect to the default world size, this should be changeable
        self.setSceneRect(0, 0, self.design["rules"]["world-size"][0], self.design["rules"]["world-size"][1])

        # add the background, this color will be easily changed
        self.background = QGraphicsRectItem(0, 0, self.design["rules"]["world-size"][0],
                                            self.design["rules"]["world-size"][1])
        self.background.setPen(self.outlinepen)
        self.background.setBrush(QBrush(QColor(convert_color_to_hex(tuple(self.design["rules"]["background-color"])))))
        self.addItem(self.background)

    def remove_floor(self):

        self.removeItem(self.floor)
        self.remove_floor_from_design()

    def remove_floor_from_design(self):

        platform_to_remove = None
        for platform in self.design["platforms"]:
            if platform["type"] == "FloorPlatform":
                platform_to_remove = platform
                break

        self.design["platforms"].remove(platform_to_remove)

    # initializes the canvas scene
    def initialize_scene(self):

        self.installEventFilter(self)

        self.add_background()
        self.add_default_floor()

    # function that is used to add the platform and it's data to the list of
    # items that is currently being displayed by the canvas scene
    def add_platform(self, x, y, width, height, color, return_platform=False):

        platform = QGraphicsRectItem(0, 0, width, height)
        platform.setPos(x, y)

        platform.setPen(self.outlinepen)
        platform.setBrush(QBrush(QColor(color)))
        self.addItem(platform)

        if return_platform:
            return platform
        else:
            return None

    # used to add the platform to the canvas scene when the mouse button is pressed
    def add_platform_to_scene(self, event, return_platform=False):

        if self.placer_selected_platform is None:
            return

        try:
            attributes = self.data["types"][self.placer_selected_platform]
        except KeyError:
            try:
                attributes = {
                    "width": int(self.designer.entered_width.text()),
                    "height": int(self.designer.entered_height.text()),
                    "color": DEFAULTS.platform_color
                }
            except ValueError:
                return

        pos = event.scenePos()

        x, y = self.get_snap_coordinates(int(pos.x()), int(pos.y()))

        platform = self.add_platform(x,
                                     y,
                                     attributes["width"],
                                     attributes["height"],
                                     convert_color_to_hex(tuple(attributes["color"])),
                                     return_platform=return_platform)

        if return_platform:
            return platform

    # handles the data and adds the platform that was placed to the
    # dictionary containing all information about the level that is
    # being currently built so that it can be exported later
    def add_platform_to_design(self, design, platform_type, x, y, width, height, color):

        x, y = self.get_snap_coordinates(x, y)

        design["platforms"].append(
            {
                "type": platform_type,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "color": color
            }
        )

    # used by the placer tool to remove the last drawn platform
    # if the user did not decide to place it there
    def remove_shadow(self):
        if self.shadow is not None:
            self.removeItem(self.shadow)
            self.shadow = None

    # when a platform is dragged by the selector, this function will look for
    # the old platform in the current design and change its coordinates to
    # where the platform is currently placed on the canvas scene
    def adjust_selected_platform_coordinates(self, old_x, old_y):
        pos = self.selector_selected_platform.pos()

        for platform in self.design["platforms"]:
            if old_x == platform["x"] and old_y == platform["y"]:
                platform["x"] = pos.x()
                platform["y"] = pos.y()
                break

    # depending on what tool is selected the mouse move event function
    # will behave differently, so this is a series of conditionals looking
    # for which tool is being used and calling the appropriate behavior
    def mouseMoveEvent(self, event):
        if self.designer.tool == "Placer":
            self.mouse_move_placer_event(event)
        elif self.designer.tool == "Selector":
            self.mouse_move_selector_event(event)

    # depending on what tool is selected the mouse press event function
    # will behave differently, so this is a series of conditionals looking
    # for which tool is being used and calling the appropriate behavior
    def mousePressEvent(self, event):
        if self.designer.tool == "Placer":
            self.mouse_press_placer_event(event)
        elif self.designer.tool == "Selector":
            self.mouse_press_selector_event(event)
            self.mouse_pressed = True
            x, y = self.get_snap_coordinates(event.scenePos().x(), event.scenePos().y())
            self.prev_mouse_pos = self.return_pos(x, y)

    # waits for a mouse release event and applies the appropriate behavior based on
    # what tool is currently selected
    def mouseReleaseEvent(self, event):
        if self.designer.tool == "Selector":
            self.mouse_pressed = False
            self.prev_mouse_pos = None

    # mouse move event behavior for the placer tool
    def mouse_move_placer_event(self, event):
        self.remove_shadow()

        platform = self.add_platform_to_scene(event, return_platform=True)
        if platform is not None:
            platform.setOpacity(0.5)

        self.shadow = platform

    # mouse press event behavior for the placer tool
    def mouse_press_placer_event(self, event):
        if self.placer_selected_platform is not None:
            self.add_platform_to_scene(event)

            try:
                platform = self.data["types"][self.placer_selected_platform]
            except KeyError:
                try:
                    platform = {
                        "width": int(self.designer.entered_width.text()),
                        "height": int(self.designer.entered_height.text()),
                        "color": DEFAULTS.platform_color
                    }
                except ValueError:
                    return

            self.add_platform_to_design(self.design,
                                        self.placer_selected_platform,
                                        int(event.scenePos().x()),
                                        int(event.scenePos().y()),
                                        platform["width"],
                                        platform["height"],
                                        platform["color"])

    # restoring color to any potential platforms that the user hovered over but
    # is no longer hovering over
    def restore_color_to_other_platforms(self, platform):

        color_restore_conditions = [platform is not self.hovered_over_platform,
                                    self.hovered_over_platform is not None]

        if False not in color_restore_conditions:
            if not self.selector_old_colors[self.hovered_over_platform]["selected"]:
                color = self.selector_old_colors[self.hovered_over_platform]["color"]
                self.hovered_over_platform.setBrush(QBrush(QColor(color)))
                self.hovered_over_platform.setOpacity(1)
                del self.selector_old_colors[self.hovered_over_platform]
                self.hovered_over_platform = None

    # checking to see if the user is hovering over a new platform and then setting
    # it's color to red and its opacity to 0.5
    # function also keeps track of the platforms old color
    # so that it may be restored later
    def apply_hover_effect_onto_platform(self, platform):

        hover_action_conditions = [platform is not self.background,
                                   platform is not self.hovered_over_platform,
                                   platform is not self.selector_selected_platform]

        if False not in hover_action_conditions:
            self.hovered_over_platform = platform
            self.selector_old_colors.update(
                {
                    platform: {
                        "selected": False,
                        "color": convert_color_to_hex(platform.brush().color().getRgb())
                    }
                }
            )
            platform.setBrush(QBrush(QColor(self.selector_SELECTED_COLOR)))
            platform.setOpacity(0.5)

    # mouse move event behavior for the selector tool
    def mouse_move_selector_event(self, event):
        if not self.mouse_pressed:
            pos = event.scenePos()

            platform = self.itemAt(pos)

            self.restore_color_to_other_platforms(platform)
            self.apply_hover_effect_onto_platform(platform)
        else:
            self.drag_selected_platform(event)

    # allows you to drag the platform that was just selected to a new position
    def drag_selected_platform(self, event):
        if self.selector_selected_platform is not None:
            pos = event.scenePos()
            x, y = self.get_snap_coordinates(pos.x(), pos.y())

            old_x = self.selector_selected_platform.x()
            old_y = self.selector_selected_platform.y()

            mouse_displacement_x = x - self.prev_mouse_pos.x()
            mouse_displacement_y = y - self.prev_mouse_pos.y()

            self.selector_selected_platform.setPos(self.selector_selected_platform.x() + mouse_displacement_x,
                                                   self.selector_selected_platform.y() + mouse_displacement_y)

            self.adjust_selected_platform_coordinates(old_x, old_y)

            self.prev_mouse_pos = Core.QPointF(x, y)

    # deselects the selected platform by changing its color and opacity
    # back to normal and setting selected platform back to None
    # the delete action also gets disabled
    def deselect_selected_platform(self):
        color = self.selector_old_colors[self.selector_selected_platform]["color"]
        self.selector_selected_platform.setBrush(QBrush(QColor(color)))
        self.selector_selected_platform.setOpacity(1)
        del self.selector_old_colors[self.selector_selected_platform]
        self.selector_selected_platform = None
        self.designer.toggle_delete_action(False)

    # select the platform that the mouse is currently hovering over by
    # increasing it's opacity and keeping it that color until its deselected
    # the delete action also gets enabled
    def select_hovered_over_platform(self):
        self.selector_selected_platform = self.hovered_over_platform
        self.selector_selected_platform.setOpacity(0.65)
        self.selector_old_colors[self.selector_selected_platform]["selected"] = True
        self.hovered_over_platform = None
        self.designer.toggle_delete_action(True)

    # mouse press event behavior for the selector tool
    def mouse_press_selector_event(self, event):

        # deselect the last thing that was selected and restore its color
        if self.selector_selected_platform is not None:
            self.deselect_selected_platform()

        # if the mouse is hovering over a platform, select that platform
        if self.hovered_over_platform is not None:
            self.select_hovered_over_platform()

    # this is simply looking to see if the mouse has left the canvas
    # in order to remove any potential "shadows" or platforms that
    # are drawn on the canvas but were not actually placed anywhere
    def eventFilter(self, watched, event):
        if event.type() == Core.QEvent.Leave:
            if self.designer.tool == "Placer":
                self.remove_shadow()
            elif self.designer.tool == "Selector":
                if self.hovered_over_platform is not None:
                    self.select_hovered_over_platform()
                    self.deselect_selected_platform()
            return True
        else:
            return False


# represents the main GUI window
class Designer(QWidget):
    def __init__(self, application):
        super(Designer, self).__init__()

        with open("platforms.json") as filename:
            self.data = json.load(filename)

        self.application = application
        self.filename = None
        self.canvas = None
        self.canvas_scene = None

        self.selection = []
        self.tool = "Placer"
        self.initialize_interface()

    # center the GUI on the desktop when it is first launched
    def center_screen(self):
        # get the geometry features of the desktop
        desktop_geometry = self.application.desktop().screenGeometry()
        # calculate new x and y values
        x = (desktop_geometry.width() - self.width()) / 2
        y = (desktop_geometry.height() - self.height()) / 2
        # move the main window to those values
        self.move(x, y)

    # export the current canvas design into a file with the passed in filename
    def export_level(self, filename):
        with open(filename, "w") as name:
            json.dump(self.canvas_scene.design, name, indent=4)

    # toggle the button selection, this function treats regular buttons like radio buttons
    def toggle_selection(self, button):
        # since a button has just been press, change any button that is
        # flat back to its default state
        for select in self.selection:
            if select.isFlat():
                select.setFlat(False)

        # set the button that was pressed to the flat state
        button.setFlat(True)

        # store the platform text of the selected platform type
        self.canvas_scene.placer_selected_platform = button.text()

        # keep the width and height entries disabled unless needed
        custom_list = ["CustomPlatform", "FloorPlatform"]
        self.entered_width.setEnabled(button.text() in custom_list)
        self.entered_height.setEnabled(button.text() in custom_list)




    # listens for the user to close the GUI and checks whether a save warning message should be applied
    def closeEvent(self, event):

        response = self.apply_save_warning_message()

        if response == QMessageBox.Cancel:
            event.ignore()
        else:
            event.accept()

    def add_button_to_box_layout(self, text, box_layout):
        button = QPushButton(text)
        button.setStyleSheet("padding: 20px;")
        # when the button is clicked, run a function that
        # takes in that button and toggles it appropriately
        button.clicked.connect(
            lambda b=button: self.toggle_selection(b)
        )
        # throw the button into the selection list to have
        # a reference to all generated buttons
        self.selection.append(button)
        box_layout.addWidget(button)

    # initializes the left frame which is composed of the prebuilt platform options
    def initialize_left_frame(self):

        # custom group box creation
        custom_section = QGroupBox()
        custom_button_layout = QVBoxLayout()
        self.add_button_to_box_layout("CustomPlatform", custom_button_layout)
        self.add_button_to_box_layout("FloorPlatform", custom_button_layout)
        custom_section.setLayout(custom_button_layout)

        # initialize a group box to place the platform buttons
        self.left_box = QGroupBox()
        # create a vertical box layout to layout the buttons in
        # the group box vertically and set it to the group box
        form = QVBoxLayout()
        self.left_box.setLayout(form)

        # for each type of platform, create a button and add it
        # to the vertical box layout
        for key in self.data["types"].keys():
            self.add_button_to_box_layout(str(key), form)

        # create a scrollable area
        scroll_area = QScrollArea()
        # set the scrollable area to be the group box
        scroll_area.setWidget(self.left_box)

        # getting the width of the respective scroll bar in
        # order to set the group box dimensions properly
        bar_width = scroll_area.verticalScrollBar().width()

        frame_height = DEFAULTS.screen_size[1]
        frame_width = self.left_box.width() + (bar_width / 2.22)

        # giving the left frame a fixed size so that it is not resizable
        # main goal is to never have a horizontal scrollbar and for the
        # group box to maintain a certain shape regardless of how many
        # platforms currently exist
        self.left_frame.setFixedSize(frame_width, frame_height)

        # defining a vertical layout for the scroll area since the scroll
        # area at this point contains the box widget
        layout = QVBoxLayout()

        custom_area = QFrame()
        custom_layout = QVBoxLayout()

        self.custom_entry = QWidget()
        entry_layout = QHBoxLayout()

        entry_layout.addWidget(QLabel("W: "))
        self.entered_width = QLineEdit()
        self.entered_width.setEnabled(False)
        entry_layout.addWidget(self.entered_width)

        entry_layout.addWidget(QLabel("H: "))
        self.entered_height = QLineEdit()
        self.entered_height.setEnabled(False)
        entry_layout.addWidget(self.entered_height)

        self.custom_entry.setLayout(entry_layout)

        custom_layout.addWidget(self.custom_entry)
        custom_layout.addWidget(custom_section)

        custom_area.setLayout(custom_layout)

        layout.addWidget(custom_area)
        layout.addWidget(scroll_area)

        # set the left frames layout to the vertical layout that contains
        # the scrollable area and all of it's contents
        self.left_frame.setLayout(layout)

    # initialize the canvas scene with all of its elements
    def initialize_canvas(self):

        self.canvas = QGraphicsView()

        bar_width = self.canvas.verticalScrollBar().height()
        bar_height = self.canvas.horizontalScrollBar().height()

        canvas_width = DEFAULTS.screen_size[0] + (bar_width / 1.25)
        canvas_height = DEFAULTS.screen_size[1] + (bar_height / 1.25)

        self.canvas.setFixedSize(canvas_width, canvas_height)
        self.canvas.setMouseTracking(True)
        self.canvas_scene = Scene(self)

        self.middle_layout.addWidget(self.canvas)

    # applies the necessary QFileDialog depending on the circumstances of the current design
    # and any loaded files. This function will return the response that the user chose so other
    # functions can choose how to act after the message box independently. This function will
    # return None if no warning message was necessary to appear
    def apply_save_warning_message(self):

        msgBox = QMessageBox()
        msgBox.setText("This level as been modified.")
        msgBox.setInformativeText("Do you want to save your changes?")
        msgBox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Save)

        default_design = self.canvas_scene.create_initial_design()
        if self.filename is None and not self.canvas_scene.design == default_design:
            ret = msgBox.exec_()

            # open the save file dialog and then reset the scene
            if ret == QMessageBox.Save:
                self.save_as()

            return ret

        elif self.filename is None:
            return None

        else:
            with open(self.filename) as filename:
                data = json.load(filename)

            file_data, designer_data = json.dumps(data, sort_keys=True),\
                                       json.dumps(self.canvas_scene.design, sort_keys=True)

            if not file_data == designer_data:

                ret = msgBox.exec_()

                if ret == QMessageBox.Save:
                    self.save()

                return ret
            else:
                return None

    # the new file action, this will display the save warning message if it is appropriate
    # and then will proceed to reset the canvas scene and design if it should
    def new_file(self):
        response = self.apply_save_warning_message()

        # if the user did not cancel then reset the scene
        if not response == QMessageBox.Cancel:
            self.canvas_scene = Scene(self)
            self.filename = None
            self.canvas_scene.reset_design()
            self.canvas_scene.add_default_floor()
            self.setWindowTitle("Level Designer")
        else:
            pass

    # this lets the user open an existing file
    def open_file(self):

        response = self.apply_save_warning_message()
        if response == QMessageBox.Cancel:
            return

        filename_attributes = QFileDialog.getOpenFileName(
            self, "Open File", "../levels", selectedFilter="*.stg"
        )

        if filename_attributes[0] == "":
            return

        self.filename = filename_attributes[0]
        self.setWindowTitle("Level Designer - {}".format(self.filename))

        with open(self.filename) as name:
            new_level_data = json.load(name)

        self.canvas_scene.remove_all_items()
        self.canvas_scene.add_all_items(new_level_data)

    # saves the current file
    def save(self):
        if self.filename is None:
            self.save_as()
        else:
            self.export_level(self.filename)

    # opens the save as dialog to let the user save their design
    def save_as(self):

        filename_attributes = QFileDialog.getSaveFileName(
            self, "Save File", "../levels", selectedFilter="*.stg"
        )

        if filename_attributes[0] == "":
            return

        self.filename = filename_attributes[0]
        self.export_level(self.filename)
        self.setWindowTitle("Level Designer - {}".format(self.filename))

    # toggles snap on and off if the user clicks on 'snap on' or 'snap off' in the edit menu
    def toggle_snap(self, action):

        self.canvas_scene.snap_on = not self.canvas_scene.snap_on
        action.setChecked(self.canvas_scene.snap_on)

    # applies the newly selected snap if the user pressed "apply" on the snap adjustment window
    def snap_adjustment_window_allow_action(self, entry):

        self.canvas_scene.snap_strength = int(entry.text())
        self.snap_pop_up_window.close()

    # opens up the snap adjustment window to allow the user to modify the snap strength
    def snap_adjustment_window(self):

        self.snap_pop_up_window = QWidget()
        self.snap_pop_up_window.setWindowTitle("Snap Adjustment")

        overall_layout = QVBoxLayout()

        self.snap_pop_up_window.setLayout(overall_layout)

        display_layout = QHBoxLayout()
        display_frame = QWidget()
        display_frame.setLayout(display_layout)

        label = QLabel('Strength')
        entry = QLineEdit()
        entry.setText(str(self.canvas_scene.snap_strength))
        entry.setAlignment(Core.Qt.AlignHCenter)

        display_layout.addWidget(label)
        display_layout.addWidget(entry)

        action_layout = QHBoxLayout()
        action_frame = QWidget()
        action_frame.setLayout(action_layout)

        apply_button = QPushButton()
        apply_button.setText("Apply")
        apply_button.clicked.connect(lambda text=entry: self.snap_adjustment_window_allow_action(entry))

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self.snap_pop_up_window.close)

        action_layout.addWidget(apply_button)
        action_layout.addWidget(cancel_button)

        overall_layout.addWidget(display_frame)
        overall_layout.addWidget(action_frame)

        self.snap_pop_up_window.show()

    def world_size_adjustment_window(self):

        self.world_size_pop_up_window = QWidget()
        self.world_size_pop_up_window.setWindowTitle("World Size Adjustment")

        overall_layout = QVBoxLayout()

        self.world_size_pop_up_window.setLayout(overall_layout)

        header_layout = QHBoxLayout()
        header_frame = QWidget()
        header_frame.setLayout(header_layout)

        main_label = QLabel("World Size")
        header_layout.addWidget(main_label)

        bottom_layout = QHBoxLayout()
        bottom_frame = QWidget()
        bottom_frame.setLayout(bottom_layout)

        bottom_left_layout = QVBoxLayout()
        bottom_left_frame = QWidget()
        bottom_left_frame.setLayout(bottom_left_layout)

        x_row_layout = QHBoxLayout()
        x_row_frame = QWidget()
        x_row_frame.setLayout(x_row_layout)

        x_label = QLabel("x: ")
        x_row_layout.addWidget(x_label)

        x_line_edit = QLineEdit()
        x_line_edit.setText(str(self.canvas_scene.design["rules"]["world-size"][0]))
        x_line_edit.setAlignment(Core.Qt.AlignHCenter)
        x_row_layout.addWidget(x_line_edit)

        bottom_left_layout.addWidget(x_row_frame)

        y_row_layout = QHBoxLayout()
        y_row_frame = QWidget()
        y_row_frame.setLayout(y_row_layout)

        y_label = QLabel("y: ")
        y_row_layout.addWidget(y_label)

        y_line_edit = QLineEdit()
        y_line_edit.setText(str(self.canvas_scene.design["rules"]["world-size"][1]))
        y_line_edit.setAlignment(Core.Qt.AlignHCenter)
        y_row_layout.addWidget(y_line_edit)

        bottom_left_layout.addWidget(y_row_frame)

        bottom_layout.addWidget(bottom_left_frame)

        resize_floor_check_button = QCheckBox("Resize Floor")
        resize_floor_check_button.setChecked(True)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda x=x_line_edit,
                                            y=y_line_edit,
                                            resize=resize_floor_check_button:
                                     self.adjust_world_size(x, y, resize))

        bottom_layout.addWidget(apply_button)

        overall_layout.addWidget(header_frame)
        overall_layout.addWidget(bottom_frame)
        overall_layout.addWidget(resize_floor_check_button)

        self.world_size_pop_up_window.show()

    def adjust_world_size(self, x_entry, y_entry, resize):

        self.canvas_scene.design["rules"]["world-size"] = [int(x_entry.text()), int(y_entry.text())]
        x, y, width, height = 0, 0, self.canvas_scene.design["rules"]["world-size"][0],\
                                    self.canvas_scene.design["rules"]["world-size"][1]

        self.canvas_scene.setSceneRect(x, y, width, height)
        self.canvas_scene.background.setRect(x, y, width, height)

        if resize.isChecked():
            self.canvas_scene.remove_floor()
            self.canvas_scene.add_default_floor()
            self.canvas_scene.add_platform_to_design(
                self.canvas_scene.design,
                "FloorPlatform",
                0, self.canvas_scene.design["rules"]["world-size"][1] - DEFAULTS.floor_height,
                width, height, DEFAULTS.platform_color
            )
        self.world_size_pop_up_window.close()

    def background_color_window(self):

        color = QColorDialog.getColor()
        if color == QColor():
            return
        else:
            self.canvas_scene.background.setBrush(QBrush(color))
            color_rgb = [color.red(), color.green(), color.blue()]
            self.canvas_scene.design["rules"]["background-color"] = color_rgb

    # deletes the platform that is selected by the selector from the canvas design
    def delete_selected_platform_from_design(self):

        pos = self.canvas_scene.selector_selected_platform.pos()

        item_to_delete = None
        for platform in self.canvas_scene.design["platforms"]:
            if pos.x() == platform["x"] and pos.y() == platform["y"]:
                item_to_delete = platform
                break

        self.canvas_scene.design["platforms"].remove(item_to_delete)

    # deletes the platform that is selected by the selector from the canvas scene and design
    def delete_selected_platform(self):

        self.canvas_scene.removeItem(self.canvas_scene.selector_selected_platform)
        self.delete_selected_platform_from_design()

    # enables the delete action only if a platform is selected
    def toggle_delete_action(self, enable_or_disable):

        for action in self.edit_menu.actions():
            if action.text() == "Delete":
                action.setEnabled(enable_or_disable)
                break

    # initializes the file menu and all of its actions
    def initialize_file_menu(self):

        self.file_menu = self.main_menu.addMenu('&File')

        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_file)
        new_action.setShortcut('ctrl+n')

        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_file)
        open_action.setShortcut('ctrl+o')

        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save)
        save_action.setShortcut('ctrl+s')

        save_as_action = QAction('Save As', self)
        save_as_action.triggered.connect(self.save_as)
        save_as_action.setShortcut('ctrl+shift+s')

        self.file_menu.addAction(new_action)
        self.file_menu.addAction(open_action)
        self.file_menu.addAction(save_action)
        self.file_menu.addAction(save_as_action)

    # initializes the edit menu and all of its actions
    def initialize_edit_menu(self):

        self.edit_menu = self.main_menu.addMenu('&Edit')

        snap_toggle = QAction('Snap On', self, checkable=True)
        snap_toggle.setChecked(True)
        snap_toggle.triggered.connect(lambda: self.toggle_snap(snap_toggle))

        snap_intensity_adjustment = QAction('Set Snap Strength', self)
        snap_intensity_adjustment.triggered.connect(self.snap_adjustment_window)

        background_color_adjustment = QAction('Change Background Color', self)
        background_color_adjustment.triggered.connect(self.background_color_window)
        background_color_adjustment.setShortcut("Ctrl+Shift+C")

        world_size_adjustment = QAction('Adjust World Size', self)
        world_size_adjustment.triggered.connect(self.world_size_adjustment_window)
        world_size_adjustment.setShortcut("Ctrl+Shift+W")

        delete = QAction('Delete', self)
        delete.triggered.connect(self.delete_selected_platform)
        delete.setShortcut("Ctrl+d")
        delete.setEnabled(False)

        self.edit_menu.addAction(snap_toggle)
        self.edit_menu.addAction(snap_intensity_adjustment)
        self.edit_menu.addAction(background_color_adjustment)
        self.edit_menu.addAction(world_size_adjustment)
        self.edit_menu.addAction(delete)

    def add_to_platforms_window(self):
        pass

    # initializes the config menu and all of its actions
    def initialize_config_menu(self):

        self.config_menu = self.main_menu.addMenu('&Config.')

        add_to_platforms = QAction('Add To Existing Platforms', self)
        add_to_platforms.triggered.connect(lambda: self.add_to_platforms_window)

        self.config_menu.addAction(add_to_platforms)

    # initializes the menu bar and adds it to the GUI
    def initialize_menubar(self):

        self.main_menu = QMenuBar()

        self.initialize_file_menu()
        self.initialize_edit_menu()
        self.initialize_config_menu()

        self.main_layout.addWidget(self.main_menu)

    # sets the type of tool that is selected, for both designer and the canvas
    def set_tool(self, action_type):

        self.tool = action_type
        self.canvas_scene.tool = action_type

    # toggles the previously selected action to disable it
    def toggle_old_action(self, new_action):

        if self.tool_action is None:
            pass
        else:
            old_action = self.tool_action
            self.tool_action = None
            old_action.trigger()
            self.tool_action = new_action

    # intended to abstract the common things that all
    # triggered actions share
    def toggle_action(self, action, action_type):

        self.toggle_old_action(action)
        if action.isChecked():
            self.set_tool(action_type)

        if action_type == "Placer":
            self.toggle_placer(action)
        elif action_type == "Selector":
            self.toggle_selector(action)

    # if the placer has just been checked, enable the platform list
    # on the left side of the screen, otherwise disable it
    def toggle_placer(self, placer):
        for button in self.selection:
            button.setFlat(False)

        self.canvas_scene.placer_selected_platform = None
        self.left_frame.setEnabled(placer.isChecked())

    # deselects the platform that is selected if it is selected
    def toggle_selector(self, selector):
        if self.canvas_scene.selector_selected_platform is not None:
            self.canvas_scene.deselect_selected_platform()

    # selected the initial tool that should be selected
    def initialize_starting_action(self, action):
        action.setChecked(True)
        self.tool_action = action

    # initializes the toolbar and all of its actions
    def initialize_toolbar(self):

        self.tool_bar = QToolBar()

        placer = QAction(QIcon('images/placer_icon.png'), 'Placer', self, checkable=True)
        placer.triggered.connect(lambda: self.toggle_action(placer, "Placer"))

        selector = QAction(QIcon('images/selector_icon.png'), 'Selector', self, checkable=True)
        selector.triggered.connect(lambda: self.toggle_action(selector, "Selector"))

        self.tool_bar.addAction(placer)
        self.tool_bar.addAction(selector)

        self.initialize_starting_action(placer)

        self.main_layout.addWidget(self.tool_bar)

    # initialize the general GUI
    def initialize_interface(self):

        # Set the window title
        self.setWindowTitle("Level Designer")
        # Set the gui icon
        self.setWindowIcon(QIcon('images/builder.jpg'))

        # create a shortcut that activates the close event
        QShortcut(QKeySequence("ctrl+q"), self, self.close)

        # Creating the layout for the MAIN WINDOW
        self.main_layout = QVBoxLayout()
        # Setting the main window to the main layout
        self.setLayout(self.main_layout)

        # Creating a middle frame that will hold a horizontal layout
        # This will be the container for the list of platforms on the
        # left and the canvas on the right
        self.middle_frame = QWidget()
        self.middle_layout = QHBoxLayout()
        # Setting the middle frames layout to a horizontal layout
        self.middle_frame.setLayout(self.middle_layout)

        # Creating the left frame that will hold a vertical layout
        # This is the specific container for the list of platforms
        # which will be placed into the middle layout
        self.left_frame = QWidget()
        # Initialize the left frame with the buttons
        self.initialize_left_frame()
        # Placing the left frame into the middle layout
        self.middle_layout.addWidget(self.left_frame)

        # initialize canvas
        self.initialize_canvas()

        # Initializing the menu bar
        self.initialize_menubar()

        # Initializing the tool bar
        self.initialize_toolbar()

        # Adding the middle frame into the main layout
        self.main_layout.addWidget(self.middle_frame)

        self.show()
        self.center_screen()

app = QApplication(sys.argv)
designer = Designer(app)
sys.exit(app.exec_())
