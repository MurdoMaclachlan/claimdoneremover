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

from os import remove
from os.path import isfile
from configparser import ConfigParser
from .log import doLog
from .misc import writeToFile

def createIni(gvars):
    
    doLog("praw.ini missing, incomplete or incorrect. It will need to be created.", gvars)
    iniVars = {
        "client_id": input("Please input your client id:  "),
        "client_secret": input("Please input your client secret:  "),
        "username": gvars.config["user"], # Since createIni is never called before the config is initialised, this is safe to draw from
        "password": input("Please input your Reddit password:  ")
    }
    with open(gvars.savePath+"/praw.ini", "a+") as file:
        file.write("[oscr]\n")
        for i in iniVars:
            file.write(i+"="+iniVars[i]+"\n")
    return True

def extractIniDetails(gvars):
    with open(gvars.home+"/.config/praw.ini", "r+") as file:
        content = file.read().splitlines()
        return None if content == [] else oscrOnly(content) # return None if praw.ini is empty

def getCredentials(gvars):
    
    # Use configparser magic to get the credentials from praw.ini
    credentials = ConfigParser()
    credentials.read(gvars.savePath + "/praw.ini")
    return dict(credentials["oscr"])
   
def oscrOnly(content, gvars):
    oscrContent = []
    append = False
    for line in content:
        if line.startswith("[") and not line in ["[oscr]", "[oscr]          "]:
            append = False
        elif line in ["[cdrcredentials]", "[oscr]", "[oscr]          "]:
            append = True
        if line == "[cdrcredentials]":
            doLog(f"Replacing line '{line}' with '[oscr]'.", gvars)
            line = "[oscr]"
        if append: oscrContent.append(line)
    return oscrContent

def reformatIni(gvars):

    try:
        with open(gvars.home+"/.config/praw.ini", "r") as file:
            content = file.read().splitlines()
        
        # If praw.ini is empty
        if content == []:
            doLog("praw.ini file is empty. Proceeding to create.", gvars)
            return createIni(gvars)
        
        else:
            with open(gvars.home+"/.config/oscr/praw.ini", "w+") as file:
                
                # Keep only OSCR content
                oscrContent = oscrOnly(content, gvars)
                
                # If no cdrcredentials or OSCR section was found
                if oscrContent == []:
                    doLog("praw.ini file is missing a section for OSCR. Proceeding to create.", gvars)
                    success = False
                
                # Else, write all OSCR content to new file
                else:
                    success = writeToFile(gvars, oscrContent, file)
                    
        # Remove OSCR section from old praw.ini, and remove file if no other sections are present
        strippedContent = stripOSCR(content)
        remove(gvars.home+"/.config/praw.ini")
        with open(gvars.home+"/.config/praw.ini", "w+") as file:
            for line in strippedContent:
                file.write(line+"\n")
            delete = True if file.readlines() == [] else False
        if delete: remove(gvars.home+"/.config/praw.ini")
        
        return True if success else createIni(gvars)

    # Catch missing praw.ini                
    except FileNotFoundError:
        if isfile(gvars.savePath + "/praw.ini"):
            doLog("praw.ini already formatted.", gvars)
        else: createIni(gvars)
           
def stripOSCR(content):
    delete = False
    for line in content:
        if line in ["[oscr]", "[oscr]          "]: delete = True
        elif line.startswith("["): delete = False
        if delete: content.pop(content.index(line))
    return content
