from cast.application import ApplicationLevelExtension, ReferenceFinder, create_link, Bookmark
from cast.analysers import CustomObject
import logging
import re
import sys
 
class ApplicationExtension(ApplicationLevelExtension):
    nbVBFileScanned = 0
    nbVBFunctions = 0
    nbVBSubroutines = 0
    nbVBDialogs = 0
    nbVBDialogEvents = 0
    nbVBLinkToFunction = 0
    
    nbLinksCreatedDialogEvents = 0
    nbLinksFunctionSubToFunctionSub = 0
    nbLinksFunctionSubToDialog = 0
    nbCallsBetweenFunctionsSubs_NameNotCaptured = 0
    nbDialogDeclaration_DialogNotFound = 0
    nbDialogNotFound = 0
    nbVBLinkToStandardFunction = 0

    
    VBDialogList = []
    VBLinkToFunction = []
    VBFunctionList = []
    VBSubList = []    
    
    def end_application(self, application):
        logging.info(" ========================================================================================== ")
        #logging.debug("com.castsoftware.uc.vantivebastic extension - running code at the end of an application")

        # iterate all Vantive basic functions of the application
        for vbfunction in application.search_objects(category='VantiveBasic_Function'):
            self.nbVBFunctions += 1
            vbfunction_name = vbfunction.get_name()
            vbfunction_fullname = vbfunction.get_fullname()
            self.VBFunctionList.append(vbfunction_name)
            logging.debug('vbfunction --> '+vbfunction_name+' --> '+vbfunction_fullname)

        # dummy object representing links to any function (to capture the link to standard Vantive Basic functions)
        for vo in application.search_objects(category='VantiveBasic_LinkToFunction'):
            self.VBLinkToFunction.append(vo)
            self.nbVBLinkToFunction += 1
            logging.debug('vblinktofct --> '+vo.get_fullname())            
    
        # iterate all Vantive basic subroutines of the application
        for vbsub in application.search_objects(category='VantiveBasic_Sub'):
            self.nbVBSubroutines += 1
            vbsub_name = vbsub.get_name()
            vbsub_fullname = vbsub.get_fullname()
            self.VBSubList.append(vbsub_name)
            logging.debug('vbsub --> '+vbsub_name+' --> '+vbsub_fullname)
    
         # iterate all Vantive basic dialogs of the application
        for vbdialog in application.search_objects(category='VantiveBasic_Dialog'):
            self.nbVBDialogs += 1
            vbdialog_name = vbdialog.get_name()
            vbdialog_fullname = vbdialog.get_fullname()
            self.VBDialogList.append(vbdialog_name)
            logging.debug('vbdialog --> '+vbdialog_name+' --> '+vbdialog_fullname)               
        
        # list all files saved for Vantive Basic
        files = application.get_files(['sourceFile'])
         
        #looping through Vantive basic files
        for o in files:
            # check if file is analyzed source code, or if it generated (Unknown)
            if not o.get_path():
                continue
            # check if file is a Vantive basic script file
            if not (o.get_path().lower().endswith('.vb') or o.get_path().lower().endswith('.bas')):
                continue
            logging.debug("file found: >" + str(o.get_path()))
            self.scan_vbfile(application, o)               
            self.nbVBFileScanned += 1
       
        # Final reporting in ApplicationPlugins.castlog
        logging.info("###################################################################################")
        logging.info("Vantive Basic Runtime STATISTICS : Number of .vb files scanned : " + str(self.nbVBFileScanned))
        logging.info("Vantive Basic Runtime STATISTICS : Number of Vantive basic functions : " + str(self.nbVBFunctions))
        logging.info("Vantive Basic Runtime STATISTICS : Number of Vantive basic subroutines (sub) : " + str(self.nbVBSubroutines))    
        logging.info("Vantive Basic Runtime STATISTICS : Number of Vantive basic dialog : " + str(self.nbVBDialogs))    
        logging.info("Vantive Basic Runtime STATISTICS : Number of Vantive basic dialog events : " + str(self.nbVBDialogEvents)) 
        logging.info("###################################################################################")
        logging.info("Vantive Basic Runtime STATISTICS : Number of links created between VantiveBasic Function/Sub to VantiveBasic Dialog : " + str(self.nbLinksFunctionSubToDialog))
        logging.info("Vantive Basic Runtime STATISTICS : Number of links created between VantiveBasic Dialog and events (Function or Sub) : " + str(self.nbLinksCreatedDialogEvents))
        logging.info("Vantive Basic Runtime STATISTICS : Number of links created between VantiveBasic Function/Sub to Function/Sub  : " + str(self.nbLinksFunctionSubToFunctionSub))
        logging.info("Vantive Basic Runtime STATISTICS : Number of links to function : " + str(self.nbVBLinkToFunction)) 
        logging.info("Vantive Basic Runtime STATISTICS : Number of links to external standard functions : " + str(self.nbVBLinkToStandardFunction))
        
        #logging.info("Vantive Basic Runtime STATISTICS : VantiveBasic Function/Sub to Function/Sub links - Number of  : " + str(self.nbCallsBetweenFunctionsSubs_NameNotCaptured))
        #nbCallsBetweenFunctionsSubs_NameNotCaptured = 0
        #nbDialogDeclaration_DialogNotFound = 0
        #nbDialogNotFound = 0
    
        logging.info(" ========================================================================================== ")

    ####################################################################################################################
 
    
    def find_VBFunctionOrSub_by_position(self, vbfile, bookmark):
        #"""
        #Find the Function or Sub located at a specific bookmark
        #"""
        result = None
        result_position = None
        for sub_object in vbfile.load_objects():
            if sub_object.get_type() in ('VantiveBasic_Function' , 'VantiveBasic_Sub'):
                #logging.debug(" ### %s %s",sub_object.get_type(), sub_object.get_name())
                for position in sub_object.get_positions():
                    if position.contains_position(bookmark.begin_line,bookmark.begin_column) and (not result_position or result_position.contains(position)):
                        result = sub_object
                        result_position = position
                        break
        #logging.debug(" ### %s ",str(result))   
        return result

    ####################################################################################################################
    
    def scan_vbfile(self, application, vbfile):
                                    
        # one RF for multiples patterns
        rfCall = ReferenceFinder()
        # Be careful, the order here is important !!!!!!
        rfCall.add_pattern('COMMENTEDline', before = '', element = r'^[ /s\t]*\'.*$', after = '')
        rfCall.add_pattern('COMMENTEDmultiline', before = '', element = r'\/\*.*\*\/', after = '')
        rfCall.add_pattern('DialogDeclaration', before = '', element = r'[bB][eE][gG][iI][nN][ /s\t]+[dD][iI][aA][lL][oO][gG].*$', after = '')
        rfCall.add_pattern('CallsBetweenFunctionsSubs', before = '', element = r'[=][ \t]*[A-Za-z0-9_]+[ \t]*\(', after = '')

        # search all patterns in current program
        try:
            references = [reference for reference in rfCall.find_references_in_file(vbfile)]
            #logging.debug("  STEP A24 ") 
        except FileNotFoundError:
            logging.warning("Wrong file or file path, from Vn-1 or previous " + str(vbfile))
        else:
            #logging.debug("  STEP A25 ") 
            # for debugging and traversing the results
            for reference in references:
                #logging.debug("  STEP A26: reference found: >" +str(reference))
                ####################################################################################################################
                # capturing and creating the link from the VantiveBasic_Dialog ou VantiveBasic_Sub to VantiveBasic_Dialog ou VantiveBasic_Sub
                if reference.pattern_name=='CallsBetweenFunctionsSubs':
                    objectRef = None
                    # of  
                    if reference.object.get_type() == 'VantiveBasic_LinkToFunction':
                        objectRef = self.find_VBFunctionOrSub_by_position(vbfile, reference.bookmark)
                        logging.debug("  CallsBetweenFunctionsSubs: %s ==> %s (parent %s)", reference.value, reference.bookmark, objectRef)
                    else:
                        objectRef = reference.object
                        logging.warning("  CallsBetweenFunction captured in a comment ? %s %s %s", reference.value, reference.bookmark, reference.object)

                    if not objectRef:
                        logging.warning(" Missing parent object for VantiveBasic_LinkToFunction %s", reference.object)
                        continue
                    
                    p = re.compile("[=][ \t]*([A-Za-z0-9_]+)[ \t]*\(")            
                    m = p.search(reference.value)
                    functionOrSubName = None
                    if m:
                        try:
                            functionOrSubName = m.group(1)
                        except: # catch *all* exceptions
                            None                                
                    if functionOrSubName == None:
                        logging.warn(" CallsBetweenFunctionsSubs - Not able to capture Function of Sub name in %s", reference.value)  
                        self.nbCallsBetweenFunctionsSubs_NameNotCaptured += 1 
                    else:
                        functionOrSubNameType = None
                        for functionname in self.VBFunctionList:
                            if functionOrSubName.lower() == functionname.lower():
                                functionOrSubName = functionname
                                functionOrSubNameType = 'Function'
                                break
                        if functionOrSubNameType == None:
                            for subname in self.VBSubList:
                                #logging.debug("                  STEP A28 %s", subname)                             
                                if functionOrSubName.lower() == subname.lower():
                                    functionOrSubName = subname
                                    functionOrSubNameType = 'Sub'
                                    break         
                        #logging.debug("  STEP A30 %s", functionOrSubName) 
                        # the artifacts called is a known function or sub, so we are creating the link
                        if functionOrSubNameType != None:
                            for oFunctionSub in application.search_objects(name=functionOrSubName):
                                if oFunctionSub.get_type() in ('VantiveBasic_Function' , 'VantiveBasic_Sub'):
                                #if objectRef.id != oFunctionSub.id:
                                    logging.info("CallsBetweenFunctionsSubs - Creating a link from %s %s (%s) ==> to %s %s (%s)", objectRef.get_type(), objectRef.get_name(), objectRef.id, functionOrSubNameType, functionOrSubName, oFunctionSub.id)
                                    create_link('callLink', objectRef, oFunctionSub, reference.bookmark)
                                    self.nbLinksFunctionSubToFunctionSub += 1
                                    break                           
                        # it's a standard Vantive basic function, not a customer function or sub we are creating an external object
                        # this will help us setting some end points in TCC
                        else:
                            for o in self.VBLinkToFunction:
                                if vbfile.get_name() in o.get_fullname():
                                    #create_link('callLink', objectRef, o)
                                    #logging.debug('Creating link to VantiveBasic_LinkToFunction %s', functionOrSubName);
                                    self.nbVBLinkToStandardFunction += 1
                                    break
                    
                ####################################################################################################################                    
                # capturing and creating the link from the VantiveBasic_Dialog object to its Function or Sub Event

                if reference.pattern_name=='DialogDeclaration':
                    logging.debug("  DialogDeclaration: %s ==> %s (parent %s)", reference.value, reference.bookmark, reference.object)
                                              
                    # retrieve the name of the dialog
                    p = re.compile("[bB][eE][gG][iI][nN][ \t]+[dD][iI][aA][lL][oO][gG]+[ \t]+([A-Za-z0-9_]+)")            
                    m = p.search(reference.value)
                    dialogName = None
                    if m:
                        try:
                            dialogName = m.group(1)
                        except: # catch *all* exceptions
                            None                                
                    if dialogName == None:
                        logging.warn(" DialogDeclaration - Not able to capture Dialog name in %s", reference.value)
                        self.nbDialogDeclaration_DialogNotFound += 1
                        
                    # retrieve the name of the event
                    p = re.compile("[bB][eE][gG][iI][nN][ /s\t]+[dD][iI][aA][lL][oO][gG].*,\.([A-Za-z0-9_]+).*$")
                    m = p.search(reference.value)
                    eventName = None
                    if m:
                        try:
                            eventName = m.group(1)
                            self.nbVBDialogEvents += 1  
                        except: # catch *all* exceptions
                            None
                    if eventName == None:
                        logging.debug(" DialogDeclaration - No event for this Dialog %s", reference.value)             

                    
                    if dialogName != None and eventName != None:                        
                        foundDialogToLink = False
                        foundEventToLink = False
                        try:
                            for oDialog in application.search_objects(name=dialogName):
                                if foundEventToLink:
                                    break
                                # check if the Dialog found is the one in the current file
                                i = -1
                                try:
                                    i = oDialog.get_fullname().index(vbfile.get_name())
                                except ValueError:         
                                    None 
                                if i <= 0:
                                    # skip the Dialog because it's from another file with same name, we want only the Dialog that is in the current file with this name 
                                    continue
                                foundDialogToLink=True
                                #logging.debug("DialogDeclaration - Creating a link from Dialog %s ==> to Function or Sub %s", dialogName, eventName)
                                logging.debug('DialogDeclaration - Dialog Object found --> '+oDialog.get_fullname()+'/'+oDialog.get_type())
                                
                                dialogParentObject = self.find_VBFunctionOrSub_by_position(vbfile, reference.bookmark)
                                logging.debug("dialogParentObject %s",str(dialogParentObject))
                                if dialogParentObject:
                                    create_link('callLink', dialogParentObject, oDialog, reference.bookmark)
                                    self.nbLinksFunctionSubToDialog += 1
                                    logging.info("DialogDeclaration - FuncSubToDialog Link created between %s %s (%s) => %s %s (%s)", dialogParentObject.get_type(),dialogParentObject.get_fullname(),dialogParentObject.id,oDialog.get_type(), oDialog.get_fullname(),oDialog.id)
                                else:
                                    logging.warning("DialogDeclaration dialog parent function not found for %s", str(oDialog))
                                
                                # in some case, the function/sub has not the same case and we need to have the case to find the object and create the link
                                for functionname in self.VBFunctionList:
                                    if eventName.lower() == functionname.lower():
                                        eventName = functionname
                                        break
                                for subname in self.VBSubList:
                                    if eventName.lower() == subname.lower():
                                        eventName = subname
                                        break                                
                                for oFunctionSub in application.search_objects(name=eventName):
                                    #logging.debug('DialogDeclaration - Function/Sub Object found--> '+oFunctionSub.get_fullname()+'/'+oFunctionSub.get_type())
                                    foundEventToLink = True
                                    create_link('callLink', oDialog, oFunctionSub, reference.bookmark)
                                    logging.info("DialogDeclaration - DialogToEvent Link created between %s %s (%s) => %s %s (%s)", oDialog.get_type(), oDialog.get_fullname(), oDialog.id, oFunctionSub.get_type(), oFunctionSub.get_fullname(), oFunctionSub.id)
                                    self.nbLinksCreatedDialogEvents += 1
                                    break
                        except KeyError: 
                            logging.warn("DialogDeclaration - Error creating link from Dialog %s ==> to Function or Sub %s", dialogName, eventName)
                        
                        if not foundDialogToLink:
                            logging.warning("DialogDeclaration - Dialog Object %s not found", dialogName)
                            self.nbDialogNotFound += 1
                        if foundDialogToLink and not foundEventToLink:
                            logging.warning("DialogDeclaration - Function/Sub Object %s not found", eventName)
                            self.nbDialogDeclaration_DialogNotFound  += 1
                ####################################################################################################################
    
                        

