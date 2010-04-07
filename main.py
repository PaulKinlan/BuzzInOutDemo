#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch

from google.appengine.api import xmpp

import templates
import model
import webdecorators

import re
import logging
import urllib
import feedparser

class MainHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(templates.RenderThemeTemplate("index.tmpl", {}))
   
    
class LoginHandler(webapp.RequestHandler):
  @webdecorators.session
  def get(self):
    
    email = self.request.get("email")
    
    xmpp.send_invite(email)
    
    fingerUrl = "http://www.google.com/s2/webfinger/?q=acct:%s" % email
    fingerFetch = urlfetch.fetch(fingerUrl)
    fingerContent = fingerFetch.content
    logging.info(fingerContent)
    aliasMatches = re.search(r"<Link rel='http://specs.openid.net/auth/2.0/provider' href='(.+?)'", fingerContent)
    buzzFeedMatch = re.search(r"<Link rel='http://schemas.google.com/g/2010#updates-from' href='(.+?)'", fingerContent)
    
    self.SessionObj.email = email
    
    if buzzFeedMatch:
      buzzUrl = buzzFeedMatch.group(1)
      # Stash the URL... This whole session thing is not perfect at all.
      # It can be overwritten .
      self.SessionObj.buzzUrl = buzzUrl
      self.SessionObj.profileUrl = ""
      self.SessionObj.put()

    
    if aliasMatches:
      # The email is valid so start a session.      
      url = aliasMatches.group(1)

      profile_request = urlfetch.fetch(url)
      profile_response = profile_request
      
      if profile_response.headers["x-xrds-location"]:
        xrds_uri = profile_response.headers["x-xrds-location"]
        xrds_request = urlfetch.fetch(xrds_uri)
        
        matches = re.search(r"<URI>(.+)</URI>", xrds_request.content)
        
        if matches:
          uri = matches.group(1)
          return_to = "http://statusmate.appspot.com/login_return"
          
          auth_request_params =  {
             "openid.ns": "http://specs.openid.net/auth/2.0",
             "openid.mode": "checkid_setup",
             "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
             "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
             "openid.return_to": return_to
          }
          
          auth_request_uri = "%s&%s" % (uri, urllib.urlencode(auth_request_params))
          
          self.redirect(auth_request_uri)  
          return
        else:
          self.response.out.write("Sorry, your openid information cannot be discovered.")
    else:
      self.response.out.write("Sorry, your email can't be fingered.")
   
class ReturnHandler(webapp.RequestHandler):
  @webdecorators.session
  def get(self):
    logging.info(self.request.headers)
    profile = self.request.get("openid.identity")
    logging.info(urllib.unquote(profile))
    logging.info(self.SessionObj.profile)
    
    self.redirect('/services')
    return
    
    # Only transfer if we have a valid user. 
    if self.SessionObj.profile == urllib.unquote(profile).replace('https://',''):
      self.SessionObj.user = model.User.Get(profile)

      self.SessionObj.put()
      
    else:
      self.redirect('/auth_error')
    
class Services(webapp.RequestHandler):
  @webdecorators.session
  def get(self):
    """
    Get the Buzz feed associated with the session.
    """
    feed = feedparser.parse(self.SessionObj.buzzUrl)
    logging.info(feed.feed)
    # Get the 
    hub = feed.feed.links[1].href
    logging.info(hub)
    url = "%s?hub.callback=%s&hub.topic=%s&hub.verify=sync&hub.mode=subscribe" % (hub, urllib.quote("http://statusmate.appspot.com/callback/%s" % self.SessionObj.email), urllib.quote(self.SessionObj.buzzUrl))
    logging.info(url)
    urlfetch.fetch(url, method = "POST")
    
    self.response.out.write(templates.RenderThemeTemplate("buzz.tmpl", {"feed": feed, "hub" : hub}))
    
    
class Feed(webapp.RequestHandler):
  def get(self, serivce, user):
    """
    Gets a feed for a given user and
    """
    self.response.out.write(templates.render(""))
    
class AuthErrorHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(self.request)
    
class PubsubhubbubEndpoint(webapp.RequestHandler):
  def get(self, email):
    """
    Recieves a user's buzzes
    """
    mode = self.request.get("hub.mode")
    
    if mode == "subscribe":
      logging.info("SUBSCRIBE")
      self.response.out.write(self.request.get("hub.challenge"))
      return
      
  def post(self, email):
    logging.info("PUBLISH")
    logging.info(self.request.body)
    email = urllib.unquote(email)
    logging.info(email)
    
    if email is None:
      email = "paul.kinlan@gmail.com"
    
    feed = feedparser.parse(self.request.body)
    
    for entry in feed.entries:
      xmpp.send_message(email, entry.content[0].value)

def main():
  handlers = [
    ('/', MainHandler),
    ('/login', LoginHandler),
    ('/login_return', ReturnHandler),
    ('/auth_error', AuthErrorHandler),
    ('/callback/(.+)', PubsubhubbubEndpoint),
    ('/services', Services)
  ]
  application = webapp.WSGIApplication(handlers,
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
