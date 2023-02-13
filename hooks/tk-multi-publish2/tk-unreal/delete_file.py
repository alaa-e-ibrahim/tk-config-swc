# Copyright (c) 2017 ShotGrid Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by ShotGrid Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class AddPublishPlugin(HookBaseClass):
    """
    """
    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(self.disk_location, "icons", "file.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Delete after upload"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Deletes the file upon successful uploading.
        """
        
    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        return {"accepted": True}

    def finalize(self, settings, item):
        """
        Removing published file
        """
        # self.logger.info("Finalize: path: %s" % item.properties["path"])
        #self.logger.info("Finalize: original_path: %s" % item.properties["original_path"])

        original_path = item.properties["original_path"]
        try:
            if os.path.isfile(original_path):
                self.logger.info("Deleting file %s ..." % original_path)
                os.remove(original_path)
        except:
            # If it fails, inform the user.
            self.logger.info("Unable to delete file: %s, file not found" % original_path)

