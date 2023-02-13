# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import pprint
import traceback

import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists
from sgtk.platform.qt import QtGui, QtCore
from tank.platform.qt5 import QtWidgets

HookBaseClass = sgtk.get_hook_baseclass()


class BasicFilePublishPlugin(HookBaseClass):

    @property
    def settings(self):
        settings = super(BasicFilePublishPlugin, self).settings or {}

        # define the settings the custom plugin UI will set
        settings["set_in_review"] = {
            "type": "string",
            "default": None,
            "description": "Whether the task's status will be set to in review."
        }
        settings["reviewer"] = {
            "type": "dict",
            "default": None,
            "description": "The reviewer that will be set on the task."
        }
        settings["publish_name_text"] = {
            "type": "string",
            "default": None,
            "description": "Potential publish name"
        }
        settings["publish_token_text"] = {
            "type": "string",
            "default": None,
            "description": "publish token"
        }
        return settings


    def create_settings_widget(self, parent):
        # Create our custom widget and return it.
        # It is actually a collection of widgets parented to a single widget.
        self.review_widget = ReviewWidget(parent, self.parent.shotgun)
        return self.review_widget


    def get_ui_settings(self, widget):
        # This will get called when the selection changes in the UI.
        # We need to gather the settings from the UI and return them
        return {"set_in_review": widget.review_status,
                "reviewer": widget.reviewer,
                "publish_name_text": widget.publish_name_text,
                "publish_token_text": widget.publish_token_text}


    def set_ui_settings(self, widget, settings):
        # The plugin task has just been selected in the UI, so we must set the UI state given the settings.
        # It's possible this is the first time the plugin task has been selected, in which case we won't have
        # any settings passed.
        # There also maybe multiple plugins selected in which case there might be a mix of states
        # The current implementation simply sets the settings for each settings block, so the end state of the UI
        # will represent that of the last selected item.
        for setting_block in settings:
            in_review = setting_block.get("set_in_review")
            if in_review:
                widget.review_status = in_review

            reviewer = setting_block.get("reviewer")
            if reviewer:
                widget.reviewer = reviewer

            publish_name_text = setting_block.get("publish_name_text")
            if publish_name_text:
                widget.publish_name_text = publish_name_text

            publish_token_text = setting_block.get("publish_token_text")
            if publish_token_text:
                widget.publish_token_text = publish_token_text


    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # set a Shotgun API instance
        sg = self.parent.shotgun

        in_review = settings.get("set_in_review")
        reviewer = settings.get("reviewer")
        publish_name_text = settings.get("publish_name_text")
        publish_token_text = settings.get("publish_token_text")

        # If we have a task then we can potentially set the review status and reviewer.
        if item.context.task:

            batch_data = []

            # set task status in review if chosen
            if in_review and in_review.value == True:
                self.logger.debug("Setting Task status to in review")
                batch_data.append({"request_type": "update",
                                   "entity_type": "Task",
                                   "entity_id": item.context.task["id"],
                                   "data": {"sg_status_list": "rev"}})

            # set the reviewer if chosen
            if reviewer and reviewer.value is not None:
                self.logger.debug("Adding Task reviewer: %s" % reviewer.value)
                batch_data.append({"request_type": "update",
                                   "entity_type": "Task",
                                   "entity_id": item.context.task["id"],
                                   "data": {"task_reviewers": [reviewer.value]},
                                   "multi_entity_update_modes":{"task_reviewers": "add"}})

            if batch_data:
                sg.batch(batch_data)

        else:
            if in_review and in_review.value == True:
                self.logger.warning("Set to in review chosen, but no Task has been set, skipping.")
            if reviewer and reviewer.value is not None:
                self.logger.warning("Reviewer chosen, but no Task has been set, skipping.")


class ReviewWidget(QtGui.QWidget):

    def __init__(self, parent, sg):

        super(ReviewWidget, self).__init__(parent)

        self.__setup_ui()
        # Add the reviewers to the reviewer combo box
        self.__populate_reviewers(sg, self.reviewer_cmbx)

    @property
    def review_status(self):
        return self.review_cbx.isChecked()

    @review_status.setter
    def review_status(self, value):
        self.review_cbx.setChecked(value)

    @property
    def reviewer(self):
        """
        Extract the Shotgun user data from the widget and return it.
        Should return something like {u'type': u'HumanUser', u'id': 190, u'name': u'Bob'}.
        :return: dict
        """
        index = self.reviewer_cmbx.currentIndex()
        return self.reviewer_cmbx.itemData(index)

    @reviewer.setter
    def reviewer(self, value):
        """
        When passed the Shotgun user data, it looks up the combobox index that matches this data and
        sets it to the current index.
        :param value:
        :return: Void
        """
        index = self.reviewer_cmbx.findData(value)
        self.reviewer_cmbx.setCurrentIndex(index)

    @property
    def publish_name_text(self):
        return self.publish_name_display.text()

    @publish_name_text.setter
    def publish_name_text(self, value):
        self.publish_name_display.setText(value)

    @property
    def publish_token_text(self):
        return self.publish_token_display.text()

    @publish_token_text.setter
    def publish_token_text(self, value):
        self.publish_token_display.setText(value)

    def __setup_ui(self):
        """
        Creates and lays out all the Qt widgets
        :return:
        """
        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        # Create a check box to hold the state of whether we should set the task in review.
        self.review_cbx = QtGui.QCheckBox("Set task to in review")

        # Create a Combobox to list and chose the reviewers.
        self.reviewer_cmbx = QtGui.QComboBox()
        self.reviewer_lbl = QtGui.QLabel("Select reviewer")
        self.reviewer_layout = QtGui.QHBoxLayout()
        self.reviewer_layout.addWidget(self.reviewer_cmbx)
        self.reviewer_layout.addWidget(self.reviewer_lbl)

        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        self.review_cbx.setSizePolicy(sp)
        self.reviewer_cmbx.setSizePolicy(sp)

        layout.addWidget(self.review_cbx)
        layout.setAlignment(self.review_cbx, QtCore.Qt.AlignLeft)
        layout.addLayout(self.reviewer_layout)

        self.review_cbx.hide()
        self.reviewer_lbl.hide()
        self.reviewer_cmbx.hide()

        self.publish_name_widgets_layout = QtGui.QHBoxLayout()
        self.publish_name_widgets_layout.setSpacing(4)
        self.publish_name_widgets_layout.setContentsMargins(-1, 1, -1, 8)
        self.publish_name_widgets_layout.setObjectName("publish_name_widgets_layout")
        self.publish_name_label = QtGui.QLabel("Publish Name")
        self.publish_name_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.publish_name_label.setOpenExternalLinks(True)
        self.publish_name_label.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.TextSelectableByMouse)
        self.publish_name_label.setObjectName("publish_name_label")

        self.publish_name_display = QtWidgets.QLineEdit()
        self.publish_name_display.setCursorPosition(0)
        self.publish_name_display.setToolTip('Display potential publish name override.')
        self.publish_name_display.setPlaceholderText('Potential publish name override')
        self.publish_name_display.setObjectName("publish_name_display")
        self.publish_name_display.setEnabled(False)
        self.publish_name_widgets_layout.addWidget(self.publish_name_label)
        self.publish_name_widgets_layout.addWidget(self.publish_name_display)

        self.publish_name_widgets_layout.setStretch(0, 1)
        self.publish_name_widgets_layout.setStretch(1, 100)
        self.publish_name_widgets_layout.setStretch(2, 1)

        self.publish_token_widgets_layout = QtGui.QHBoxLayout()
        self.publish_token_widgets_layout.setSpacing(4)
        self.publish_token_widgets_layout.setContentsMargins(-1, 1, -1, 8)
        self.publish_token_widgets_layout.setObjectName("publish_token_widgets_layout")
        self.publish_token_label = QtGui.QLabel("Publish Token")
        self.publish_token_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.publish_token_label.setOpenExternalLinks(True)
        self.publish_token_label.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.TextSelectableByMouse)
        self.publish_token_label.setObjectName("publish_token_label")

        self.publish_token_display = QtWidgets.QLineEdit()
        self.publish_token_display.setCursorPosition(0)
        self.publish_token_display.setToolTip('Publish token added at the end of publish name.')
        self.publish_token_display.setPlaceholderText('Publish token')
        self.publish_token_display.setObjectName("publish_token_display")
        self.publish_token_display.setEnabled(True)
        self.publish_token_widgets_layout.addWidget(self.publish_token_label)
        self.publish_token_widgets_layout.addWidget(self.publish_token_display)

        self.publish_token_widgets_layout.setStretch(0, 1)
        self.publish_token_widgets_layout.setStretch(1, 100)
        self.publish_token_widgets_layout.setStretch(2, 1)

        layout.addLayout(self.publish_name_widgets_layout)
        layout.addLayout(self.publish_token_widgets_layout)

    def __populate_reviewers(self, sg, combobox):
        """
        Populate the reviewer combobox with all the available reviewers found on the project.
        :param sg: Shotgun API instance
        :param combobox: The QCombobox that should be populated with users.
        :return: Void
        """

        # Get the current scene context
        current_context = sgtk.platform.current_engine().context

        # This logic assumes that you have a reviewer group that you have assigned users to
        # You could define available reviewers in a different way.
        filters = [
            # Only find users in the reviewer Group (id 6).
            ["groups", "is", {"type":"Group", "id": 6}],
            # Limit it to showing only reviewers that can see the current project.
            ["projects", "is", current_context.project]
        ]
        reviewers = sg.find("HumanUser", filters, ["name"])

        # Add an option so the user doesn't have to assign to someone.
        combobox.addItem("Leave unchanged")

        # Now add all the found users to the reviewer combo box.
        for reviewer in reviewers:
            combobox.addItem(reviewer["name"], reviewer)
