"""
    Copyright (C) 2020-present, Murdo B. Maclachlan

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.
    
    Contact me at murdo@maclachlans.org.uk
"""

import praw
import re
import configparser
from time import sleep
from alive_progress import alive_bar as aliveBar
from os.path import isfile
from .gvars import version
from .log import doLog, updateLog
from .comment import removeNonAlpha, remover
from .ini import createIni, extractIniDetails, getCredentials
from .misc import exitWithLog, writeToFile

"""
    Beneath is the main program. From here, all run-time flow
    of OSCR is controlled through the oscr() function, passed
    gvars by the oscr top-level script run through the console
    command.
    
    This function initiates after all arguments have been
    checked and global variables have been collected and
    processed as needed, and continues to loop until run-time
    ends.
"""

def oscr(gvars):

    doLog(f"Running OSCR version {version} with recur set to {gvars.config['recur']}.", gvars)
    doLog("WARNING: log updates are OFF. Console log will not be saved for this instance.", gvars) if not gvars.config["logUpdates"] else None
    
    # Initialises Reddit() instance
    try:
        reddit = praw.Reddit(
            user_agent = gvars.config["os"] + ":oscr:v" + version + " (by /u/MurdoMaclachlan)",
            **getCredentials(gvars)
        )
    
    # Catch for invalid ini, will create a new one then restart the program;
    # the restart is required due to current PRAW limitations. :'(
    except (configparser.NoSectionError, praw.exceptions.MissingRequiredAttributeException, KeyError):
        if isfile(gvars.savePath+"/praw.ini"):
            iniDetails = extractIniDetails(gvars)
            if iniDetails is None: pass
            else:
                writeToFile(gvars, iniDetails, open(gvars.savePath+"/oscr/praw.ini", "w+"))
                exitWithLog(gvars, "praw.ini successfully created, program restart required for this to take effect.")

        if createIni(gvars): exitWithLog(gvars, "praw.ini successfully created, program restart required for this to take effect.")
        else: exitWithLog(gvars, "Failed to create praw.ini file, something went wrong.")
    
    # Fetches statistics
    if gvars.config["reportTotals"]:
        from .statistics import fetch, update
        totalCounted, totalDeleted = fetch("counted", gvars), fetch("deleted", gvars)
    
    updateLog("Updating log...", gvars)
    updateLog("Log updated successfully.", gvars)
    
    while True:
        deleted, counted, waitingFor = 0, 0, 0
        
        # Fetches the comment list from Reddit
        doLog("Retrieving comments...", gvars)
        commentList = reddit.redditor(gvars.config["user"]).comments.new(limit=gvars.config["limit"])
        doLog("Comments retrieved; checking...", gvars)
        
        # Initialises the progress bar
        with aliveBar(gvars.config["limit"], spinner='classic', bar='classic', enrich_print=False) as progress:
            
            # Checks all the user's comments, deleting them if they're past the cutoff.
            for comment in commentList:
                if gvars.config["useRegex"]: 
                    if sum([True for pattern in gvars.config["regexBlacklist"] if re.match(pattern, (comment.body.lower(), comment.body)[gvars.config["caseSensitive"]])]) > 0 and str(comment.subreddit).lower() in gvars.config["subredditList"]:
                        deleted, waitingFor = remover(comment, gvars.config["cutoffSec"], deleted, waitingFor, gvars)
                else:
                    if (removeNonAlpha(comment.body.lower()), comment.body)[gvars.config["caseSensitive"]] in gvars.config["blacklist"] and str(comment.subreddit).lower() in gvars.config["subredditList"]:
                        deleted, waitingFor = remover(comment, gvars.config["cutoffSec"], deleted, waitingFor, gvars)
                counted += 1
                
                progress()
    
        doLog(f"Successfully checked all {counted} available comments.", gvars)
    
        # Notifies if the end of Reddit's listing is reached (i.e. no new comments due to API limitations)
        try:
            if counted < gvars.config["limit"]:
                doLog(f"OSCR counted less comments than your limit of {gvars.config['limit']}. You may have deleted all available elligible comments, or a caching error may have caused Reddit to return less coments than it should. It may be worth running OSCR once more.", gvars)
        except TypeError:
            if counted < 1000:
                doLog("OSCR counted less comments than your limit of 1000. You may have deleted all available elligible comments, or a caching error may have caused Reddit to return less coments than it should. It may be worth running OSCR once more.", gvars)
    
        # Updates statistics
        if gvars.config["reportTotals"]:
            totalCounted += counted
            totalDeleted += deleted
            update("counted", totalCounted, gvars)
            update("deleted", totalDeleted, gvars)
        
        # Gives info about this iteration; how many comments were counted, deleted, still waiting for.
        doLog(f"Counted this cycle: {str(counted)}", gvars)
        doLog(f"Deleted this cycle: {str(deleted)}", gvars)
        doLog(f"Waiting for: {str(waitingFor)}", gvars)
        if gvars.config["reportTotals"]:
            doLog(f"Total Counted: {str(totalCounted)}", gvars)
            doLog(f"Total Deleted: {str(totalDeleted)}", gvars)
    
        # If recur is set to false, updates log and kills the program.
        if not gvars.config["recur"]:
            updateLog("Updating log...", gvars)
            updateLog("Log updated successfully.", gvars)
            updateLog("Exiting...", gvars)
            break
    
        # Updates log, prepares for next cycle.
        updateLog("Updating log...", gvars)
        updateLog("Log updated successfully.", gvars)
        doLog(f"Waiting {str(gvars.config['wait'])} {gvars.config['unit'][0] if gvars.config['wait'] == 1 else gvars.config['unit'][1]} before checking again...", gvars)
        updateLog("", gvars)
    
        sleep(gvars.config["waitTime"])
