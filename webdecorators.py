import functools
from model import Session
import logging
import hashlib
import urllib
import datetime

from google.appengine.ext import db
from google.appengine.api import memcache

def authorize(redirectTo = "/"):
	def factory(method):
		'Ensures that when an auth cookie is presented to the request that is is valid'
		@functools.wraps(method)
		def wrapper(self, *args, **kwargs):
		
			#Get the session parameters
			auth_id = self.request.cookies.get('auth_id', '')
			session_id = self.request.cookies.get('session_id', '')
			service = urllib.unquote(args[0])
			
			#Check the db for the session
			session = Session.GetSession(session_id, auth_id)
			
			if session is None:
				logging.info("No Session")
				self.redirect(redirectTo)
				return
			else:
				if session.service is None:
					logging.info("Service is None")
					self.redirect(redirectTo)
					return
				
				if hashlib.sha1(service).hexdigest() != hashlib.sha1(session.service.email).hexdigest():
					# The service in the url is not the same as the sessioned service.
					self.redirect(redirectTo)
					return
				
				result = method(self, *args, **kwargs)
				
			return result
		return wrapper
	return factory
	
def session(method):
	'Ensures that the sessions object (if it exists) is attached to the request.'
	@functools.wraps(method)
	def wrapper(self, *args, **kwargs):
	
		#Get the session parameters
		auth_id = self.request.cookies.get('auth_id', '')
		session_id = self.request.cookies.get('session_id', '')
		
		#Check the db for the session
		session = Session.GetSession(session_id, auth_id)			
					
		if session is None:
			session = Session()
			session.session_id = Session.MakeId()
			session.auth_token = Session.MakeId()
			session.put()
		
		# Attach the session to the method
		self.SessionObj = session			
					
		#Call the handler.			
		result = method(self, *args, **kwargs)
		
		self.response.headers.add_header('Set-Cookie', 'auth_id=%s; path=/; HttpOnly' % str(session.auth_token))
		self.response.headers.add_header('Set-Cookie', 'session_id=%s; path=/; HttpOnly' % str(session.session_id))
		
		return result
	return wrapper
	
def redirect(method, redirect = "/applications"):
	'When a known user is logged in redirect them to their home page'
	@functools.wraps(method)
	def wrapper(self, *args, **kwargs):
		try:	
			if self.SessionObj is not None:
				if self.SessionObj.user is not None:
					self.redirect(redirect)
					return
		except:
			pass
		return method(self, *args, **kwargs)
	return wrapper