import sys
import json

from PySide.QtGui import *
import PySide.QtCore as Core

sys.path.append("../")
import GLOBALS


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

        with open("../platforms.json") as filename:
            self.data = json.load(filename)

        # General attributes used by all tools
        self.designer = designer
        self.designer.canvas.setScene(self)
        self.outlinepen = QPen(QColor(convert_color_to_hex(GLOBALS.BLACK)))
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

    # resets the dictionary that holds all of information about the design
    def reset_design(self):

        self.design = {
            "platforms": []
        }

    # removes all items from the list of canvas items and resets the dictionary
    # that holds the current design
    def remove_all_items(self):

        for item in self.items():
            self.removeItem(item)

        self.reset_design()

    # takes in a dictionary filled with platform data and adds all of them
    # to the list of items being drawn by the canvas and also adding them
    # to the dictionary holding the data of the current design
    # this is useful for opening pre-existing files to edit them
    def add_all_items(self, new_data):

        for platform in new_data["platforms"]:

            width = self.data["types"][platform["type"]]["width"]
            height = self.data["types"][platform["type"]]["height"]
            color = self.data["types"][platform["type"]]["color"]

            self.add_platform(platform["x"],
                              platform["y"],
                              width,
                              height,
                              convert_color_to_hex(tuple(color)))
            self.add_platform_to_design(platform["type"], platform["x"], platform["y"])

    # function that adds the default floor as to speed up the designing process
    def add_default_floor(self):

        # adding the default floor
        floor_platform = self.data["types"]["FloorPlatform"]
        floor = QGraphicsRectItem(0, GLOBALS.world_size[1] - GLOBALS.floor_height, floor_platform["width"],
                                  floor_platform["height"])
        floor.setPen(self.outlinepen)
        floor.setBrush(QBrush(QColor(convert_color_to_hex(tuple(floor_platform["color"])))))
        self.addItem(floor)
        self.add_platform_to_design("FloorPlatform", 0, GLOBALS.world_size[1] - GLOBALS.floor_height)

    # adds the background to the list of items being drawn by the canvas
    def add_background(self):

        # add the background, this color will be easily changed
        self.background = QGraphicsRectItem(0, 0, GLOBALS.world_size[0], GLOBALS.world_size[1])
        self.background.setPen(self.outlinepen)
        self.background.setBrush(QBrush(QColor(convert_color_to_hex(GLOBALS.SKY_BLUE))))
        self.addItem(self.background)

    # initializes the canvas scene
    def initialize_scene(self):

        # sets the scene rect to the default world size, this should be changeable
        self.setSceneRect(0, 0, GLOBALS.world_size[0], GLOBALS.world_size[1])

        self.installEventFilter(self)

        self.add_background()
        self.add_default_floor()

    # function that is used to add the platform and it's data to the list of
    # items that is currently being displayed by the canvas scene
    def add_platform(self, x, y, width, height, color, return_platform=False):

        platform = QGraphicsRectItem(x, y, width, height)

        platform.setPen(self.outlinepen)
        platform.setBrush(QBrush(QColor(color)))
        self.addItem(platform)

        if return_platform:
            return platform
        else:
            return None

    # used to add the platform to the canvas scene when the mouse button is pressed
    def add_platform_to_scene(self, event, return_platform=False):

        try:
            attributes = self.data["types"][self.placer_selected_platform]
        except KeyError:
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
    def add_platform_to_design(self, platform_type, x, y):

        x, y = self.get_snap_coordinates(x, y)

        self.design["platforms"].append(
            {
                "type": platform_type,
                "x": x,
                "y": y
            }
        )

    # used by the placer tool to remove the last drawn platform
    # if the user did not decide to place it there
    def remove_shadow(self):
        if self.shadow is not None:
            self.removeItem(self.shadow)
            self.shadow = None

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
            self.add_platform_to_design(self.placer_selected_platform,
                                        int(event.scenePos().x()),
                                        int(event.scenePos().y()))

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
        pos = event.scenePos()

        platform = self.itemAt(pos)

        self.restore_color_to_other_platforms(platform)
        self.apply_hover_effect_onto_platform(platform)

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
            self.remove_shadow()
            return True
        else:
            return False


# represents the main GUI window
class Designer(QWidget):
    def __init__(self, application):
        super(Designer, self).__init__()

        with open("../platforms.json") as filename:
            self.data = json.load(filename)

        self.application = application
        self.filename = None
        self.canvas = None
        self.canvas_scene = None

        self.selection = []
        self.tool = "Placer"
        self.initialize_interface()

    def center_screen(self):
        # get the geometry features of the desktop
        desktop_geometry = self.application.desktop().screenGeometry()
        # calculate new x and y values
        x = (desktop_geometry.width() - self.width()) / 2
        y = (desktop_geometry.height() - self.height()) / 2
        # move the main window to those values
        self.move(x, y)

    def export_level(self, filename):
        with open(filename, "w") as name:
            json.dump(self.canvas_scene.design, name, indent=4)

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

    def initialize_left_frame(self):

        # initialize a group box to place the platform buttons
        self.left_box = QGroupBox()
        # create a vertical box layout to layout the buttons in
        # the group box vertically and set it to the group box
        form = QVBoxLayout()
        self.left_box.setLayout(form)

        # for each type of platform, create a button and add it
        # to the vertical box layout
        for key in self.data["types"].keys():
            button = QPushButton(str(key))
            button.setStyleSheet("padding: 20px;")
            # when the button is clicked, run a function that
            # takes in that button and toggles it appropriately
            button.clicked.connect(
                lambda b=button: self.toggle_selection(b)
            )
            # throw the button into the selection list to have
            # a reference to all generated buttons
            self.selection.append(button)
            form.addWidget(button)

        # create a scrollable area
        scroll_area = QScrollArea()
        # set the scrollable area to be the group box
        scroll_area.setWidget(self.left_box)

        # getting the width and height of the respective scroll bars in
        # order to set the group box dimensions properly
        bar_width = scroll_area.verticalScrollBar().width()
        bar_height = scroll_area.horizontalScrollBar().height()

        # make sure that the height of the group box does not exceed the
        # height of the canvas to maintain the desired aesthetics
        # This is where the scroll bar will come in handy
        if self.left_box.height() > GLOBALS.size[1]:
            frame_height = GLOBALS.size[1]
        else:
            frame_height = self.left_box.height() + (bar_height / 1.25)

        frame_width = self.left_box.width() + (bar_width / 2.22)

        # giving the left frame a fixed size so that it is not resizable
        # main goal is to never have a horizontal scrollbar and for the
        # group box to maintain a certain shape regardless of how many
        # platforms currently exist
        self.left_frame.setFixedSize(frame_width, frame_height)

        # defining a vertical layout for the scroll area since the scroll
        # area at this point contains the box widget
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)

        # set the left frames layout to the vertical layout that contains
        # the scrollable area and all of it's contents
        self.left_frame.setLayout(layout)

    def initialize_canvas(self):

        self.canvas = QGraphicsView()

        bar_width = self.canvas.verticalScrollBar().height()
        bar_height = self.canvas.horizontalScrollBar().height()

        canvas_width = GLOBALS.size[0] + (bar_width / 1.25)
        canvas_height = GLOBALS.size[1] + (bar_height / 1.25)

        self.canvas.setFixedSize(canvas_width, canvas_height)
        self.canvas.setMouseTracking(True)
        self.canvas_scene = Scene(self)

        self.middle_layout.addWidget(self.canvas)

    def open_file(self):

        filename_attributes = QFileDialog.getOpenFileName(
            self, "Open File", "../levels", selectedFilter="*.stg"
        )
        self.filename = filename_attributes[0]
        self.setWindowTitle("Level Designer - {}".format(self.filename))

        with open(self.filename) as name:
            new_level_data = json.load(name)

        self.canvas_scene.remove_all_items()
        self.canvas_scene.add_background()
        self.canvas_scene.add_all_items(new_level_data)

    def save(self):
        if self.filename is None:
            self.save_as()
        else:
            self.export_level(self.filename)

    def save_as(self):

        filename_attributes = QFileDialog.getSaveFileName(
            self, "Save File", "../levels", selectedFilter="*.stg"
        )
        self.filename = filename_attributes[0]
        self.export_level(self.filename)
        self.setWindowTitle("Level Designer - {}".format(self.filename))

    def toggle_snap(self, action):

        self.canvas_scene.snap_on = not self.canvas_scene.snap_on
        action.setChecked(self.canvas_scene.snap_on)

    def snap_adjustment_window_allow_action(self, entry):

        self.canvas_scene.snap_strength = int(entry.text())
        self.snap_pop_up_window.close()

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

    def delete_selected_platform_from_design(self):

        rect = self.canvas_scene.selector_selected_platform.rect()

        item_to_delete = None
        for platform in self.canvas_scene.design["platforms"]:
            if rect.x() == platform["x"] and rect.y() == platform["y"]:
                item_to_delete = platform
                break

        self.canvas_scene.design["platforms"].remove(item_to_delete)

    def delete_platform(self):

        self.canvas_scene.removeItem(self.canvas_scene.selector_selected_platform)
        self.delete_selected_platform_from_design()

    def toggle_delete_action(self, enable_or_disable):

        for action in self.edit_menu.actions():
            if action.text() == "Delete":
                action.setEnabled(enable_or_disable)
                break

    def initialize_file_menu(self):

        self.file_menu = self.main_menu.addMenu('&File')

        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_file)
        open_action.setShortcut('ctrl+o')

        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save)
        save_action.setShortcut('ctrl+s')

        save_as_action = QAction('Save As', self)
        save_as_action.triggered.connect(self.save_as)
        save_as_action.setShortcut('ctrl+shift+s')

        self.file_menu.addAction(open_action)
        self.file_menu.addAction(save_action)
        self.file_menu.addAction(save_as_action)

    def initialize_edit_menu(self):

        self.edit_menu = self.main_menu.addMenu('&Edit')

        snap_toggle = QAction('Snap On', self, checkable=True)
        snap_toggle.setChecked(True)
        snap_toggle.triggered.connect(lambda: self.toggle_snap(snap_toggle))

        snap_intensity_adjustment = QAction('Set Snap Strength', self)
        snap_intensity_adjustment.triggered.connect(self.snap_adjustment_window)

        delete = QAction('Delete', self)
        delete.triggered.connect(self.delete_platform)
        delete.setShortcut("Ctrl+d")
        delete.setEnabled(False)

        self.edit_menu.addAction(snap_toggle)
        self.edit_menu.addAction(snap_intensity_adjustment)
        self.edit_menu.addAction(delete)

    # initializes the menu bar and adds it to the GUI
    def initialize_menubar(self):

        self.main_menu = QMenuBar()

        self.initialize_file_menu()
        self.initialize_edit_menu()

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
        self.left_box.setEnabled(placer.isChecked())

    # nothing for now
    def toggle_selector(self, selector):
        pass

    def initialize_starting_action(self, action):

        action.setChecked(True)
        self.tool_action = action

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

    def initialize_interface(self):

        # Set the window title
        self.setWindowTitle("Level Designer")
        # Set the gui icon
        self.setWindowIcon(QIcon('images/builder.jpg'))

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
