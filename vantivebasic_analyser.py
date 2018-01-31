from cast.analysers import ua, log, create_link, CustomObject
import os



class VantiveBasic(ua.Extension):
    """
    Vantive Basic analyser 
    """
    
    
    def __init__(self):
         
        # do we have the correct UA selected or not
        self.active = True
        # default extension list (for unit tests)
        # same as in metamodel...
        self.extensions = ['.vb']
     
    def start_analysis(self):
        # resistant (for unit tests)
        try:
            options = cast.analysers.get_ua_options()               #@UndefinedVariable dynamically added
            if not 'VantiveBasic' in options:
                # SQLScript language not selected : inactive
                self.active = False
            else:
                # options :
                self.extensions = options['VantiveBasic'].extensions
        except:
            pass
         
    def start_file(self, file):
         
        if not self.active:
            return # no need to do something
 
        path = file.get_path().lower()
        _, ext = os.path.splitext(path)
 
        if not ext in self.extensions:
            return
 
        #else : proceed...
        log.info('Analysing file %s' % file.get_path())
        
        # Creating an object to track the call to end points (File manipulation, ...)
        #log.debug('Creating VantiveBasic_EndPoint')
        #o = CustomObject()
        #o.set_name('VantiveBasic_EndPoint')
        #o.set_external()
        #o.set_type('VantiveBasic_LinkToStandardFunction')
        #o.set_parent(file)
        #o.save()
        
    #def start_object(self, object):
    #    log.info('Start object %s' % str(object))

    def end_object(self, object):
        #log.debug('end_object %s ' % str(object)) 
                 #% str(object.get_position()))
        None
