from msi import *
import serial
import cherrypy
import os.path
from cherrypy.lib.static import serve_file
	

print "****************************"
print "Starting Marantz Web Service"
print 'MSW: Python Version   : ' + platform.python_version()
print 'MSW: PySerial Version : ' + serial.VERSION

serialIn = serial.Serial('/dev/ttyS0', 9600, bytesize=8, parity='N', stopbits=1, timeout=0)
print 'MSW: Connection success - Port: ' + serialIn.portstr

marantzSerialInt = MarantzSerialInterface(serialIn)
marantzSerialInt.start()


class WebApp:
	def index(self):
		current_dir = os.path.dirname(os.path.abspath(__file__))
		return open(os.path.join(current_dir, 'html', 'webInterface.html'))

	index.exposed = True
	
	@cherrypy.expose
	def jquery_js(self):
		current_dir = os.path.dirname(os.path.abspath(__file__))
		return serve_file(os.path.join(current_dir, 'js', 'jquery.js'),
                              content_type='application/javascript')
	
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def status(self, **kwargs):
		aStatus = marantzSerialInt.status()
		return {"power" : aStatus.pwr, "volume": aStatus.vol}
		
	@cherrypy.expose
	@cherrypy.tools.json_out()		
	def powerOn(self, **kwargs):
		marantzSerialInt.cmdMeta('powerOn')
		return {"message" : "ACK"}

	@cherrypy.expose
	@cherrypy.tools.json_out()		
	def powerOff(self, **kwargs):
		marantzSerialInt.cmdMeta('powerOff')
		return {"message" : "ACK"}
		
	@cherrypy.expose
	@cherrypy.tools.json_out()		
	def volumeUp(self, **kwargs):
		marantzSerialInt.cmdMeta('volumeUp')
		return {"message" : "ACK"}
		
	@cherrypy.expose
	@cherrypy.tools.json_out()		
	def volumeDown(self, **kwargs):
		marantzSerialInt.cmdMeta('volumeDown')
		return {"message" : "ACK"}
		

cherrypy.config.update({'server.socket_host': '0.0.0.0', 
                         'server.socket_port': 9999, 
                        })
cherrypy.quickstart(WebApp())
